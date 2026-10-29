#!/usr/bin/env python3
"""Put the example's synthetic stock into a running Stock count server. Standard library only.

Usage:  python seed.py http://127.0.0.1:8181 seed_items.json

It POSTs each item in the file to /api/items on a loopback address and prints what the server
answered. Run it once against a server started with a fresh, throwaway data file. An item whose
code is already there is reported and skipped. It refuses any address that is not 127.0.0.1 or
localhost, so it cannot be pointed at a real system by accident.

Exit codes: 0 every item was created or was already there. 1 the server refused an item.
2 bad arguments or an unreadable file.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main(argv):
    if len(argv) != 2 or not argv[0].startswith(("http://127.0.0.1:", "http://localhost:")):
        print(__doc__)
        return 2
    try:
        items = json.loads(Path(argv[1]).read_bytes().decode("utf-8-sig"))["items"]
    except (OSError, ValueError, KeyError) as e:
        print("seed: cannot read %s (%s)" % (argv[1], str(e)[:60]), file=sys.stderr)
        return 2
    bad = 0
    for item in items:
        req = urllib.request.Request(argv[0].rstrip("/") + "/api/items", data=json.dumps(item).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                print("created   %s" % json.loads(r.read())["sku"])
        except urllib.error.HTTPError as e:
            err = json.loads(e.read()).get("error", {})
            if err.get("code") == "duplicate_sku":
                print("already   %s" % item["sku"])
            else:
                bad += 1
                print("REFUSED   %s: %s %s" % (item["sku"], err.get("message"), err.get("fields")))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
