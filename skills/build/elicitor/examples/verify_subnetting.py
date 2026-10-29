#!/usr/bin/env python3
"""Verify the answer key of the subnetting quiz against Python's ipaddress module. Standard library only.

Usage:
  python verify_subnetting.py QUIZ [--json]

QUIZ is the built quiz (subnetting-quiz.html) or its instrument file (instruments/subnetting-quiz.json).

What it enforces (ERROR, exit 1):
  - the quiz has exactly the twelve items this script knows, and no others
  - for every item, the set of options marked correct equals the answer computed here with
    ipaddress; a marked option that is wrong and a right option left unmarked both fail
  - every figure this script lists under CLAIMS is true, and the explanation it was taken from
    (named in WHERE by item, option and a phrase) still contains that phrase. If an explanation is
    reworded, the figure in it has to be checked again and the two lists updated
What it cannot tell: whether the wording of an item or an explanation is clear, and whether an
explanation makes a claim that is not listed under CLAIMS (12 of the 48 explanations have no
listed figure). Those were read by the author, not computed.

Exit codes: 0 every key and claim verified. 1 a mismatch. 2 bad arguments or unreadable input.
"""
import ipaddress as ip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_instrument import InputError, load_instrument  # noqa: E402


def usable(prefix):
    """Usable host addresses in an IPv4 subnet of this prefix length (/30 and shorter)."""
    return ip.ip_network("0.0.0.0/%d" % prefix).num_addresses - 2


def net_of(host):
    return ip.ip_interface(host).network


def smallest_prefix_for(hosts):
    return max(p for p in range(1, 31) if usable(p) >= hosts)


def in_same_subnet(host, candidates):
    net = net_of(host)
    return {c for c in candidates if ip.ip_address(c) in net}


# item id -> a function of the item's option texts that returns the set of correct option texts
ANSWERS = {
    "mask-26": lambda opts: {str(ip.ip_network("0.0.0.0/26").netmask)},
    "hosts-27": lambda opts: {str(usable(27))},
    "network-of-host": lambda opts: {str(net_of("192.168.10.77/26").network_address)},
    "broadcast-of-host": lambda opts: {str(net_of("172.16.5.130/25").broadcast_address)},
    "first-usable": lambda opts: {str(next(ip.ip_network("10.20.30.96/28").hosts()))},
    "last-usable": lambda opts: {str(list(ip.ip_network("192.168.4.0/22").hosts())[-1])},
    "prefix-for-hosts": lambda opts: {"/%d" % smallest_prefix_for(50)},
    "same-subnet": lambda opts: in_same_subnet("192.168.1.100/27", opts),
    "subnets-from-24": lambda opts: {str(len(list(ip.ip_network("192.168.0.0/24").subnets(new_prefix=28))))},
    "wildcard": lambda opts: {str(ip.ip_network("0.0.0.0/255.255.240.0").hostmask)},
    "containing-subnet": lambda opts: {str(net_of("10.1.9.200/21"))},
    "summary-route": lambda opts: {str(n) for n in ip.collapse_addresses(ip.ip_network("192.168.%d.0/24" % k) for k in (8, 9, 10, 11))},
}


def is_boundary(text):
    try:
        ip.ip_network(text, strict=True)
        return True
    except ValueError:
        return False


