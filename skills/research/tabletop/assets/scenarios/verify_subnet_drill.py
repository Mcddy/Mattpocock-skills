#!/usr/bin/env python3
"""Check the addressing facts of the subnet fault drill with Python's ipaddress module.

Usage:
  python verify_subnet_drill.py [SCENARIO.json] [--json]

With no file it reads subnet-fault-drill.json from the folder this script is in.

Why it exists: a study drill that teaches a wrong fact is worse than no drill. Every statement the
drill makes about addresses, masks and which hosts a machine believes are on its own network is
written as a claim in the scenario's "addressing" block, and this script works each one out again.

The "addressing" block:
  {"hosts": {"file server": "172.16.10.25", ...},
   "networks": {"VLAN 10 servers": "172.16.10.0/24", ...},
   "claims": [{"id": "C1", "kind": "...", "expect": ..., "says": "the sentence the drill relies on"}]}
Claim kinds:
  netmask       {"prefix": 16, "expect": "255.255.0.0"}
  network       {"interface": "172.16.10.25/16", "expect": "172.16.0.0/16"}   the network an interface is in
  on_link       {"interface": "172.16.10.25/16", "address": "172.16.20.57", "expect": true}
                does a host with that address and mask treat the other address as on its own network
  member        {"network": "172.16.20.0/24", "address": "172.16.20.57", "expect": true}
  overlap       {"a": "172.16.0.0/16", "b": "172.16.20.0/24", "expect": true}
  usable_hosts  {"network": "172.16.10.0/24", "expect": 254}       addresses minus network and broadcast

What it enforces (exit 1): a claim whose expected value is not what ipaddress computes; an address
or network written anywhere else in the scenario's text that the addressing block does not list
(so the story and the checked facts cannot drift apart); a host that sits in none, or more than
one, of the declared VLAN networks.
What it cannot tell: how a particular operating system or router behaves. It checks arithmetic on
addresses. That a host asks by ARP for anything its mask says is on-link is standard IPv4 host
behaviour and is stated in the drill, not proved here.

Exit codes: 0 every claim holds. 1 a claim fails. 2 bad arguments or unreadable input.
"""
import ipaddress
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADDRESS = re.compile(r"(?<!\d)(?<!\d\.)(\d{1,3}(?:\.\d{1,3}){3})(/\d{1,2})?(?!\d)(?!\.\d)")   # a full stop may follow
MASK_LIKE = re.compile(r"255\.\d+\.\d+\.\d+")


