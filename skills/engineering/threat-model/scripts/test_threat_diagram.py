#!/usr/bin/env python3
"""Tests for threat_diagram.py. Standard library only; no browser is needed.

Usage:
  python test_threat_diagram.py [-v]

These tests cover what the generator writes: that it refuses a model it should not draw, that the
model is embedded intact, that no string from the model can end the data block, that the output
is the same bytes each time, and that the page it writes asks nothing of the network and uses
none of the things a sandboxed frame blocks. They build their models from the shipped template
model in assets/ and write only inside a temporary folder.

They do not open the page. How it renders, whether its controls work and whether its text has
enough contrast are checked in a browser with delivery_check.py, contrast_check.py,
target_size.py and dead_controls.py, and by looking at it.

Exit codes: 0 every test passed. 1 a test failed.
"""
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRIPT = str(HERE / "threat_diagram.py")
TEMPLATE_MODEL = HERE.parent / "assets" / "threat-model-template.json"
HOSTILE = '</script><script>window.__planted=1</script><!-- <img src=x onerror="window.__planted=2"> & "q"'


def embedded(page):
    m = re.search(r'<script type="application/json" id="model-data">(.*?)</script>', page, re.S)
    return json.loads(m.group(1)) if m else None


class Generator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.model = json.loads(TEMPLATE_MODEL.read_bytes().decode("utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, model):
        p = self.dir / name
        p.write_bytes(json.dumps(model).encode("utf-8"))
        return p

    def call(self, *args):
        r = subprocess.run([sys.executable, "-B", SCRIPT] + [str(a) for a in args], capture_output=True, timeout=60)
        return r.returncode, r.stdout.decode("utf-8"), r.stderr.decode("utf-8")

    def test_a_clean_model_is_drawn_and_embedded_intact(self):
        src, out = self.write("m.json", self.model), self.dir / "d.html"
        code, text, err = self.call(src, "--out", out, "--today", "2026-10-09")
        self.assertEqual(code, 0, err)
        self.assertIn("6 threat(s)", text)
        data = embedded(out.read_text(encoding="utf-8"))
        self.assertEqual(data["model"], self.model)
        self.assertEqual(data["source"], "m.json")
        self.assertEqual(data["derived"]["threat_state"]["T1"], "open_built_unverified")
        self.assertEqual(data["derived"]["boundary"], {"F1": True, "F2": False, "F3": True, "F4": True, "F5": False})
        self.assertEqual(data["check"]["errors"], [])

    def test_output_is_the_same_bytes_each_time(self):
        src = self.write("m.json", self.model)
        a, b = self.dir / "a.html", self.dir / "b.html"
        self.assertEqual(self.call(src, "--out", a, "--today", "2026-10-09")[0], 0)
        self.assertEqual(self.call(src, "--out", b, "--today", "2026-10-09")[0], 0)
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_planted_string_that_tries_to_end_the_data_block_stays_data(self):
        m = copy.deepcopy(self.model)
        m["system"] = "Planted " + HOSTILE
        m["elements"][0]["name"] = HOSTILE
        m["threats"][0]["impact"] = "Planted impact " + HOSTILE
        src, out = self.write("m.json", m), self.dir / "d.html"
        self.assertEqual(self.call(src, "--out", out, "--today", "2026-10-09")[0], 0)
        page = out.read_text(encoding="utf-8")
        self.assertNotIn("window.__planted=1</script>", page)
        self.assertNotIn("<img src=x", page)
        self.assertEqual(page.count("</script>"), 2)            # the data block and the page's own script, nothing more
        self.assertEqual(embedded(page)["model"]["system"], "Planted " + HOSTILE)

    def test_a_model_with_checker_errors_is_not_drawn(self):
        m = copy.deepcopy(self.model)
        m["threats"][0]["status"] = "mitigated"                  # its verification has never run
        src, out = self.write("m.json", m), self.dir / "d.html"
        code, text, err = self.call(src, "--out", out, "--today", "2026-10-09")
        self.assertEqual(code, 1)
        self.assertFalse(out.exists())
        self.assertIn("[mitigated_unverified]", text)
        self.assertIn("nothing was written", err)

    def test_allow_errors_draws_it_and_embeds_the_errors_for_the_banner(self):
        m = copy.deepcopy(self.model)
        m["threats"][0]["status"] = "mitigated"
        src, out = self.write("m.json", m), self.dir / "d.html"
        code, _, err = self.call(src, "--out", out, "--today", "2026-10-09", "--allow-errors")
        self.assertEqual(code, 0, err)
        data = embedded(out.read_text(encoding="utf-8"))
        self.assertEqual([e["code"] for e in data["check"]["errors"]], ["mitigated_unverified"])
        self.assertEqual(data["derived"]["threat_state"]["T1"], "mitigated_claim_unsupported")

    def test_a_model_with_broken_structure_is_never_drawn(self):
        m = copy.deepcopy(self.model)
        m["flows"][0]["to"] = "E99"
        src, out = self.write("m.json", m), self.dir / "d.html"
        code, _, err = self.call(src, "--out", out, "--today", "2026-10-09", "--allow-errors")
        self.assertEqual(code, 1)
        self.assertFalse(out.exists())
        self.assertIn("structure is broken", err)

    def test_bad_arguments_exit_two_and_the_input_is_never_overwritten(self):
        src = self.write("m.json", self.model)
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        for args in ([src], [src, "--out"], [src, "--out", src], [src, "--out", self.dir / "d.html", "--frobnicate"],
                     [src, "--out", self.dir / "d.html", "--today", "09-10-2026"], [self.dir / "none.json", "--out", self.dir / "d.html"],
                     [src, "--out", self.dir / "d.html", "--template", self.dir / "none.html"]):
            code, _, err = self.call(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(len(err.strip().splitlines()), 1, err)
            self.assertNotIn("Traceback", err)
        self.assertEqual(before, hashlib.sha256(src.read_bytes()).hexdigest())
        self.assertFalse((self.dir / "d.html").exists())

    def test_the_page_asks_nothing_of_the_network_and_uses_nothing_a_sandboxed_frame_blocks(self):
        src, out = self.write("m.json", self.model), self.dir / "d.html"
        self.assertEqual(self.call(src, "--out", out, "--today", "2026-10-09")[0], 0)
        page = out.read_text(encoding="utf-8")
        shell = re.sub(r'<script type="application/json" id="model-data">.*?</script>', "", page, flags=re.S)
        for pattern in (r"<form\b", r"\balert\(", r"\bconfirm\(", r"\bprompt\(", r"<link\b", r"@import", r"\bfetch\(", r"XMLHttpRequest",
                        r"(?:src|href)\s*=\s*[\"']https?:", r"url\(\s*[\"']?https?:", r"innerHTML", r"document\.write", r"user-scalable", r"maximum-scale"):
            self.assertIsNone(re.search(pattern, shell), pattern)
        self.assertEqual(len(re.findall(r"<script\b", page)), 2)
        self.assertIn('lang="en"', page)
        page.encode("ascii")                                     # the template and the embedded data are plain ASCII


if __name__ == "__main__":
    unittest.main()