# figures quoted in the explanations, each stated as (what the explanation says, whether it is true)
CLAIMS = [
    ("255.255.192.0 is /18", ip.ip_network("0.0.0.0/255.255.192.0").prefixlen == 18),
    ("255.255.255.128 is /25", ip.ip_network("0.0.0.0/255.255.255.128").prefixlen == 25),
    ("255.255.255.224 is /27", ip.ip_network("0.0.0.0/255.255.255.224").prefixlen == 27),
    ("a /27 has 32 addresses in total", ip.ip_network("0.0.0.0/27").num_addresses == 32),
    ("a /28 has 14 usable addresses", usable(28) == 14),
    ("a /26 has 62 usable addresses", usable(26) == 62),
    ("a /27 has 30 usable addresses", usable(27) == 30),
    ("a /25 has 126 usable addresses", usable(25) == 126),
    ("a /24 has 254 usable addresses", usable(24) == 254),
    ("a /24 is four times the size of a /26", ip.ip_network("0.0.0.0/24").num_addresses == 4 * ip.ip_network("0.0.0.0/26").num_addresses),
    ("192.168.10.77/24 would be in network 192.168.10.0", str(net_of("192.168.10.77/24").network_address) == "192.168.10.0"),
    ("/26 blocks in the last octet start at 0, 64, 128, 192", [int(n.network_address) & 255 for n in ip.ip_network("192.168.10.0/24").subnets(new_prefix=26)] == [0, 64, 128, 192]),
    ("192.168.10.76 is not a /26 boundary", not is_boundary("192.168.10.76/26")),
    ("192.168.10.128/26 holds 128 to 191", str(ip.ip_network("192.168.10.128/26").broadcast_address) == "192.168.10.191"),
    ("the lower /25 of 172.16.5.0 ends at 127", str(ip.ip_network("172.16.5.0/25").broadcast_address) == "172.16.5.127"),
    ("the upper /25 of 172.16.5.0 starts at 128", str(net_of("172.16.5.130/25").network_address) == "172.16.5.128"),
    ("172.16.0.0/16 has broadcast 172.16.255.255", str(ip.ip_network("172.16.0.0/16").broadcast_address) == "172.16.255.255"),
    ("10.20.30.96/28 runs from 96 to 111", str(ip.ip_network("10.20.30.96/28").broadcast_address) == "10.20.30.111"),
    ("the last usable address in 10.20.30.96/28 is 110", str(list(ip.ip_network("10.20.30.96/28").hosts())[-1]) == "10.20.30.110"),
    ("192.168.4.0/22 runs to 192.168.7.255", str(ip.ip_network("192.168.4.0/22").broadcast_address) == "192.168.7.255"),
    ("192.168.4.0/24 has last usable 192.168.4.254", str(list(ip.ip_network("192.168.4.0/24").hosts())[-1]) == "192.168.4.254"),
    ("192.168.4.0/23 has last usable 192.168.5.254", str(list(ip.ip_network("192.168.4.0/23").hosts())[-1]) == "192.168.5.254"),
    ("a /22 is twice the size of a /23", ip.ip_network("0.0.0.0/22").num_addresses == 2 * ip.ip_network("0.0.0.0/23").num_addresses),
    ("the /27 holding 192.168.1.100 runs from 96 to 127", (str(net_of("192.168.1.100/27").network_address), str(net_of("192.168.1.100/27").broadcast_address)) == ("192.168.1.96", "192.168.1.127")),
    ("192.168.1.95 is the broadcast of the block 64 to 95", str(ip.ip_network("192.168.1.64/27").broadcast_address) == "192.168.1.95"),
    ("192.168.1.126 is the last usable address of that block", str(list(net_of("192.168.1.100/27").hosts())[-1]) == "192.168.1.126"),
    ("192.168.1.128/27 holds 128 to 159", str(ip.ip_network("192.168.1.128/27").broadcast_address) == "192.168.1.159"),
    ("a /24 gives 8 subnets of /27", len(list(ip.ip_network("192.168.0.0/24").subnets(new_prefix=27))) == 8),
    ("each /28 has 16 addresses", ip.ip_network("0.0.0.0/28").num_addresses == 16),
    ("the block size in the third octet for 255.255.240.0 is 16", 256 - 240 == 16 and ip.ip_network("0.0.0.0/255.255.240.0").prefixlen == 20),
    ("10.1.0.0/21 covers up to 10.1.7.255", str(ip.ip_network("10.1.0.0/21").broadcast_address) == "10.1.7.255"),
    ("10.1.8.0/21 covers up to 10.1.15.255", str(ip.ip_network("10.1.8.0/21").broadcast_address) == "10.1.15.255"),
    ("10.1.9.0 is not a /21 boundary", not is_boundary("10.1.9.0/21")),
    ("10.1.9.0 is inside 10.1.8.0/21", ip.ip_address("10.1.9.0") in ip.ip_network("10.1.8.0/21")),
    ("10.1.16.0/21 starts above 10.1.9.200", ip.ip_network("10.1.16.0/21").network_address > ip.ip_address("10.1.9.200")),
    ("192.168.8.0/23 covers exactly 192.168.8.0/24 and 192.168.9.0/24", [str(n) for n in ip.ip_network("192.168.8.0/23").subnets(new_prefix=24)] == ["192.168.8.0/24", "192.168.9.0/24"]),
    ("192.168.8.0/22 runs from 192.168.8.0 to 192.168.11.255", str(ip.ip_network("192.168.8.0/22").broadcast_address) == "192.168.11.255"),
    ("192.168.8.0/21 covers eight /24 blocks up to 192.168.15.255", len(list(ip.ip_network("192.168.8.0/21").subnets(new_prefix=24))) == 8 and str(ip.ip_network("192.168.8.0/21").broadcast_address) == "192.168.15.255"),
    ("192.168.0.0/20 covers sixteen /24 blocks up to 192.168.15.255", len(list(ip.ip_network("192.168.0.0/20").subnets(new_prefix=24))) == 16 and str(ip.ip_network("192.168.0.0/20").broadcast_address) == "192.168.15.255"),
]


