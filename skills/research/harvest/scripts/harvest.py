#!/usr/bin/env python3
"""Collect a list of public sources politely and keep what was fetched, with provenance.
Standard library only.

Usage:
  python harvest.py check   JOB.json [--allow-local] [--json]
  python harvest.py plan    JOB.json [--offline-fixtures DIR] [--fixture-map NAME] [--allow-local] [--json]
  python harvest.py run     JOB.json --out DIR [--max-age-days N] [--refetch] [--max-wait SECONDS]
                            [--offline-fixtures DIR] [--fixture-map NAME] [--allow-local] [--json]
  python harvest.py verify  DIR [--json]
  python harvest.py extract DIR [--json]
  python harvest.py ledger  DIR --out SOURCES.csv [--json]

JOB.json (every key is required unless marked optional; unknown keys are refused):
  {"job_id": "kebab-case-id",
   "description": "what is being collected and why, in a sentence or two",
   "people": "none",                      none | public_role_only   (see below)
   "user_agent": "harvest/1.0 (research collection; contact: REPLACE_ME)",
   "delay_seconds": 2, "max_requests": 60, "max_bytes": 20000000, "timeout_seconds": 20,
   "sources": [{"id": "S1", "address": "https://...", "title": "...", "publisher": "...",
                "tier": "primary", "kind": "page", "published": "2026-01-15"}]}
  tier is primary | peer_reviewed | secondary | aggregator | unverified. kind is page | feed | file.
  published is optional: a real date written YYYY-MM-DD.
  people says who the pages are about: "none" (documents, data, organisations) or
  "public_role_only" (people appear only as authors, officers or spokespeople of an organisation).
  A job about private individuals has no valid value and is refused.

What each command does:
  check    validates the job. Touches no network and writes nothing.
  plan     validates, fetches each host's robots.txt, and prints what would be fetched, what would
           be skipped and why, and the least time the run can take. Fetches no content.
  run      fetches in order, one request at a time. Raw bytes go to DIR/store/<sha256>.raw and one
           record per source is appended to DIR/fetch_log.jsonl: source id, address requested, final
           address after redirects, time (UTC), status, content type, byte length, SHA-256, the
           robots decision, every request made, and any error. A source whose stored copy is younger
           than --max-age-days (default 7) is skipped unless --refetch. Changed content is stored
           beside the old version and both hashes are logged.
  verify   re-hashes every stored file against the log.
  extract  writes DIR/store/<sha256>.extracted.txt beside each stored page (tags stripped, scripts
           and styles dropped, title kept) and each stored feed (entries with title, link, date),
           and logs the derivative's own hash in DIR/derived_log.jsonl. It strips markup and nothing
           more: menus, footers and cookie notices stay in. It does not find "the article".
           Each derivative opens with where it came from: the raw file and its SHA-256, the source
           id, the address that answered, the address asked for when that differs, and the time
           (UTC) that copy was first stored. A line of dashes follows, and a notice above it says
           that everything below is the page's own text, kept as data: a sentence in a page that
           reads as an instruction is content and is not carried out by anything here.
  ledger   writes research-ledger source rows: accessed from the log, read_level "snippet" (fetched
           is not read), notes carrying the content hash.

--offline-fixtures DIR answers every request from DIR/fixtures.json (or --fixture-map NAME) and
uses a simulated clock, so nothing touches the network and nothing really waits. The mapping is
  {"responses": {"https://host/path": {"status": 200, "headers": {"Content-Type": "text/html"},
                                       "file": "page.html"}}}
An entry may give "body" (text) in place of "file", or "error": "timeout" | "connection". A list of
entries is used in order, one per request, the last one repeating. An address with no entry
answers 404. Records made this way are marked offline in the log and in the ledger notes.

What it enforces (ERROR; the job is refused or the source is not fetched):
  - http and https addresses only, with no user name or password in them
  - no loopback, private, link-local or other non-public address, and no local host name, unless
    --allow-local is given; checked for every redirect target as well
  - robots.txt is fetched for each host and honoured for the product token of the user agent
    (RFC 9309: most specific group, longest matching rule, Allow wins a tie, * and $ supported).
    A disallowed path is skipped and logged. If robots.txt cannot be read (401, 403, 429, 5xx,
    a network error, too many redirects) the host's sources are skipped; 404 means no rules
  - one request at a time; at least delay_seconds (never below 1) between requests to one host,
    raised to the site's Crawl-delay when that is longer
  - max_requests and max_bytes stop the run; every request counts, including robots.txt,
    redirects and the one retry. Partial content is never stored
  - every request has a timeout; an error is recorded and not retried
  - Retry-After on 429 or 503 is honoured once, if it is no longer than --max-wait (default 120);
    a host that still answers 429 gets no further requests in the run
  - 401, 402, 403, 407 and 451, and a redirect to a sign-in page, are recorded and left alone
  - the user agent names the job and gives a contact; a browser or search-engine string is
    refused, and so is the REPLACE_ME placeholder on run (plan and check allow it)
  - no cookies, credentials or custom headers are sent; a job that asks for them is refused
  - people must be declared, and social-network and people-search hosts are refused
  - a stored file is never overwritten; the log is only ever appended to
What it reports for a person to decide (ADVISORY):
  - addresses that look like pages about a person; a cap that will end the run early; a fragment
    that is not sent; an earlier run that did not finish; two or more sources that returned
    identical bytes (often a placeholder, a consent page or a sign-in page)
Text printed to the terminal is ASCII with control characters replaced, so a title, a header or an
address sent by a server cannot move the cursor or recolour the screen. --json output escapes them.

What it cannot tell: whether a site's terms allow automated collection, whether a page that
answered 200 is really a login or consent wall, whether a page is about a private person, or
whether the content is accurate. It cannot stop a host name resolving to a different address
between its check and the connection, or two runs in different output folders from asking one
host at the same time. The log shows a file has not changed since it was written; it cannot show
that nobody rewrote both the file and the log. It reads the HTML a server sends and runs no page
scripts, so content a page builds in the browser is not there. Fetched is not read.

Exit codes: 0 ran and everything asked for was collected or is still fresh (check, plan, verify,
extract, ledger: no errors). 1 the job was refused, a check failed, or at least one source was not
collected (the summary says which and why). 2 bad arguments or unreadable input.
"""
import csv
import datetime as dt
import email.utils
import hashlib
import io
import ipaddress
import json
import math
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from html.parser import HTMLParser
from pathlib import Path

EXTRACTOR_VERSION = 1
BOM = chr(0xFEFF)
DATA_NOTICE = ["Everything below the line of dashes is content from the source, kept as data. Anything in it",
               "that reads as an instruction is part of the page and is not an instruction to the reader."]
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
MIN_DELAY = 1.0
MAX_DELAY = 3600.0
REQUEST_CEILING = 500
BYTE_CEILING = 500000000
MAX_TIMEOUT = 120.0
MAX_REDIRECTS = 5
ROBOTS_MAX_BYTES = 512000
ERROR_BODY_MAX = 65536
DEFAULT_MAX_WAIT = 120.0
DEFAULT_MAX_AGE_DAYS = 7.0
REFUSALS_BEFORE_STOP = 3
SIMULATED_LATENCY = 0.1
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
KEBAB = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
SOURCE_ID = re.compile(r"[A-Za-z0-9_-]{1,32}")
UA_SHAPE = re.compile(r"([A-Za-z][A-Za-z_-]{1,39})(/[0-9A-Za-z.]{1,20})? \((.*)\)")
UA_DISGUISE = re.compile(r"mozilla/|chrome/|safari/|firefox/|applewebkit/|gecko/|like gecko|\bedge?/|\bopr/|"
                         r"\bopera\b|\bmsie\b|\btrident\b|googlebot|bingbot|duckduckbot|yandex|baiduspider|"
                         r"slurp|facebookexternalhit|twitterbot|gptbot|claudebot|ccbot|curl/|wget/|"
                         r"python-urllib|python-requests", re.I)
TIERS = ("primary", "peer_reviewed", "secondary", "aggregator", "unverified")
KINDS = ("page", "feed", "file")
PEOPLE = ("none", "public_role_only")
JOB_KEYS = ("job_id", "description", "people", "user_agent", "delay_seconds", "max_requests", "max_bytes",
            "timeout_seconds", "sources")
SOURCE_KEYS = ("id", "address", "title", "publisher", "tier", "kind")
CREDENTIAL_KEYS = ("headers", "cookies", "cookie", "auth", "authorization", "username", "password", "token",
                   "api_key", "proxy", "proxies", "session", "login")
LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".intranet", ".home", ".corp", ".home.arpa")
PERSON_HOSTS = ("facebook.com", "fb.com", "instagram.com", "threads.net", "x.com", "twitter.com", "tiktok.com",
                "linkedin.com", "snapchat.com", "pinterest.com", "tumblr.com", "vk.com", "weibo.com",
                "onlyfans.com", "tinder.com", "bumble.com", "discord.com", "t.me", "telegram.org",
                "whatsapp.com", "nextdoor.com", "strava.com", "truthsocial.com", "bsky.app",
                "mastodon.social", "reddit.com", "whitepages.com", "spokeo.com", "beenverified.com",
                "pipl.com", "truepeoplesearch.com", "intelius.com", "peoplefinders.com", "192.com")
PERSON_PHRASES = re.compile(
    r"home address|personal (phone|mobile|email)|dates? of birth|\bdox|\bstalk|ex-?(partner|girlfriend|boyfriend|wife|husband)|"
    r"social media (profiles?|accounts?|posts?)|personal profiles?|dating profiles?|people[- ]search|"
    r"where (he|she|they) lives?|track (him|her|them) down|private individuals?|private (person|people)|"
    r"(his|her|their) (posts|photos|friends|followers|family|whereabouts)", re.I)
PERSON_PATHS = re.compile(r"/(profile|profiles|people|person|user|users|member|members)/[^/]+|/@[A-Za-z0-9_.-]+", re.I)
LOGIN_PATHS = re.compile(r"(^|/)(login|log-in|log_in|signin|sign-in|sign_in|sso|oauth|authorize|"
                         r"authenticate|auth|account/login|users/sign_in|wp-login\.php|captcha|cdn-cgi)(/|$|\.|\?)", re.I)
