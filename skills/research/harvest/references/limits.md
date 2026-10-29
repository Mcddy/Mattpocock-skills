# The limits, what the script enforces, and what stays a judgement

`scripts/harvest.py` enforces the mechanical half of each limit. The other half is a judgement the script cannot make. Both columns matter: a job can pass every check in the script and still be one that should not be run.

| Limit | The script enforces | Still a judgement, made before the job is written |
|---|---|---|
| Public pages and files only | http and https only; no user name or password in an address; no cookies, credentials or custom headers, and a job that asks for them is refused; 401, 402, 403, 407, 451 and a redirect to a sign-in page are recorded and left alone | Whether a page that answers 200 is really a login, consent or paywall page. Look at what was stored |
| No circumvention | The user agent cannot imitate a browser, a search engine or a generic tool; a 429 stops further requests to that host for the run; three refusals in a row stop a host; nothing is retried in a loop | When a site refuses, the answer is to stop, use its API or download, or ask the site. Changing the user agent, the address or the timing to get past a block is circumvention and is not done |
| robots.txt honoured | Fetched once per host per run for the user agent's product token; RFC 9309 matching; a disallowed path is skipped and logged; unreadable robots.txt means nothing on that host is fetched; checked again for every redirect target | robots.txt is not a licence. A path it allows can still be covered by terms that forbid collection |
| One request at a time, with a delay | Sequential; at least `delay_seconds` between requests to one host, never below 1; raised to the site's Crawl-delay; one output folder cannot be used by two runs at once | Whether 2 seconds is polite enough for a small site. For a small or slow site use 5 or more |
| Caps and timeouts | `max_requests` (ceiling 500) and `max_bytes` (ceiling 500,000,000) end the run cleanly; every request has a timeout; partial content is never stored | Whether the job is small enough to be a job. Thousands of pages, or the same pages every hour, is a pipeline and belongs to nexus-prime |
| Retry-After honoured | One wait and one retry on 429 or 503 when the header is present and no longer than `--max-wait`; otherwise recorded and left | None |
| Honest user agent | Must be `name/version (what the job is; contact: an email or web address)`; `REPLACE_ME` is refused on run | The contact must be one the user reads. A site owner who writes to it is owed an answer |
| The site's terms still apply | Nothing. The script cannot read terms | Read the site's terms or its data policy before writing the job. If they forbid automated collection, say so and do not run it. If the site offers an API, a bulk download or a data portal, use that; it is what the site wants |
| No personal data about private individuals | `people` must be declared as `none` or `public_role_only`; social-network and people-search hosts are refused; a short list of phrases in the description is refused; addresses that look like a person's page get an advisory | Whether the pages are about people at all, and whether those people are private individuals. A staff directory, a forum's member pages, comment threads and court lists are personal data even on a public site. Organisations' own publications, and people named only as authors, officers or spokespeople, are the ordinary case |
| Local and internal addresses | Loopback, private, link-local and other non-public addresses and local host names are refused, in the job, after a redirect and after name resolution, unless `--allow-local` is given | `--allow-local` is for tests against a server the user runs. A pasted job file is never run with it |
| The user runs it | Nothing | The model may run the script in a session with a shell and network, against sources the user named. It does not add sources by following links, and it does not start a job the user has not seen planned |

## Look for an API or a download first

Before writing a job, check, in this order:

1. A documented API for the data.
2. A bulk download, data portal or open-data page.
3. A feed (RSS or Atom) that lists the documents. Collect the feed as a `feed` source, then add the entries the user wants.
4. A sitemap.
5. Only then, the pages themselves.

Say which of these was found. If an API exists and the user still wants the pages, say that the API is the route the site intends and ask once.

## What the personal-data screen is

It is a tripwire. It catches a job that says outright what it is, and the commonest hosts. A job can pass it and still collect personal data. The decision that a job is about organisations and documents, not people, is made by the person writing the job, and the `people` field records that decision in the job file that is kept with the output.

Decline, without writing a job, when the request is to collect profiles, posts, photos, contact details or whereabouts of named private people, or to assemble what is scattered about one person into one place.