# where each figure in CLAIMS is quoted: item id, option text, and the phrase in that option's explanation
WHERE = [
    ("mask-26", "255.255.192.0", "That is /18"),
    ("mask-26", "255.255.255.128", "That is /25"),
    ("mask-26", "255.255.255.224", "That is /27"),
    ("hosts-27", "32", "32 is the total number of addresses in a /27"),
    ("hosts-27", "14", "14 is the usable count for a /28"),
    ("hosts-27", "62", "62 is the usable count for a /26"),
    ("prefix-for-hosts", "/27", "A /27 has 30 usable addresses"),
    ("prefix-for-hosts", "/25", "A /25 has 126 usable addresses"),
    ("prefix-for-hosts", "/24", "A /24 has 254 usable addresses"),
    ("prefix-for-hosts", "/24", "four times the size of the smallest block that does"),
    ("network-of-host", "192.168.10.0", "the network if the prefix were /24"),
    ("network-of-host", "192.168.10.64", "blocks of 64 in the last octet: 0, 64, 128, 192"),
    ("network-of-host", "192.168.10.76", "76 is not a block boundary for /26"),
    ("network-of-host", "192.168.10.128", "holds 128 to 191"),
    ("broadcast-of-host", "172.16.5.127", "the lower /25, which holds 0 to 127"),
    ("broadcast-of-host", "172.16.5.128", "128 is the network address of the upper /25"),
    ("broadcast-of-host", "172.16.255.255", "the broadcast address of 172.16.0.0/16"),
    ("first-usable", "10.20.30.111", "The block runs from 96 to 111"),
    ("first-usable", "10.20.30.110", "110 is the last usable address in this /28"),
    ("last-usable", "192.168.7.254", "A /22 covers 192.168.4.0 to 192.168.7.255"),
    ("last-usable", "192.168.4.254", "That would be right for 192.168.4.0/24"),
    ("last-usable", "192.168.5.254", "A /23 starting at 192.168.4.0 would end there"),
    ("last-usable", "192.168.5.254", "A /22 is twice that size"),
    ("same-subnet", "192.168.1.97", "The /27 that holds 100 runs from 96 to 127"),
    ("same-subnet", "192.168.1.95", "the block before, which holds 64 to 95"),
    ("same-subnet", "192.168.1.126", "126 is the last usable address of the block 96 to 127"),
    ("same-subnet", "192.168.1.128", "the next block, which holds 128 to 159"),
    ("subnets-from-24", "8", "8 would be the count for /27 subnets"),
    ("subnets-from-24", "16", "each with 16 addresses"),
    ("wildcard", "0.0.16.255", "16 is the block size in the third octet for this mask"),
    ("containing-subnet", "10.1.0.0/21", "That block covers 10.1.0.0 to 10.1.7.255"),
    ("containing-subnet", "10.1.8.0/21", "which covers 10.1.8.0 to 10.1.15.255"),
    ("containing-subnet", "10.1.9.0/21", "10.1.9.0 is not a /21 boundary"),
    ("containing-subnet", "10.1.9.0/21", "It is an address inside 10.1.8.0/21"),
    ("containing-subnet", "10.1.16.0/21", "That block starts at 10.1.16.0, which is above the address"),
    ("summary-route", "192.168.8.0/23", "only two of the four /24 blocks: 192.168.8.0 and 192.168.9.0"),
    ("summary-route", "192.168.8.0/22", "make one /22: 192.168.8.0 to 192.168.11.255"),
    ("summary-route", "192.168.8.0/21", "A /21 covers eight /24 blocks, 192.168.8.0 to 192.168.15.255"),
    ("summary-route", "192.168.0.0/20", "covers 192.168.0.0 to 192.168.15.255: sixteen /24 blocks"),
]