def strings(node, skip_key=None):
    """Every string in a JSON value, leaving out one top-level key."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for x in node:
            yield from strings(x)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k != skip_key:
                yield from strings(v)


def evaluate(c):
    """Return (computed value, problem). problem is None when the claim could be worked out."""
    kind = c.get("kind")
    try:
        if kind == "netmask":
            if isinstance(c.get("prefix"), bool) or not isinstance(c.get("prefix"), int):
                return None, "prefix must be a whole number"
            return str(ipaddress.ip_network("0.0.0.0/%d" % c["prefix"]).netmask), None
        if kind == "network":
            return str(ipaddress.ip_interface(c["interface"]).network), None
        if kind == "on_link":
            return ipaddress.ip_address(c["address"]) in ipaddress.ip_interface(c["interface"]).network, None
        if kind == "member":
            return ipaddress.ip_address(c["address"]) in ipaddress.ip_network(c["network"]), None
        if kind == "overlap":
            return ipaddress.ip_network(c["a"]).overlaps(ipaddress.ip_network(c["b"])), None
        if kind == "usable_hosts":
            net = ipaddress.ip_network(c["network"])
            if net.version != 4:
                return None, "usable_hosts supports IPv4 only; IPv6 subnet-router anycast semantics differ"
            return net.num_addresses if net.prefixlen >= 31 else net.num_addresses - 2, None
    except (KeyError, TypeError, ValueError) as e:
        return None, "could not be worked out (%s)" % str(e)[:80]
    return None, "unknown kind %r" % kind


def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return type(a) is type(b) and a == b


def verify(scenario):
    results, problems = [], []
    block = scenario.get("addressing") if isinstance(scenario, dict) else None
    if not isinstance(block, dict) or not isinstance(block.get("claims"), list) or not block["claims"]:
        return [], ["the scenario has no addressing block with claims to check"]
    hosts = block.get("hosts") if isinstance(block.get("hosts"), dict) else {}
    networks = block.get("networks") if isinstance(block.get("networks"), dict) else {}
    for c in block["claims"]:
        if not isinstance(c, dict):
            problems.append("a claim is not an object")
            continue
        got, problem = evaluate(c)
        ok = problem is None and same(got, c.get("expect"))
        results.append({"id": c.get("id", "?"), "kind": c.get("kind"), "expect": c.get("expect"), "computed": got, "ok": ok,
                        "problem": problem, "says": c.get("says", "")})
    # The story may only use addresses the block knows about.
    listed = set(str(v) for v in hosts.values()) | set(str(v) for v in networks.values())
    for c in block["claims"]:
        if isinstance(c, dict):
            for key in ("interface", "address", "network", "a", "b", "expect"):
                if isinstance(c.get(key), str):
                    listed.add(c[key])
                    listed.add(c[key].split("/")[0])
    for text in strings(scenario, skip_key="addressing"):
        for m in ADDRESS.finditer(text):
            whole_match, bare = m.group(0), m.group(1)
            if MASK_LIKE.fullmatch(bare):
                if bare not in listed:
                    problems.append("the text uses the mask %s, which no claim checks" % bare)
                continue
            if whole_match not in listed and bare not in listed:
                problems.append("the text mentions %s, which the addressing block does not list" % whole_match)
    # Every host belongs to exactly one declared VLAN network.
    vlans = {}
    for name, net in networks.items():
        try:
            n = ipaddress.ip_network(net)
        except ValueError:
            problems.append("network %r (%s) is not a valid network" % (name, net))
            continue
        if name.upper().startswith("VLAN"):
            vlans[name] = n
    for name, addr in hosts.items():
        try:
            a = ipaddress.ip_address(addr)
        except ValueError:
            problems.append("host %r (%s) is not a valid address" % (name, addr))
            continue
        homes = [v for v, n in vlans.items() if a in n]
        if len(homes) != 1:
            problems.append("host %r (%s) is in %d of the declared VLAN networks; it must be in exactly one" % (name, addr, len(homes)))
    return results, sorted(set(problems))


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a == "--json":
            flags.add(a)
        elif a.startswith("-") and a != "-":
            print("verify_subnet_drill: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) > 1:
        print("verify_subnet_drill: give at most one scenario file", file=sys.stderr)
        return 2
    path = Path(args[0]) if args else HERE / "subnet-fault-drill.json"
    try:
        raw = path.read_bytes()
        if b"\x00" in raw:
            raise ValueError("it contains a NUL byte")
        scenario = json.loads(raw.decode("utf-8-sig"))
    except OSError as e:
        print("verify_subnet_drill: cannot read %s: %s" % (path, e.strerror or e), file=sys.stderr)
        return 2
    except (UnicodeDecodeError, ValueError) as e:
        print("verify_subnet_drill: %s is not valid UTF-8 JSON (%s)" % (path, str(e)[:60]), file=sys.stderr)
        return 2
    results, problems = verify(scenario)
    failed = [r for r in results if not r["ok"]]
    if "--json" in flags:
        text = json.dumps({"claims": results, "problems": problems, "result": "FAIL" if failed or problems else "PASS"}, indent=1, ensure_ascii=True)
    else:
        L = ["verify_subnet_drill: %s" % path.name]
        for r in results:
            L.append("  %-4s %-4s %-12s expected %-16s computed %-16s %s" % ("PASS" if r["ok"] else "FAIL", r["id"], r["kind"], json.dumps(r["expect"]),
                                                                              json.dumps(r["computed"]) if r["problem"] is None else r["problem"], r["says"]))
        L += ["  FAIL " + p for p in problems]
        L.append("RESULT: %s. %d of %d claim(s) hold; %d other problem(s). This checks address arithmetic, not how any device behaves."
                 % ("FAIL" if failed or problems else "PASS", len(results) - len(failed), len(results), len(problems)))
        text = "\n".join(L)
    print(text.encode("ascii", "replace").decode("ascii"))
    return 1 if failed or problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