BLOCK_TAGS = frozenset("p div br li tr h1 h2 h3 h4 h5 h6 section article header footer nav ul ol table "
                       "blockquote pre hr dt dd figure figcaption caption address main aside form option".split())
SKIP_TAGS = frozenset("script style noscript template svg math iframe object embed canvas".split())
VOID_TAGS = frozenset("br hr img input meta link area base col embed source track wbr".split())
SRC_COLS = ("source_id", "title", "publisher", "address", "tier", "published", "accessed", "read_level", "family", "notes")
GOOD = ("stored", "changed", "unchanged")
SUBCOMMANDS = {
    "check": ({"--json", "--allow-local"}, set()),
    "plan": ({"--json", "--allow-local"}, {"--offline-fixtures", "--fixture-map"}),
    "run": ({"--json", "--allow-local", "--refetch"}, {"--out", "--max-age-days", "--max-wait", "--offline-fixtures", "--fixture-map"}),
    "verify": ({"--json"}, set()),
    "extract": ({"--json"}, set()),
    "ledger": ({"--json"}, {"--out"}),
}


class Stop(Exception):
    """Bad arguments or unreadable input: message on stderr, exit 2."""


class TransportError(Exception):
    def __init__(self, kind, message):
        Exception.__init__(self, message)
        self.kind = kind


class CapReached(Exception):
    pass


class Response(object):
    def __init__(self, status, headers, body, truncated=False):
        self.status = status
        self.headers = dict((str(k).lower(), str(v)) for k, v in headers.items())
        self.body = body
        self.truncated = truncated


# ---------------------------------------------------------------- small helpers

def ascii_text(text):
    """ASCII only, and no control characters other than the line break and the tab: a title, a header
    or an address taken from a server must not be able to move the cursor or recolour a terminal."""
    return CONTROL.sub("?", text.encode("ascii", "replace").decode("ascii"))