def verify(inst):
    errors, rows = [], []
    items = {q.get("id"): q for q in inst.get("questions", []) if isinstance(q, dict)}
    for qid in sorted(set(items) - set(ANSWERS)):
        errors.append("item %r is in the quiz but this script has no computation for it, so its key is unverified" % qid)
    for qid in sorted(set(ANSWERS) - set(items)):
        errors.append("item %r is missing from the quiz" % qid)
    for qid, fn in ANSWERS.items():
        q = items.get(qid)
        if q is None:
            continue
        texts = [o["text"] for o in q["options"]]
        marked = {o["text"] for o in q["options"] if o.get("correct") is True}
        computed = fn(texts)
        ok = marked == computed and computed <= set(texts)
        rows.append({"id": qid, "computed": sorted(computed), "marked": sorted(marked), "ok": ok})
        if not computed <= set(texts):
            errors.append("%s: the computed answer %s is not among the options" % (qid, sorted(computed)))
        elif not ok:
            errors.append("%s: the quiz marks %s as correct but ipaddress gives %s" % (qid, sorted(marked), sorted(computed)))
    if len(WHERE) != len(CLAIMS):
        errors.append("CLAIMS has %d entries and WHERE has %d; each figure needs the place it is quoted" % (len(CLAIMS), len(WHERE)))
    good = 0
    for (text, true), (qid, option, phrase) in zip(CLAIMS, WHERE):
        said = [o.get("explain", "") for o in items.get(qid, {}).get("options", []) if isinstance(o, dict) and o.get("text") == option]
        if not true:
            errors.append("claim used in an explanation is false: " + text)
        elif not said:
            errors.append("%s: option %r, whose explanation was checked for the figure %r, is no longer in the quiz" % (qid, option, text))
        elif phrase not in said[0]:
            errors.append("%s, option %r: the explanation no longer says %r, the wording checked for the figure %r. Check the new wording and update CLAIMS and WHERE"
                          % (qid, option, phrase, text))
        else:
            good += 1
    return errors, rows, good


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    unknown = [a for a in argv if a.startswith("--") and a != "--json"]
    if unknown:
        print("verify_subnetting: unknown option " + unknown[0], file=sys.stderr)
        return 2
    if len(args) != 1:
        print("verify_subnetting: expected one file. Usage: verify_subnetting.py QUIZ [--json]", file=sys.stderr)
        return 2
    try:
        inst, _kind = load_instrument(args[0])
    except InputError as e:
        print("verify_subnetting: %s" % e, file=sys.stderr)
        return 2
    errors, rows, claims_ok = verify(inst)
    if "--json" in argv:
        text = json.dumps({"errors": errors, "items": rows, "claims_true": claims_ok, "claims": len(CLAIMS)}, indent=1, ensure_ascii=True)
    else:
        L = ["verify_subnetting: %s" % args[0]]
        for r in rows:
            L.append("  %-4s %-18s computed %s" % ("OK" if r["ok"] else "BAD", r["id"], ", ".join(r["computed"])))
        L += ["  ERROR  " + e for e in errors]
        L.append("RESULT: %s. %d of %d answer key(s) match ipaddress; %d of %d quoted figure(s) are true and still worded as checked."
                 % ("FAIL" if errors else "PASS", sum(1 for r in rows if r["ok"]), len(ANSWERS), claims_ok, len(CLAIMS)))
        text = "\n".join(L)
    sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