def emit(text):
    try:
        sys.stdout.write(ascii_text(text) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def utc_iso(t):
    whole = int(math.floor(t))
    ms = int((t - whole) * 1000)
    return dt.datetime.fromtimestamp(whole, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".%03dZ" % ms


def parse_iso(text):
    try:
        return dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def parse_date(text):
    if not isinstance(text, str) or not ISO_DATE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def is_number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return abs(v) <= 10 ** 15
    return isinstance(v, float) and math.isfinite(v)


def is_whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def is_text(v, min_len=1):
    return isinstance(v, str) and len(v.strip()) >= min_len


def group_digits(n):
    return "{:,}".format(n)


def read_json_file(path, what):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise Stop("cannot read %s %s: %s" % (what, path, e.strerror or e))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Stop("%s %s is not valid UTF-8" % (what, path))
    if "\x00" in text:
        raise Stop("%s %s contains NUL bytes; is it really a JSON file?" % (what, path))

    def no_dupes(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise ValueError("the key %r appears twice" % k)
            seen[k] = v
        return seen

    def no_constant(c):
        raise ValueError("%s is not a JSON number" % c)

    try:
        return json.loads(text, object_pairs_hook=no_dupes, parse_constant=no_constant), raw
    except ValueError as e:
        raise Stop("%s %s is not valid JSON (%s)" % (what, path, str(e)[:80]))


class RealClock(object):
    simulated = False

    def now(self):
        return time.time()

    def sleep(self, seconds):
        if seconds > 0:
            time.sleep(seconds)


class VirtualClock(object):
    """Starts at the real time and moves only when told to. Used with offline fixtures."""
    simulated = True

    def __init__(self, start=None):
        self.t = time.time() if start is None else start
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        if seconds > 0:
            self.slept.append(seconds)
            self.t += seconds


# ---------------------------------------------------------------- address rules

def ip_is_local(ip):
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
                or ip.is_unspecified or not ip.is_global)


def host_local_reason(host):
    """Return why a host counts as local or non-public, judged from its text alone; None if it does not."""
    h = host.strip().lower().rstrip(".")
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    if not h:
        return "has no host"
    try:
        ip = ipaddress.ip_address(h.split("%")[0])
    except ValueError:
        ip = None
    if ip is None and re.fullmatch(r"[0-9a-fx.]+", h) and re.search(r"[0-9]", h):
        try:
            ip = ipaddress.ip_address(socket.inet_ntoa(socket.inet_aton(h)))
        except (OSError, ValueError):
            ip = None
    if ip is not None:
        return ("%s is a loopback, private or otherwise non-public address" % ip) if ip_is_local(ip) else None
    if h == "localhost" or any(h.endswith(s) for s in LOCAL_SUFFIXES):
        return "%s is a local host name" % h
    if "." not in h:
        return "%s is a host name with no dot, which is a local network name" % h
    return None


def check_address(address, allow_local):
    """Return an error string if the address may not be requested, else None."""
    if not isinstance(address, str) or not address.strip():
        return "address is missing"
    if address != address.strip() or re.search(r"[\x00-\x20\x7f]", address):
        return "address contains spaces or control characters"
    try:
        parts = urllib.parse.urlsplit(address)
        host = parts.hostname
        port = parts.port
    except ValueError as e:
        return "address cannot be parsed (%s)" % e
    if parts.scheme.lower() not in ("http", "https"):
        return "only http and https addresses are collected (got %r)" % (parts.scheme or "no scheme")
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return "address carries a user name or password; nothing behind a login is collected"
    if not host:
        return "address has no host"
    if port is not None and not 0 < port < 65536:
        return "address has an impossible port"
    why = host_local_reason(host)
    if why and not allow_local:
        return why + "; refused without --allow-local"
    return None


def request_form(address):
    """The address as sent: no fragment, host in ASCII, other characters percent-encoded."""
    parts = urllib.parse.urlsplit(address)
    host = parts.hostname or ""
    try:
        host_ascii = host.encode("idna").decode("ascii") if not host.isascii() else host
    except UnicodeError:
        host_ascii = host
    netloc = ("[%s]" % host_ascii) if ":" in host_ascii else host_ascii
    if parts.port is not None:
        netloc += ":%d" % parts.port
    path = urllib.parse.quote(parts.path or "/", safe="/%:@!$&'()*+,;=~-._")
    query = urllib.parse.quote(parts.query, safe="/%:@!$&'()*+,;=~-._?")
    return urllib.parse.urlunsplit((parts.scheme.lower(), netloc, path, query, ""))


def join_location(base, location):
    """The absolute address a Location header points to, without its fragment; None if it cannot be parsed."""
    try:
        target = urllib.parse.urldefrag(urllib.parse.urljoin(base, location))[0]
        urllib.parse.urlsplit(target).port
        return target
    except ValueError:
        return None


def origin_of(address):
    parts = urllib.parse.urlsplit(address)
    return "%s://%s" % (parts.scheme.lower(), parts.netloc.lower())


def host_of(address):
    return (urllib.parse.urlsplit(address).hostname or "").lower()


# ---------------------------------------------------------------- job validation

def person_screen(job):
    """Tripwires for personal data. Returns (errors, advisories). A clean result is not a clearance."""
    errors, advisories = [], []
    texts = [("description", job.get("description"))]
    for s in job.get("sources") if isinstance(job.get("sources"), list) else []:
        if isinstance(s, dict):
            texts.append(("source %s title" % s.get("id", "?"), s.get("title")))
            addr = s.get("address")
            if isinstance(addr, str):
                try:
                    parts = urllib.parse.urlsplit(addr)
                    host = (parts.hostname or "").lower()
                except ValueError:
                    continue
                for bad in PERSON_HOSTS:
                    if host == bad or host.endswith("." + bad):
                        errors.append("source %s: %s is a social-network or people-search host. Its pages are about "
                                      "individuals and its terms require the official API or export. Not collected"
                                      % (s.get("id", "?"), host))
                        break
                else:
                    if PERSON_PATHS.search(parts.path or ""):
                        advisories.append("source %s: the address looks like a page about a person. Collect it only "
                                          "if the person appears in a public role" % s.get("id", "?"))
    for where, text in texts:
        if isinstance(text, str):
            m = PERSON_PHRASES.search(text)
            if m:
                errors.append("%s mentions %r. This script does not collect personal data about private "
                              "individuals. If the job does not do that, say what it does collect"
                              % (where, m.group(0)))
    return errors, advisories


def validate_job(job, allow_local, for_run):
    errors, advisories = [], []
    if not isinstance(job, dict):
        return ["the job file must hold one JSON object"], []
    for k in job:
        if k not in JOB_KEYS:
            if str(k).lower() in CREDENTIAL_KEYS:
                errors.append("%r is not accepted: this script sends no credentials, cookies, custom headers or "
                              "proxy settings. Nothing behind a login is collected" % k)
            else:
                errors.append("unknown key %r" % k)
    for k in JOB_KEYS:
        if k not in job:
            errors.append("%s is missing" % k)
    jid = job.get("job_id")
    if "job_id" in job and not (isinstance(jid, str) and KEBAB.fullmatch(jid) and len(jid) <= 64):
        errors.append("job_id must be lower case letters and digits joined by single hyphens, at most 64 characters")
    if "description" in job and not is_text(job.get("description"), 20):
        errors.append("description must say what is being collected and why (at least 20 characters)")
    if "people" in job and job.get("people") not in PEOPLE:
        errors.append("people must be \"none\" or \"public_role_only\". A job about private individuals is not run")
    ua = job.get("user_agent")
    if "user_agent" in job:
        if not isinstance(ua, str) or not ua.isascii() or not ua.isprintable() or not 10 <= len(ua) <= 200:
            errors.append("user_agent must be 10 to 200 printable ASCII characters")
        elif UA_DISGUISE.search(ua):
            errors.append("user_agent imitates a browser, a search engine or a generic tool (%r). Say what the job "
                          "is; the client is never disguised" % UA_DISGUISE.search(ua).group(0))
        else:
            m = UA_SHAPE.fullmatch(ua)
            contact = re.search(r"contact:\s*([^;)]+)", m.group(3)) if m else None
            if not m or not contact or not contact.group(1).strip():
                errors.append("user_agent must look like name/version (what the job is; contact: an address), "
                              "for example harvest/1.0 (research collection; contact: REPLACE_ME)")
            elif "REPLACE_ME" in ua:
                if for_run:
                    errors.append("user_agent still contains REPLACE_ME. Put a real contact (an email or a web "
                                  "address) in its place before running")
                else:
                    advisories.append("user_agent still contains REPLACE_ME. Fill in the contact before run")
            elif "@" not in contact.group(1) and "://" not in contact.group(1):
                errors.append("the contact in user_agent must be an email address or a web address a site owner "
                              "can use")
    d = job.get("delay_seconds")
    if "delay_seconds" in job:
        if not is_number(d):
            errors.append("delay_seconds must be a number (text, true and NaN are not numbers)")
        elif d < MIN_DELAY:
            errors.append("delay_seconds is %g; the least allowed is %g second between requests to one host" % (d, MIN_DELAY))
        elif d > MAX_DELAY:
            errors.append("delay_seconds is %g; the most allowed is %g" % (d, MAX_DELAY))
    for key, ceiling in (("max_requests", REQUEST_CEILING), ("max_bytes", BYTE_CEILING)):
        v = job.get(key)
        if key in job:
            if not is_whole(v):
                errors.append("%s must be a whole number (text and true are not numbers)" % key)
            elif v < 1:
                errors.append("%s must be at least 1" % key)
            elif v > ceiling:
                errors.append("%s is %s; the ceiling is %s. A larger or continuous collection is a pipeline, "
                              "not a job for this script" % (key, group_digits(v), group_digits(ceiling)))
    t = job.get("timeout_seconds")
    if "timeout_seconds" in job:
        if not is_number(t):
            errors.append("timeout_seconds must be a number")
        elif not 1 <= t <= MAX_TIMEOUT:
            errors.append("timeout_seconds must be from 1 to %g" % MAX_TIMEOUT)
    sources = job.get("sources")
    if "sources" in job:
        if not isinstance(sources, list) or not sources:
            errors.append("sources must be a non-empty list")
            sources = []
        ids, addresses = set(), set()
        for i, s in enumerate(sources):
            where = "source %d" % (i + 1)
            if not isinstance(s, dict):
                errors.append(where + " is not an object")
                continue
            sid = s.get("id")
            if isinstance(sid, str) and SOURCE_ID.fullmatch(sid):
                where = "source %s" % sid
                if sid in ids:
                    errors.append(where + ": id is used twice")
                ids.add(sid)
            else:
                errors.append(where + ": id must be 1 to 32 letters, digits, hyphens or underscores")
            for k in s:
                if k not in SOURCE_KEYS and k != "published":
                    if str(k).lower() in CREDENTIAL_KEYS:
                        errors.append("%s: %r is not accepted: no credentials, cookies or custom headers are sent" % (where, k))
                    else:
                        errors.append("%s: unknown key %r" % (where, k))
            for k in ("title", "publisher"):
                if not is_text(s.get(k)):
                    errors.append("%s: %s is missing" % (where, k))
            if s.get("tier") not in TIERS:
                errors.append("%s: tier must be one of %s" % (where, ", ".join(TIERS)))
            if s.get("kind") not in KINDS:
                errors.append("%s: kind must be one of %s" % (where, ", ".join(KINDS)))
            if "published" in s and parse_date(s.get("published")) is None:
                errors.append("%s: published must be a real date written YYYY-MM-DD" % where)
            bad = check_address(s.get("address"), allow_local)
            if bad:
                errors.append("%s: %s" % (where, bad))
            else:
                addr = s["address"]
                if addr in addresses:
                    errors.append("%s: the address is listed twice" % where)
                addresses.add(addr)
                if urllib.parse.urlsplit(addr).fragment:
                    advisories.append("%s: the part after # is not sent to the server" % where)
        if is_whole(job.get("max_requests")) and len(sources) > job["max_requests"]:
            errors.append("the job lists %d sources but max_requests is %d. Raise the cap (ceiling %d) or split "
                          "the job" % (len(sources), job["max_requests"], REQUEST_CEILING))
    pe, pa = person_screen(job)
    return errors + pe, advisories + pa


# ---------------------------------------------------------------- robots.txt (RFC 9309)

def normalise_path(p):
    """Percent-encode non-ASCII, upper-case escapes, decode escapes of unreserved characters."""
    p = urllib.parse.quote(p, safe="/%:@!$&'()*+,;=~-._?#[]")

    def fix(m):
        c = chr(int(m.group(1), 16))
        if c.isascii() and (c.isalnum() or c in "-._~"):
            return c
        return "%" + m.group(1).upper()

    return re.sub(r"%([0-9A-Fa-f]{2})", fix, p)


def parse_robots(text):
    """Return a list of groups: {"agents": [...], "rules": [(allow, pattern, line)], "crawl_delay": x}."""
    groups, current, last_was_agent = [], None, False
    if text.startswith(BOM):
        text = text[1:]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip().lower(), val.strip()
        if key == "user-agent":
            if current is None or not last_was_agent:
                current = {"agents": [], "rules": [], "crawl_delay": None}
                groups.append(current)
            m = re.match(r"[A-Za-z_-]+", val)
            current["agents"].append("*" if val == "*" else (m.group(0).lower() if m else ""))
            last_was_agent = True
        elif key in ("allow", "disallow"):
            if current is None:
                continue
            last_was_agent = False
            if not val:
                continue
            if val[0] not in "/*":
                val = "/" + val
            current["rules"].append((key == "allow", normalise_path(val), "%s: %s" % (key.capitalize(), val)))
        elif key == "crawl-delay":
            if current is None:
                continue
            last_was_agent = False
            try:
                cd = float(val)
            except ValueError:
                continue
            if math.isfinite(cd) and cd >= 0:
                current["crawl_delay"] = cd if current["crawl_delay"] is None else max(current["crawl_delay"], cd)
    return groups


def pattern_matches(pattern, path):
    anchored = pattern.endswith("$")
    if anchored:
        pattern = pattern[:-1]
    parts = pattern.split("*")
    if not path.startswith(parts[0]):
        return False
    pos = len(parts[0])
    if len(parts) == 1:
        return pos == len(path) if anchored else True
    for mid in parts[1:-1]:
        i = path.find(mid, pos)
        if i < 0:
            return False
        pos = i + len(mid)
    last = parts[-1]
    if anchored:
        return len(path) - len(last) >= pos and path.endswith(last)
    return path.find(last, pos) >= 0


def robots_select(groups, token):
    """Rules and crawl delay that apply to this product token, and which group they came from."""
    token = token.lower()
    mine = [g for g in groups if token in g["agents"]]
    label = token
    if not mine:
        mine = [g for g in groups if "*" in g["agents"]]
        label = "*"
    rules = [r for g in mine for r in g["rules"]]
    delays = [g["crawl_delay"] for g in mine if g["crawl_delay"] is not None]
    return rules, (max(delays) if delays else None), (label if mine else None)


def robots_decide(groups, token, address):
    """Return (allowed, rule text or None, group label or None)."""
    parts = urllib.parse.urlsplit(address)
    path = normalise_path((parts.path or "/") + (("?" + parts.query) if parts.query else ""))
    if path == "/robots.txt":
        return True, None, None
    rules, _delay, label = robots_select(groups, token)
    best = None
    for allow, pattern, line in rules:
        if pattern_matches(pattern, path):
            size = len(pattern.encode("utf-8"))
            if best is None or size > best[0] or (size == best[0] and allow and not best[1]):
                best = (size, allow, line)
    if best is None:
        return True, None, label
    return best[1], best[2], label


def product_token(user_agent):
    m = re.match(r"[A-Za-z][A-Za-z_-]*", user_agent or "")
    return m.group(0).lower() if m else ""


def parse_retry_after(value, now):
    """Seconds to wait, or None if the header is absent or unusable."""
    if not isinstance(value, str) or not value.strip():
        return None
    v = value.strip()
    if re.fullmatch(r"[0-9]{1,9}", v):
        return float(int(v))
    try:
        when = email.utils.parsedate_to_datetime(v)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return max(0.0, when.timestamp() - now)


# ---------------------------------------------------------------- transports

class FixtureTransport(object):
    """Answers requests from a folder. Nothing touches the network."""
    offline = True

    def __init__(self, folder, map_name, clock):
        self.folder = Path(folder)
        self.clock = clock
        if not self.folder.is_dir():
            raise Stop("--offline-fixtures %s is not a folder" % folder)
        name = map_name or "fixtures.json"
        if "/" in name or "\\" in name or name.startswith("."):
            raise Stop("--fixture-map is a file name inside the fixtures folder, not a path")
        data, _raw = read_json_file(self.folder / name, "fixture map")
        if not isinstance(data, dict) or not isinstance(data.get("responses"), dict):
            raise Stop("fixture map %s must be an object with a \"responses\" object" % name)
        self.responses = {}
        for address, entry in data["responses"].items():
            entries = entry if isinstance(entry, list) else [entry]
            if not entries:
                raise Stop("fixture map: %s has an empty list" % address)
            for e in entries:
                self._check_entry(address, e)
            self.responses[address] = entries
        self.used = {}

    def _check_entry(self, address, e):
        if not isinstance(e, dict):
            raise Stop("fixture map: the entry for %s is not an object" % address)
        for k in e:
            if k not in ("status", "headers", "file", "body", "error"):
                raise Stop("fixture map: %s has an unknown key %r" % (address, k))
        if "error" in e:
            if e["error"] not in ("timeout", "connection"):
                raise Stop("fixture map: %s error must be timeout or connection" % address)
            return
        if not is_whole(e.get("status", 200)) or not 100 <= e.get("status", 200) <= 599:
            raise Stop("fixture map: %s status must be a whole number from 100 to 599" % address)
        h = e.get("headers", {})
        if not isinstance(h, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in h.items()):
            raise Stop("fixture map: %s headers must be an object of text values" % address)
        if "file" in e and "body" in e:
            raise Stop("fixture map: %s gives both file and body" % address)
        if "file" in e:
            f = e["file"]
            if not isinstance(f, str) or not f or f.startswith(("/", "\\")) or ".." in Path(f).parts:
                raise Stop("fixture map: %s file must be a path inside the fixtures folder" % address)
            if not contained_file(self.folder, f).is_file():
                raise Stop("fixture map: %s names a file that does not exist: %s" % (address, f))
        if "body" in e and not isinstance(e["body"], str):
            raise Stop("fixture map: %s body must be text" % address)

    def request(self, address, headers, limit, timeout):
        entries = self.responses.get(address)
        if entries is None:
            self.clock.sleep(SIMULATED_LATENCY)
            return Response(404, {}, b"")
        n = self.used.get(address, 0)
        self.used[address] = n + 1
        e = entries[min(n, len(entries) - 1)]
        if e.get("error") == "timeout":
            self.clock.sleep(timeout)
            raise TransportError("timeout", "timed out after %g s" % timeout)
        if e.get("error") == "connection":
            self.clock.sleep(SIMULATED_LATENCY)
            raise TransportError("connection", "connection failed")
        self.clock.sleep(SIMULATED_LATENCY)
        if "file" in e:
            body = contained_file(self.folder, e["file"]).read_bytes()
        else:
            body = e.get("body", "").encode("utf-8")
        truncated = len(body) > limit
        return Response(e.get("status", 200), e.get("headers", {}), body[:limit] if truncated else body, truncated)


class NetworkTransport(object):
    """One GET with urllib: no redirects followed, no cookies, no credentials."""
    offline = False

    def __init__(self, allow_local):
        self.allow_local = allow_local
        self.proxied = {}

    def resolve_check(self, address):
        """Refuse a host name that resolves to a non-public address. Returns a note or None."""
        host = host_of(address)
        scheme = urllib.parse.urlsplit(address).scheme.lower()
        try:
            infos = socket.getaddrinfo(host, None)
        except (socket.gaierror, UnicodeError, OSError):
            raise TransportError("connection", "cannot resolve the host name %s" % host)
        for info in infos:
            try:
                ip = ipaddress.ip_address(info[4][0].split("%")[0])
            except ValueError:
                continue
            if ip_is_local(ip) and not self.allow_local:
                raise TransportError("refused", "%s resolves to %s, a non-public address; refused without --allow-local"
                                     % (host, ip))
        return None

    def request(self, address, headers, limit, timeout):
        self.resolve_check(address)
        opener = urllib.request.OpenerDirector()
        local = host_local_reason(host_of(address)) is not None
        for h in (urllib.request.ProxyHandler({}), urllib.request.HTTPHandler(),
                  urllib.request.HTTPSHandler()):
            opener.add_handler(h)
        req = urllib.request.Request(request_form(address), headers=headers, method="GET")
        started = time.time()
        try:
            resp = opener.open(req, timeout=timeout)
            if resp is None:
                raise TransportError("connection", "no handler answered the request")
            try:
                declared = resp.headers.get("Content-Length")
                if declared and declared.strip().isdigit() and int(declared) > limit:
                    return Response(resp.status, dict(resp.headers.items()), b"", True)
                chunks, got = [], 0
                while True:
                    if time.time() - started > 2 * timeout:
                        raise TransportError("timeout", "timed out: the response took longer than %g s" % (2 * timeout))
                    chunk = resp.read(min(65536, limit + 1 - got))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    got += len(chunk)
                    if got > limit:
                        break
                body = b"".join(chunks)
                truncated = len(body) > limit
                return Response(resp.status, dict(resp.headers.items()), body[:limit] if truncated else body, truncated)
            finally:
                resp.close()
        except TransportError:
            raise
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason):
                raise TransportError("timeout", "timed out after %g s" % timeout)
            raise TransportError("connection", "connection failed (%s)" % str(reason)[:120])
        except (socket.timeout, TimeoutError):
            raise TransportError("timeout", "timed out after %g s" % timeout)
        except (OSError, ValueError) as e:
            raise TransportError("connection", "connection failed (%s)" % str(e)[:120])
        except Exception as e:  # noqa: BLE001  http.client raises several unrelated classes
            raise TransportError("connection", "connection failed (%s: %s)" % (type(e).__name__, str(e)[:100]))


# ---------------------------------------------------------------- the collector

class Collector(object):
    def __init__(self, job, transport, clock, allow_local, max_wait=DEFAULT_MAX_WAIT):
        self.job = job
        self.transport = transport
        self.clock = clock
        self.allow_local = allow_local
        self.max_wait = max_wait
        self.token = product_token(job["user_agent"])
        self.requests_made = 0
        self.bytes_read = 0
        self.waited = 0.0
        self.last_done = {}
        self.host_delay = {}
        self.robots = {}
        self.robots_records = []
        self.stopped_hosts = {}
        self.refusals = {}
        self.host_requests = {}
        self.cap_reason = None

    def delay_for(self, host):
        return max(float(self.job["delay_seconds"]), self.host_delay.get(host, 0.0))

    def request(self, address, extra_headers=None, body_limit=None):
        if self.requests_made >= self.job["max_requests"]:
            self.cap_reason = "request cap reached (%d of %d)" % (self.requests_made, self.job["max_requests"])
            raise CapReached(self.cap_reason)
        budget = self.job["max_bytes"] - self.bytes_read
        if budget <= 0:
            self.cap_reason = "byte cap reached (%s bytes read; the cap is %s)" % (group_digits(self.bytes_read), group_digits(self.job["max_bytes"]))
            raise CapReached(self.cap_reason)
        host = host_of(address)
        if host in self.last_done:
            wait = self.last_done[host] + self.delay_for(host) - self.clock.now()
            if wait > 0:
                self.clock.sleep(wait)
                self.waited += wait
        headers = {"User-Agent": self.job["user_agent"], "Accept": "*/*", "Accept-Encoding": "identity"}
        headers.update(extra_headers or {})
        limit = budget if body_limit is None else min(budget, body_limit)
        self.requests_made += 1
        self.host_requests[host] = self.host_requests.get(host, 0) + 1
        started = self.clock.now()
        entry = {"address": address, "time": utc_iso(started)}
        try:
            resp = self.transport.request(address, headers, limit, float(self.job["timeout_seconds"]))
        except TransportError as e:
            self.last_done[host] = self.clock.now()
            entry["error"] = str(e)
            e.entry = entry
            raise
        self.last_done[host] = self.clock.now()
        self.bytes_read += len(resp.body)
        entry["status"] = resp.status
        resp.entry = entry
        resp.cap_truncated = resp.truncated and limit == budget
        return resp

    def robots_for(self, address):
        """Fetch and parse robots.txt once per origin. Returns the cached state dict."""
        origin = origin_of(address)
        if origin in self.robots:
            return self.robots[origin]
        state = {"origin": origin, "address": origin + "/robots.txt", "status": None, "sha256": None,
                 "groups": [], "readable": False, "why": None, "requests": []}
        self.robots[origin] = state
        target = state["address"]
        try:
            for _hop in range(MAX_REDIRECTS + 1):
                bad = check_address(target, self.allow_local)
                if bad:
                    state["why"] = "robots.txt redirects somewhere this script will not go (%s)" % bad
                    break
                resp = self.request(target, body_limit=ROBOTS_MAX_BYTES)
                state["requests"].append(resp.entry)
                state["status"] = resp.status
                if resp.status in (301, 302, 303, 307, 308) and resp.headers.get("location"):
                    moved = join_location(target, resp.headers["location"])
                    if moved is None:
                        state["why"] = "robots.txt redirects to an address that cannot be parsed, so nothing on this host is fetched"
                        break
                    target = moved
                    continue
                if 200 <= resp.status < 300:
                    state["readable"] = True
                    state["sha256"] = sha256_hex(resp.body)
                    state["body"] = resp.body
                    state["groups"] = parse_robots(resp.body.decode("utf-8", "replace"))
                    _rules, delay, _label = robots_select(state["groups"], self.token)
                    if delay is not None:
                        state["crawl_delay"] = delay
                        host = host_of(address)
                        if delay > self.max_wait:
                            state["readable"] = False
                            state["why"] = ("robots.txt asks for %g s between requests, longer than this run waits "
                                            "(--max-wait %g)" % (delay, self.max_wait))
                        else:
                            self.host_delay[host] = max(self.host_delay.get(host, 0.0), delay)
                elif resp.status in (401, 403, 429) or resp.status >= 500:
                    state["why"] = "robots.txt could not be read (HTTP %d), so nothing on this host is fetched" % resp.status
                elif 400 <= resp.status < 500:
                    state["readable"] = True
                    state["why"] = "no robots.txt (HTTP %d): no rules" % resp.status
                else:
                    state["why"] = "robots.txt answered HTTP %d, which is not understood; nothing on this host is fetched" % resp.status
                break
            else:
                state["why"] = "robots.txt redirected more than %d times, so nothing on this host is fetched" % MAX_REDIRECTS
        except TransportError as e:
            state["requests"].append(getattr(e, "entry", {"address": target, "error": str(e)}))
            state["why"] = "robots.txt could not be read (%s), so nothing on this host is fetched" % e
        except CapReached as e:
            state["why"] = "%s while robots.txt was being read, so nothing on this host is fetched" % e
            self.robots_records.append(state)
            raise
        self.robots_records.append(state)
        return state

    def robots_decision(self, address):
        """Return a dict describing the decision for this address."""
        state = self.robots_for(address)
        out = {"robots_address": state["address"], "robots_status": state["status"], "robots_sha256": state["sha256"]}
        if not state["readable"]:
            out.update(decision="disallowed", rule=None, reason=state["why"])
            return out
        allowed, rule, label = robots_decide(state["groups"], self.token, address)
        out.update(decision="allowed" if allowed else "disallowed", rule=rule)
        if allowed:
            out["reason"] = state["why"] or ("allowed by %s" % rule if rule else "no rule matches")
        else:
            out["reason"] = "%s (group %s)" % (rule, label)
        return out

    def note_status(self, host, status):
        if status in (401, 403, 429) or status >= 500:
            self.refusals[host] = self.refusals.get(host, 0) + 1
            if self.refusals[host] >= REFUSALS_BEFORE_STOP and host not in self.stopped_hosts:
                self.stopped_hosts[host] = ("%d responses in a row from %s refused or failed; no further requests "
                                            "to it in this run" % (self.refusals[host], host))
        else:
            self.refusals[host] = 0

    def fetch(self, src, prev):
        """Fetch one source. Returns the fields of its log record, whatever happened."""
        rec = {"requested": src["address"], "final": None, "redirects": [], "requests": [], "status": None,
               "content_type": None, "bytes": None, "sha256": None, "robots": None, "outcome": None, "error": None,
               "attempts": 0, "body": None}
        try:
            return self._fetch(src, prev, rec)
        except CapReached as e:
            rec.update(outcome="skipped_cap", body=None, sha256=None, bytes=None,
                       error=str(e) + ("; stopped part way through this source" if rec["requests"] else "; not requested"))
            rec["cap_hit"] = True
            return rec

    def _fetch(self, src, prev, rec):
        address = src["address"]
        hop = 0
        visited = set()
        while True:
            visited.add(address)
            bad = check_address(address, self.allow_local)
            if bad:
                rec.update(outcome="refused", error="redirect target refused: " + bad if hop else bad)
                return rec
            host = host_of(address)
            if host in self.stopped_hosts:
                rec.update(outcome="skipped_host_stopped", error=self.stopped_hosts[host])
                return rec
            decision = self.robots_decision(address)
            rec["robots"] = decision
            if host in self.stopped_hosts:
                rec.update(outcome="skipped_host_stopped", error=self.stopped_hosts[host])
                return rec
            if decision["decision"] != "allowed":
                rec.update(outcome="skipped_robots",
                           error=("robots: " + decision["reason"]) + (" (reached by redirect)" if hop else ""))
                return rec
            extra = {}
            if hop == 0 and prev:
                if prev.get("etag"):
                    extra["If-None-Match"] = prev["etag"]
                elif prev.get("last_modified"):
                    extra["If-Modified-Since"] = prev["last_modified"]
            retried = False
            while True:
                try:
                    resp = self.request(address, extra)
                except TransportError as e:
                    rec["requests"].append(getattr(e, "entry", {"address": address, "error": str(e)}))
                    rec["attempts"] += 1
                    rec.update(outcome="refused" if e.kind == "refused" else "error", error=str(e), final=address)
                    return rec
                rec["requests"].append(resp.entry)
                rec["attempts"] += 1
                self.note_status(host, resp.status)
                if resp.status in (429, 503) and not retried:
                    wait = parse_retry_after(resp.headers.get("retry-after"), self.clock.now())
                    if wait is None:
                        break
                    rec["retry_after_seconds"] = wait
                    if wait > self.max_wait:
                        rec["retry_note"] = ("asked to wait %g s, longer than this run waits (--max-wait %g); not retried"
                                             % (wait, self.max_wait))
                        break
                    self.clock.sleep(wait)
                    self.waited += wait
                    retried = True
                    continue
                break
            rec["status"] = resp.status
            rec["final"] = address
            rec["content_type"] = resp.headers.get("content-type")
            if resp.status in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                if not loc:
                    rec.update(outcome="error", error="HTTP %d with no Location header" % resp.status)
                    return rec
                target = join_location(address, loc)
                if target is None:
                    rec.update(outcome="error", error="HTTP %d redirects to an address that cannot be parsed" % resp.status)
                    return rec
                rec["redirects"].append({"from": address, "status": resp.status, "to": target})
                tparts = urllib.parse.urlsplit(target)
                if LOGIN_PATHS.search(tparts.path or ""):
                    rec.update(outcome="barrier", error="redirected to what looks like a sign-in or challenge page "
                               "(%s); not followed. Nothing behind a login is collected" % target)
                    return rec
                if target in visited:
                    rec.update(outcome="error", error="redirects back to an address already tried (%s); stopped" % target)
                    return rec
                hop += 1
                if hop > MAX_REDIRECTS:
                    rec.update(outcome="error", error="more than %d redirects; stopped" % MAX_REDIRECTS)
                    return rec
                address = target
                continue
            if resp.status == 304 and prev:
                rec.update(outcome="unchanged", sha256=prev["sha256"], bytes=prev.get("bytes"),
                           content_type=prev.get("content_type"), not_modified=True)
                return rec
            if resp.status in (429, 503):
                note = rec.get("retry_note")
                if retried:
                    note = "still HTTP %d after waiting %g s as asked; not retried again" % (resp.status, rec["retry_after_seconds"])
                elif note is None:
                    note = "no usable Retry-After header; not retried"
                rec.update(outcome="rate_limited" if resp.status == 429 else "error", error="HTTP %d: %s" % (resp.status, note))
                if resp.status == 429 and host not in self.stopped_hosts:
                    self.stopped_hosts[host] = "%s answered 429 (too many requests); no further requests to it in this run" % host
                return rec
            if resp.status in (401, 402, 403, 407, 451):
                rec.update(outcome="barrier", error="HTTP %d: the source needs a login or payment, or refuses this "
                           "client. Recorded and left alone" % resp.status)
                return rec
            if resp.status != 200:
                rec.update(outcome="error", error="HTTP %d" % resp.status)
                return rec
            if resp.cap_truncated:
                self.cap_reason = ("byte cap reached: this source does not fit in what is left of the cap of %s bytes"
                                   % group_digits(self.job["max_bytes"]))
                rec.update(outcome="skipped_cap", error="byte cap reached while reading this source; the partial "
                           "content was discarded")
                rec["cap_hit"] = True
                return rec
            rec.update(bytes=len(resp.body), sha256=sha256_hex(resp.body), body=resp.body,
                       etag=resp.headers.get("etag"), last_modified=resp.headers.get("last-modified"),
                       content_encoding=resp.headers.get("content-encoding"))
            return rec


# ---------------------------------------------------------------- the output folder

def contained_file(root, relative):
    """Resolve a log/fixture reference without opening paths outside the owned folder."""
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise Stop("file reference must be a relative path inside its owned folder")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise Stop("file reference escapes its owned folder")
    base = Path(root).resolve()
    target = (base / rel).resolve()
    if not target.is_relative_to(base) or target == base:
        raise Stop("resolved file reference escapes its owned folder")
    # Reject links/junctions, including links resolving within the folder: avoid races
    # between validation and opening a subsequently redirected file.
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise Stop("file reference uses a symbolic link or junction")
    return target


def read_log(path):
    """Return the parsed records of a JSON-lines log. Raises Stop on a damaged line."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        text = p.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Stop("cannot read %s (%s)" % (path, e))
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            raise Stop("%s line %d is not JSON. The log is damaged; nothing was changed" % (path, n))
        if not isinstance(r, dict):
            raise Stop("%s line %d is not a record. The log is damaged; nothing was changed" % (path, n))
        for key in ("stored", "derived_file"):
            if r.get(key):
                contained_file(p.parent, r[key])
        for key in ("sha256", "derived_sha256"):
            if r.get(key) and (not isinstance(r[key], str) or not re.fullmatch(r"[0-9a-f]{64}", r[key])):
                raise Stop("%s line %d has an invalid %s" % (path, n, key))
        out.append(r)
    return out


def append_log(path, record):
    line = json.dumps(record, ensure_ascii=True, sort_keys=True, allow_nan=False)
    with open(path, "a", encoding="ascii", newline="\n") as f:
        f.write(line + "\n")


def store_bytes(store, digest, data):
    """Write data under its hash without ever replacing a file. Returns (relative name, note or None)."""
    name = "store/%s.raw" % digest
    target = store / ("%s.raw" % digest)
    try:
        with open(target, "xb") as f:
            f.write(data)
        return name, None
    except FileExistsError:
        try:
            same = sha256_hex(target.read_bytes()) == digest
        except OSError:
            same = False
        if same:
            return name, None
        return name, "a file named %s already exists with different content. It was not overwritten; run verify" % name


def previous_good(records):
    """Latest collected record per (source id, address)."""
    best = {}
    for r in records:
        if r.get("record") == "source" and r.get("outcome") in GOOD and r.get("sha256"):
            best[(r.get("source_id"), r.get("requested"))] = r
    return best


# ---------------------------------------------------------------- commands

def load_job(path, allow_local, for_run):
    job, raw = read_json_file(path, "job file")
    errors, advisories = validate_job(job, allow_local, for_run)
    return job, raw, errors, advisories


def make_transport(opts, clock_box, allow_local):
    if "--fixture-map" in opts and "--offline-fixtures" not in opts:
        raise Stop("--fixture-map needs --offline-fixtures")
    if "--offline-fixtures" in opts:
        clock_box.append(VirtualClock())
        return FixtureTransport(opts["--offline-fixtures"], opts.get("--fixture-map"), clock_box[0])
    clock_box.append(RealClock())
    return NetworkTransport(allow_local)


def refusal_report(cmd, job, errors, advisories, as_json):
    jid = job.get("job_id") if isinstance(job, dict) else None
    if as_json:
        emit(json.dumps({"command": cmd, "job_id": jid if isinstance(jid, str) else None, "errors": errors,
                         "advisories": advisories, "result": "REFUSED"}, indent=1, ensure_ascii=True))
    else:
        L = ["harvest %s: job %s" % (cmd, jid if isinstance(jid, str) else "?")]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        L.append("RESULT: REFUSED. %d error(s). Nothing was requested and nothing was written." % len(errors))
        emit("\n".join(L))
    return 1


def cmd_check(args, flags, opts):
    job, _raw, errors, advisories = load_job(args[0], "--allow-local" in flags, False)
    if errors:
        return refusal_report("check", job, errors, advisories, "--json" in flags)
    if "--json" in flags:
        emit(json.dumps({"command": "check", "job_id": job["job_id"], "sources": len(job["sources"]), "errors": [],
                         "advisories": advisories, "result": "PASS"}, indent=1, ensure_ascii=True))
    else:
        L = ["harvest check: job %s, %d source(s)" % (job["job_id"], len(job["sources"]))]
        L += ["  ADVISORY  " + m for m in advisories]
        L.append("RESULT: PASS. The job file is well formed. This does not show that the sites' terms allow "
                 "collection or that no page is about a private person.")
        emit("\n".join(L))
    return 0


def cmd_plan(args, flags, opts):
    allow_local = "--allow-local" in flags
    job, _raw, errors, advisories = load_job(args[0], allow_local, False)
    if errors:
        return refusal_report("plan", job, errors, advisories, "--json" in flags)
    box = []
    transport = make_transport(opts, box, allow_local)
    col = Collector(job, transport, box[0], allow_local)
    rows, per_host = [], {}
    for s in job["sources"]:
        host = host_of(s["address"])
        try:
            d = col.robots_decision(s["address"])
        except CapReached as e:
            rows.append({"id": s["id"], "kind": s["kind"], "address": s["address"], "action": "SKIP", "reason": str(e)})
            continue
        per_host.setdefault(host, 0)
        if d["decision"] == "allowed":
            per_host[host] += 1
            rows.append({"id": s["id"], "kind": s["kind"], "address": s["address"], "action": "FETCH", "reason": "robots: " + d["reason"]})
        else:
            rows.append({"id": s["id"], "kind": s["kind"], "address": s["address"], "action": "SKIP", "reason": "robots: " + d["reason"]})
    n_fetch = sum(1 for r in rows if r["action"] == "FETCH")
    n_robots = col.requests_made
    planned = n_fetch + n_robots
    for h in list(per_host):
        per_host[h] += col.host_requests.get(h, 0)
    duration = sum(max(0, n - 1) * col.delay_for(h) for h, n in per_host.items())
    if planned > job["max_requests"]:
        advisories.append("the run needs at least %d requests but max_requests is %d; the cap will end it early"
                          % (planned, job["max_requests"]))
    delays = sorted(set("%s %g s" % (h, col.delay_for(h)) for h in per_host))
    if "--json" in flags:
        emit(json.dumps({"command": "plan", "job_id": job["job_id"], "offline": transport.offline, "sources": rows,
                         "to_fetch": n_fetch, "to_skip": len(rows) - n_fetch, "robots_requests": n_robots,
                         "requests_planned": planned, "max_requests": job["max_requests"],
                         "least_duration_seconds": round(duration, 1), "delay_by_host": delays,
                         "errors": [], "advisories": advisories}, indent=1, ensure_ascii=True))
    else:
        L = ["harvest plan: job %s, %d source(s), %d host(s)%s" % (job["job_id"], len(rows), len(per_host),
             ", offline fixtures (no network)" if transport.offline else "")]
        L.append("  user agent  " + job["user_agent"])
        for r in rows:
            L.append("  %-5s %-6s %-5s %s" % (r["action"], r["id"], r["kind"], r["address"]))
            L.append("        " + r["reason"])
        L += ["  ADVISORY  " + m for m in advisories]
        L.append("  to fetch %d, to skip %d. Requests: %d content + %d robots.txt = %d of the cap of %d."
                 % (n_fetch, len(rows) - n_fetch, n_fetch, n_robots, planned, job["max_requests"]))
        L.append("  Least time for the run: %g s (%s between requests to one host, one request at a time). "
                 "Transfer time, redirects and waits a server asks for come on top." % (round(duration, 1), "; ".join(delays) or "no hosts"))
        L.append("RESULT: PLAN ONLY. robots.txt was read for %d host(s); no content was fetched." % len(per_host))
        emit("\n".join(L))
    return 0


def cmd_run(args, flags, opts):
    allow_local = "--allow-local" in flags
    if "--out" not in opts:
        raise Stop("run needs --out DIR")
    max_age = DEFAULT_MAX_AGE_DAYS
    if "--max-age-days" in opts:
        try:
            max_age = float(opts["--max-age-days"])
        except ValueError:
            max_age = float("nan")
        if not math.isfinite(max_age) or max_age < 0:
            raise Stop("--max-age-days needs a number of days, 0 or more")
    max_wait = DEFAULT_MAX_WAIT
    if "--max-wait" in opts:
        try:
            max_wait = float(opts["--max-wait"])
        except ValueError:
            max_wait = float("nan")
        if not math.isfinite(max_wait) or not 0 <= max_wait <= 3600:
            raise Stop("--max-wait needs a number of seconds from 0 to 3600")
    job, raw, errors, advisories = load_job(args[0], allow_local, True)
    if errors:
        return refusal_report("run", job, errors, advisories, "--json" in flags)
    box = []
    transport = make_transport(opts, box, allow_local)
    clock = box[0]
    out = Path(opts["--out"])
    if out.exists() and not out.is_dir():
        raise Stop("--out %s exists and is not a folder" % out)
    log_path = out / "fetch_log.jsonl"
    earlier = read_log(log_path)
    try:
        (out / "store").mkdir(parents=True, exist_ok=True)
        (out / "jobs").mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise Stop("cannot create %s: %s" % (out, e.strerror or e))
    lock = out / "run.lock"
    try:
        fd = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        raise Stop("%s exists: another run is using this folder, or an earlier run was killed. "
                   "If no run is active, remove that file and run again" % lock)
    except OSError as e:
        raise Stop("cannot write in %s: %s" % (out, e.strerror or e))
    os.write(fd, ("pid %d started %s\n" % (os.getpid(), utc_iso(time.time()))).encode("ascii"))
    os.close(fd)
    run_no = 1 + sum(1 for r in earlier if r.get("record") == "run_start")
    if clock.simulated:
        seen = [parse_iso(r.get("time")) for r in earlier]
        seen = [t for t in seen if t is not None]
        if seen and max(seen) + 1.0 > clock.t:
            clock.t = max(seen) + 1.0
    starts = sum(1 for r in earlier if r.get("record") == "run_start")
    ends = sum(1 for r in earlier if r.get("record") == "run_end")
    if starts > ends:
        advisories.append("an earlier run in this folder has no end record; it was interrupted")
    job_sha = sha256_hex(raw)
    col = Collector(job, transport, clock, allow_local, max_wait)
    prev = previous_good(earlier)
    mode = "offline-fixtures" if transport.offline else "network"
    results, stop_reason, interrupted = [], None, False
    try:
        job_copy = out / "jobs" / ("%s.json" % job_sha)
        if not job_copy.exists():
            with open(job_copy, "xb") as f:
                f.write(raw)
        append_log(log_path, {"record": "run_start", "run": run_no, "job_id": job["job_id"], "job_sha256": job_sha,
                              "time": utc_iso(clock.now()), "mode": mode, "clock": "simulated" if clock.simulated else "real",
                              "user_agent": job["user_agent"], "delay_seconds": job["delay_seconds"],
                              "max_requests": job["max_requests"], "max_bytes": job["max_bytes"],
                              "timeout_seconds": job["timeout_seconds"], "max_age_days": max_age,
                              "refetch": "--refetch" in flags, "sources": len(job["sources"]),
                              "script": "harvest.py", "extractor": EXTRACTOR_VERSION})
        logged_robots = 0
        for s in job["sources"]:
            base = {"record": "source", "run": run_no, "job_id": job["job_id"], "source_id": s["id"],
                    "title": s["title"], "publisher": s["publisher"], "tier": s["tier"], "kind": s["kind"],
                    "published": s.get("published"), "offline": transport.offline}
            p = prev.get((s["id"], s["address"]))
            rec = None
            if stop_reason:
                rec = {"requested": s["address"], "outcome": "skipped_cap", "error": stop_reason + "; not requested"}
            elif p and "--refetch" not in flags:
                age = max(0.0, clock.now() - (parse_iso(p.get("time")) or 0)) / 86400.0
                if age < max_age:
                    rec = {"requested": s["address"], "outcome": "skipped_fresh", "sha256": p["sha256"],
                           "bytes": p.get("bytes"), "stored": p.get("stored"), "final": p.get("final"),
                           "error": None, "note": "stored copy from %s is younger than %g day(s)" % (p.get("time"), max_age)}
            if rec is None:
                try:
                    rec = col.fetch(s, p)
                except CapReached as e:
                    stop_reason = str(e)
                    rec = {"requested": s["address"], "outcome": "skipped_cap", "error": stop_reason + "; not requested"}
                if rec.pop("cap_hit", False):
                    stop_reason = col.cap_reason
            body = rec.pop("body", None)
            if body is not None:
                name, problem = store_bytes(out / "store", rec["sha256"], body)
                if problem:
                    rec.update(outcome="error", error=problem)
                else:
                    rec["stored"] = name
                    if p and p["sha256"] == rec["sha256"]:
                        rec["outcome"] = "unchanged"
                    elif p:
                        rec["outcome"] = "changed"
                        rec["previous_sha256"] = p["sha256"]
                        rec["previous_stored"] = p.get("stored")
                    else:
                        rec["outcome"] = "stored"
            elif rec.get("outcome") == "unchanged" and p:
                rec["stored"] = p.get("stored")
            for state in col.robots_records[logged_robots:]:
                rr = {"record": "robots", "run": run_no, "job_id": job["job_id"], "address": state["address"],
                      "status": state["status"], "sha256": state["sha256"], "requests": state["requests"],
                      "readable": state["readable"], "note": state["why"], "offline": transport.offline,
                      "time": utc_iso(clock.now()), "crawl_delay": state.get("crawl_delay")}
                if state.get("body") is not None:
                    name, problem = store_bytes(out / "store", state["sha256"], state["body"])
                    rr["stored"] = name
                    if problem:
                        rr["note"] = problem
                append_log(log_path, rr)
            logged_robots = len(col.robots_records)
            base.update(rec)
            base["time"] = utc_iso(clock.now())
            append_log(log_path, base)
            results.append(base)
    except KeyboardInterrupt:
        interrupted = True
        stop_reason = "interrupted by the user"
    finally:
        counts = {}
        for r in results:
            counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
        try:
            append_log(log_path, {"record": "run_end", "run": run_no, "job_id": job["job_id"], "time": utc_iso(clock.now()),
                                  "requests_made": col.requests_made, "bytes_read": col.bytes_read,
                                  "waited_seconds": round(col.waited, 3), "stop_reason": stop_reason,
                                  "outcomes": counts, "sources_done": len(results), "sources": len(job["sources"])})
        finally:
            try:
                os.remove(str(lock))
            except OSError:
                pass
    collected = sum(1 for r in results if r["outcome"] in GOOD + ("skipped_fresh",))
    missing = len(job["sources"]) - collected
    if "--json" in flags:
        emit(json.dumps({"command": "run", "run": run_no, "job_id": job["job_id"], "mode": mode, "sources": results,
                         "outcomes": counts, "requests_made": col.requests_made, "max_requests": job["max_requests"],
                         "bytes_read": col.bytes_read, "max_bytes": job["max_bytes"], "waited_seconds": round(col.waited, 3),
                         "stop_reason": stop_reason, "collected_or_fresh": collected, "not_collected": missing,
                         "errors": [], "advisories": advisories}, indent=1, ensure_ascii=True))
    else:
        L = ["harvest run %d: job %s, %d source(s), %s" % (run_no, job["job_id"], len(job["sources"]),
             "offline fixtures: nothing was fetched from the network and waits were simulated" if transport.offline else "network")]
        L += ["  ADVISORY  " + m for m in advisories]
        words = {"stored": "STORED", "changed": "CHANGED", "unchanged": "UNCHANGED", "skipped_fresh": "FRESH",
                 "skipped_robots": "SKIPPED", "skipped_cap": "SKIPPED", "skipped_host_stopped": "SKIPPED",
                 "barrier": "BARRIER", "rate_limited": "LIMITED", "refused": "REFUSED", "error": "ERROR"}
        for r in results:
            line = "  %-9s %-6s %s" % (words.get(r["outcome"], r["outcome"].upper()), r["source_id"], r["requested"])
            L.append(line)
            if r["outcome"] in GOOD:
                detail = "HTTP %s, %s bytes, sha256 %s" % (r.get("status"), group_digits(r["bytes"]) if is_whole(r.get("bytes")) else "?", r["sha256"][:16])
                if r["outcome"] == "changed":
                    detail += ", was %s" % r["previous_sha256"][:16]
                if r.get("final") and r["final"] != r["requested"]:
                    detail += ", final address %s" % r["final"]
                if r.get("retry_after_seconds") is not None:
                    detail += ", waited %g s as asked then retried once" % r["retry_after_seconds"]
                L.append("            " + detail)
            elif r["outcome"] == "skipped_fresh":
                L.append("            " + r.get("note", ""))
            else:
                L.append("            " + (r.get("error") or ""))
        L.append("  requests %d of the cap of %d; bytes %s of the cap of %s; waited %g s in all%s"
                 % (col.requests_made, job["max_requests"], group_digits(col.bytes_read), group_digits(job["max_bytes"]),
                    round(col.waited, 1), " (simulated)" if clock.simulated else ""))
        if stop_reason:
            L.append("  STOPPED EARLY: " + stop_reason)
        names = {"skipped_fresh": "still fresh", "skipped_robots": "skipped by robots", "skipped_cap": "skipped at a cap",
                 "skipped_host_stopped": "skipped, host stopped", "barrier": "behind a barrier", "rate_limited": "rate limited"}
        have = ", ".join("%d %s" % (n, names.get(k, k)) for k, n in sorted(counts.items()) if k in GOOD + ("skipped_fresh",))
        lack = ", ".join("%d %s" % (n, names.get(k, k)) for k, n in sorted(counts.items()) if k not in GOOD + ("skipped_fresh",))
        if len(results) < len(job["sources"]):
            lack = (lack + ", " if lack else "") + "%d not reached" % (len(job["sources"]) - len(results))
        L.append("RESULT: %d of %d source(s) collected or still fresh%s; %d not collected%s. Fetched is not read."
                 % (collected, len(job["sources"]), (" (%s)" % have) if have else "", missing, (" (%s)" % lack) if lack else ""))
        emit("\n".join(L))
    if interrupted:
        return 1
    return 0 if missing == 0 else 1


def open_folder(path):
    d = Path(path)
    if not d.is_dir():
        raise Stop("%s is not a folder" % path)
    if not (d / "fetch_log.jsonl").is_file():
        raise Stop("%s has no fetch_log.jsonl; is it a harvest output folder?" % path)
    return d, read_log(d / "fetch_log.jsonl")


def cmd_verify(args, flags, opts):
    d, records = open_folder(args[0])
    errors, advisories, expected = [], [], {}
    for r in records:
        if r.get("record") in ("source", "robots") and r.get("stored") and r.get("sha256"):
            if r.get("record") == "robots" or r.get("outcome") in GOOD:
                expected.setdefault(r["stored"], set()).add(r["sha256"])
    derived = read_log(d / "derived_log.jsonl")
    for r in derived:
        if r.get("derived_file") and r.get("derived_sha256"):
            expected.setdefault(r["derived_file"], set()).add(r["derived_sha256"])
    ok = 0
    for name in sorted(expected):
        want = expected[name]
        f = contained_file(d, name)
        if len(want) > 1:
            errors.append("%s is logged with %d different hashes" % (name, len(want)))
            continue
        if not f.is_file():
            errors.append("%s is in the log but missing from the folder" % name)
            continue
        got = sha256_hex(f.read_bytes())
        if got not in want:
            errors.append("%s does not match the log: logged sha256 %s, file is %s" % (name, sorted(want)[0], got))
        else:
            ok += 1
    store = d / "store"
    if store.is_dir():
        for f in sorted(store.iterdir()):
            if f.is_file() and ("store/" + f.name) not in expected:
                advisories.append("store/%s is not in any log" % f.name)
    if "--json" in flags:
        emit(json.dumps({"command": "verify", "files_logged": len(expected), "files_matching": ok, "errors": errors,
                         "advisories": advisories}, indent=1, ensure_ascii=True))
    else:
        L = ["harvest verify: %d file(s) named in the logs, %d re-hashed and matching" % (len(expected), ok)]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        L.append("RESULT: %s. %d error(s), %d advisory note(s). A match means the file is the one that was logged; "
                 "it does not show the log itself is untouched." % ("FAIL" if errors else "PASS", len(errors), len(advisories)))
        emit("\n".join(L))
    return 1 if errors else 0


# ---------------------------------------------------------------- extraction

class TextExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.out, self.title_parts, self.skip, self.in_title = [], [], [], False
        self.link_just_closed = False

    def handle_starttag(self, tag, attrs):
        if tag == "a" and self.link_just_closed and not self.skip:
            self.out.append(" ")
        self.link_just_closed = False
        if tag in SKIP_TAGS and tag not in VOID_TAGS:
            self.skip.append(tag)
        elif tag == "title" and not self.skip:
            self.in_title = True
        elif tag in BLOCK_TAGS:
            self.out.append("\n")
        elif tag in ("td", "th"):
            self.out.append(" ")

    def handle_startendtag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        self.link_just_closed = tag == "a"
        if tag == "title":
            self.in_title = False
        elif tag in BLOCK_TAGS:
            self.out.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        self.link_just_closed = False
        if self.in_title:
            self.title_parts.append(data)
        else:
            self.out.append(data)


def decode_page(body, content_type):
    """Return (text, how it was decoded, number of characters that could not be decoded)."""
    for bom, name in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if body.startswith(bom):
            text = body.decode(name, "replace")
            return text, "%s (byte-order mark)" % name, text.count(chr(0xFFFD))
    declared, where = None, None
    m = re.search(r"charset\s*=\s*[\"']?([A-Za-z0-9_.:-]+)", content_type or "", re.I)
    if m:
        declared, where = m.group(1), "Content-Type header"
    else:
        m = re.search(br"charset\s*=\s*[\"']?([A-Za-z0-9_.:-]+)", body[:4096], re.I)
        if m:
            declared, where = m.group(1).decode("ascii"), "meta tag"
    if declared:
        try:
            text = body.decode(declared, "replace")
            return text, "%s (%s)" % (declared.lower(), where), text.count(chr(0xFFFD))
        except LookupError:
            pass
    try:
        return body.decode("utf-8"), "utf-8 (not declared; valid)", 0
    except UnicodeDecodeError:
        text = body.decode("cp1252", "replace")
        return text, "windows-1252 (assumed: no usable charset declared and not valid UTF-8)", text.count(chr(0xFFFD))


def html_to_text(body, content_type):
    text, how, bad = decode_page(body, content_type)
    p = TextExtractor()
    try:
        p.feed(text)
        p.close()
    except Exception as e:  # noqa: BLE001  the parser is lenient but not infallible
        return None, None, how, bad, "could not be parsed as HTML (%s)" % str(e)[:60]
    lines = []
    for line in "".join(p.out).replace("\r", "\n").split("\n"):
        line = " ".join(line.split())
        if line or (lines and lines[-1]):
            lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    title = " ".join(" ".join(p.title_parts).split())
    return "\n".join(lines), title, how, bad, None


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def child_text(node, names):
    for c in node:
        if local_name(c.tag) in names:
            t = " ".join("".join(c.itertext()).split())
            if t:
                return t
    return ""


def date_to_iso(text):
    if not text:
        return None
    try:
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        when = None
    if when is None:
        try:
            when = dt.datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if when.tzinfo is None:
        return when.strftime("%Y-%m-%dT%H:%M:%S") + " (no time zone given)"
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def feed_entries(body):
    """Return (feed title, entries, problem). Entries are dicts of title, link, date_as_written, date_iso."""
    if re.search(br"<!ENTITY", body, re.I):
        return None, None, "the feed declares XML entities; not parsed"
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        return None, None, "not well-formed XML (%s)" % str(e)[:60]
    kind = local_name(root.tag)
    if kind not in ("rss", "feed", "rdf"):
        return None, None, "the root element is <%s>, not an RSS or Atom feed" % kind
    holder = root
    if kind == "rss":
        for c in root:
            if local_name(c.tag) == "channel":
                holder = c
    title = child_text(holder, ("title",))
    entries = []
    for node in root.iter():
        if local_name(node.tag) not in ("item", "entry"):
            continue
        link = ""
        for c in node:
            if local_name(c.tag) == "link":
                href = c.attrib.get("href")
                if href and c.attrib.get("rel", "alternate") == "alternate":
                    link = href.strip()
                    break
                if not href and (c.text or "").strip():
                    link = c.text.strip()
                    break
        written = child_text(node, ("pubdate", "updated", "published", "date"))
        entries.append({"title": child_text(node, ("title",)), "link": link, "date_as_written": written or None,
                        "date_iso": date_to_iso(written)})
    return title, entries, None


def inflate(body, limit=50000000):
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        out = d.decompress(body, limit)
    except zlib.error:
        return None
    return None if d.unconsumed_tail else out


def cmd_extract(args, flags, opts):
    d, records = open_folder(args[0])
    latest = {}
    for r in records:
        if r.get("record") == "source" and r.get("outcome") in ("stored", "changed") and r.get("stored"):
            latest.setdefault(r["sha256"], r)
    done, errors, advisories = [], [], []
    sharers = {}
    for r in records:
        if r.get("record") == "source" and r.get("outcome") in ("stored", "changed") and r.get("sha256"):
            group = sharers.setdefault(r["sha256"], [])
            if (r.get("source_id"), r.get("requested")) not in [(x["source_id"], x["requested"]) for x in group]:
                group.append({"source_id": r.get("source_id"), "requested": r.get("requested"), "fetched": r.get("time")})
    first_seen = {}
    for n, r in enumerate(records):
        if r.get("record") == "source":
            first_seen.setdefault(r.get("source_id"), n)
    for digest in sorted(latest, key=lambda h: (first_seen.get(latest[h].get("source_id"), 0), latest[h].get("time") or "")):
        r = latest[digest]
        item = {"source_id": r.get("source_id"), "raw": r["stored"], "raw_sha256": digest, "kind": r.get("kind"),
                "address": r.get("final") or r.get("requested"), "requested": r.get("requested"), "fetched": r.get("time"),
                "also_stored_for": sharers.get(digest, [])[1:]}
        if item["also_stored_for"]:
            advisories.append("%s returned the same bytes (sha256 %s). One stored file and one derivative stand for all of them. "
                              "Look at it: identical content from different addresses is often a placeholder, a consent page "
                              "or a sign-in page" % (" and ".join(x["source_id"] or "?" for x in sharers[digest]), digest[:16]))
        raw_path = contained_file(d, r["stored"])
        if not raw_path.is_file():
            item["result"] = "raw file is missing"
            errors.append("%s: %s is missing; run verify" % (r.get("source_id"), r["stored"]))
            done.append(item)
            continue
        body = raw_path.read_bytes()
        if sha256_hex(body) != digest:
            item["result"] = "raw file does not match its hash"
            errors.append("%s: %s does not match its logged hash; run verify" % (r.get("source_id"), r["stored"]))
            done.append(item)
            continue
        if (r.get("content_encoding") or "").lower() in ("gzip", "x-gzip"):
            body = inflate(body)
            if body is None:
                item["result"] = "not extracted: the stored bytes are gzip and could not be unpacked"
                done.append(item)
                continue
        ctype = r.get("content_type") or ""
        head = ["DERIVED TEXT. This is not the source. It was made from the raw file named below by",
                "harvest.py extract (extractor %d), which strips markup and nothing more." % EXTRACTOR_VERSION,
                "raw_file: %s" % r["stored"], "raw_sha256: %s" % digest, "source_id: %s" % r.get("source_id"),
                "address: %s" % (r.get("final") or r.get("requested"))]
        if r.get("final") and r.get("final") != r.get("requested"):
            head.append("requested: %s" % r.get("requested"))
        head.append("fetched: %s (UTC; when this copy was first stored)" % r.get("time"))
        if r.get("offline"):
            head.append("note: OFFLINE FIXTURE, not fetched from the network")
        if r.get("kind") == "file":
            item["result"] = "not extracted: kind is file"
            done.append(item)
            continue
        if r.get("kind") == "feed":
            title, entries, problem = feed_entries(body)
            if problem:
                item["result"] = "not extracted: " + problem
                done.append(item)
                continue
            head += ["feed_title: %s" % title, "entries: %d" % len(entries)] + DATA_NOTICE + ["----"]
            lines = []
            for i, e in enumerate(entries, start=1):
                lines.append("[%d] %s" % (i, e["title"] or "(no title)"))
                lines.append("    link: %s" % (e["link"] or "(none)"))
                lines.append("    date: %s (as written: %s)" % (e["date_iso"] or "not parsed", e["date_as_written"] or "none"))
            item.update(entries=entries, feed_title=title)
            derived_text = "\n".join(head + lines) + "\n"
        else:
            sniff = body[:2048].lstrip().lower()
            if "html" not in ctype.lower() and not (sniff.startswith(b"<!doctype html") or b"<html" in sniff):
                item["result"] = "not extracted: the content is not HTML (%s)" % (ctype or "no content type")
                done.append(item)
                continue
            text, title, how, bad, problem = html_to_text(body, ctype)
            if problem:
                item["result"] = "not extracted: " + problem
                done.append(item)
                continue
            head += ["title: %s" % title, "decoded_as: %s" % how]
            if bad:
                head.append("undecodable_characters: %d (shown as the replacement mark)" % bad)
            head += DATA_NOTICE + ["----"]
            item.update(title=title, decoded_as=how, undecodable_characters=bad, characters=len(text))
            derived_text = "\n".join(head) + "\n" + text + "\n"
        data = derived_text.encode("utf-8")
        name = "store/%s.extracted.txt" % digest
        target = d / name
        item.update(derived_file=name, derived_sha256=sha256_hex(data))
        try:
            with open(target, "xb") as f:
                f.write(data)
            item["result"] = "written"
            append_log(d / "derived_log.jsonl", {"record": "derived", "raw_file": r["stored"], "raw_sha256": digest,
                                                 "derived_file": name, "derived_sha256": item["derived_sha256"],
                                                 "extractor": EXTRACTOR_VERSION, "source_id": r.get("source_id"),
                                                 "address": item["address"], "fetched": item["fetched"],
                                                 "time": utc_iso(time.time())})
        except FileExistsError:
            if sha256_hex(target.read_bytes()) == item["derived_sha256"]:
                item["result"] = "already present and identical"
            else:
                item["result"] = "a different derivative already exists; not overwritten"
                errors.append("%s exists with different content. It was not overwritten; move it aside to extract again" % name)
        done.append(item)
    written = sum(1 for i in done if i["result"] in ("written", "already present and identical"))
    if "--json" in flags:
        emit(json.dumps({"command": "extract", "stored_versions": len(done), "derivatives": written, "items": done,
                         "errors": errors, "advisories": advisories}, indent=1, ensure_ascii=True))
    else:
        L = ["harvest extract: %d stored version(s)" % len(done)]
        for i in done:
            L.append("  %-6s %s: %s" % (i["source_id"], i["raw"], i["result"]))
            if i.get("derived_file") and i["result"] != "a different derivative already exists; not overwritten":
                L.append("         %s sha256 %s" % (i["derived_file"], i["derived_sha256"][:16]))
                if "entries" in i:
                    L.append("         feed %r, %d entries" % (i.get("feed_title", ""), len(i["entries"])))
                else:
                    L.append("         title %r, %s characters, decoded as %s" % (i.get("title", ""), group_digits(i.get("characters", 0)), i.get("decoded_as")))
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        L.append("RESULT: %s. %d derivative(s) for %d stored version(s). A derivative is markup removed, not the "
                 "article found, and reading it is still to be done." % ("FAIL" if errors else "PASS", written, len(done)))
        emit("\n".join(L))
    return 1 if errors else 0


def cmd_ledger(args, flags, opts):
    d, records = open_folder(args[0])
    if "--out" not in opts:
        raise Stop("ledger needs --out SOURCES.csv")
    target = Path(opts["--out"])
    if target.exists():
        raise Stop("%s already exists and is not overwritten. Choose another name" % target)
    order, latest, never = [], {}, {}
    for r in records:
        if r.get("record") != "source":
            continue
        sid = r.get("source_id")
        if sid not in order:
            order.append(sid)
        if r.get("outcome") in GOOD and r.get("sha256"):
            latest[sid] = r
        elif r.get("outcome") != "skipped_fresh":
            never[sid] = r
    rows, omitted = [], []
    for sid in order:
        r = latest.get(sid)
        if r is None:
            omitted.append({"source_id": sid, "reason": (never.get(sid) or {}).get("error") or "never collected"})
            continue
        stamp = parse_iso(r.get("time")) or 0
        accessed = dt.datetime.fromtimestamp(stamp).date().isoformat()
        notes = ["harvest job %s" % r.get("job_id"), "sha256=%s" % r["sha256"]]
        if is_whole(r.get("bytes")):
            notes.append("bytes=%d" % r["bytes"])
        notes.append("fetched %s" % r.get("time"))
        if r.get("final") and r.get("final") != r.get("requested"):
            notes.append("final address %s" % r["final"])
        if r.get("offline"):
            notes.append("OFFLINE FIXTURE, not fetched from the network")
        notes.append("fetched, not read: read it before raising read_level")
        rows.append({"source_id": sid, "title": r.get("title") or "", "publisher": r.get("publisher") or "",
                     "address": r.get("requested") or "", "tier": r.get("tier") or "", "published": r.get("published") or "",
                     "accessed": accessed, "read_level": "snippet", "family": "", "notes": "; ".join(notes)})
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(SRC_COLS), lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow(row)
    try:
        with open(target, "x", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue())
    except OSError as e:
        raise Stop("cannot write %s: %s" % (target, e.strerror or e))
    if "--json" in flags:
        emit(json.dumps({"command": "ledger", "written": str(target), "rows": len(rows), "omitted": omitted,
                         "errors": [], "advisories": []}, indent=1, ensure_ascii=True))
    else:
        L = ["harvest ledger: %d row(s) written to %s" % (len(rows), target)]
        for o in omitted:
            L.append("  OMITTED   %s was never collected (%s)" % (o["source_id"], o["reason"]))
        L.append("RESULT: PASS. Every row has read_level snippet: fetched is not read. Open and read a source, "
                 "then raise its read_level by hand.")
        emit("\n".join(L))
    return 0


COMMANDS = {"check": cmd_check, "plan": cmd_plan, "run": cmd_run, "verify": cmd_verify, "extract": cmd_extract,
            "ledger": cmd_ledger}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        emit(__doc__)
        return 2 if not argv else 0
    cmd = argv[0]
    if cmd not in SUBCOMMANDS:
        print("harvest: unknown command %s (use check, plan, run, verify, extract or ledger)" % ascii_text(cmd), file=sys.stderr)
        return 2
    allowed_flags, allowed_values = SUBCOMMANDS[cmd]
    flags, opts, args, it = set(), {}, [], iter(argv[1:])
    for a in it:
        if a in allowed_flags:
            flags.add(a)
        elif a in allowed_values:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("harvest: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("-"):
            print("harvest: unknown option %s for %s" % (ascii_text(a), cmd), file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print("harvest: %s takes exactly one %s" % (cmd, "job file" if cmd in ("check", "plan", "run") else "output folder"), file=sys.stderr)
        return 2
    try:
        return COMMANDS[cmd](args, flags, opts)
    except Stop as e:
        print("harvest: " + ascii_text(str(e)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
