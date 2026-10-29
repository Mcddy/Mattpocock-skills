#!/usr/bin/env python3
"""Retained offline result-contract tests. No browser, network, deletion or installs.
All PNG/WebP bytes below are labelled stub markers, not real image captures.
Run: python test_result_contract.py --out NEW_DIRECTORY
"""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
import hashlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("state_gallery_under_test", HERE / "state_gallery.py")
sg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sg)

def facts(bad=False):
    return {"overflow_px": 20 if bad else 0, "overflow_from": ["#fixture"] if bad else [],
            "clipped_count": 0, "clipped": [], "contrast_measured": 1, "contrast_lowest": 7,
            "contrast_below": 0, "contrast_below_list": [], "contrast_not_measured": 0,
            "small_targets": 0, "small_targets_list": [], "targets_under_44": 0,
            "console_errors": 0, "console_messages": [], "failed_requests": 0, "failed_requests_list": [],
            "refused_answers": 0, "broken_answers": 0, "answers_list": [],
            "requests_aborted_on_purpose": 0, "requests_held_on_purpose": 0}

def plan():
    return {"title":"SYNTHETIC STUB FIXTURE","page":"fixture.html","uri":"file:///fixture.html",
            "sizes":[{"width":390,"height":844},{"width":1280,"height":800}],
            "themes":[{"name":"paper","sets":[],"steps":[]}],
            "states":[{"name":"sample","shows":"Stub, not a real capture","uri":"file:///fixture.html",
                       "page":"fixture.html","steps":[],"route_fail":[],"route_delay":[],"scroll_to":None}],
            "settle":0,"total":2,"file":"fixture.states.json"}

class Page:
    def __init__(self, owner):
        self.owner=owner; self.mouse=NS(move=lambda *a:None)
        self.main_frame=object()
    def goto(self,*a,**k): pass
    def wait_for_load_state(self,*a,**k): pass
    def wait_for_timeout(self,*a,**k): pass
    def close(self): pass
    def on(self,*a,**k): pass
    def add_style_tag(self,*a,**k): pass
    def evaluate(self, script, *args):
        if script==sg.ENCODE_JS:
            if self.owner.encoding_error: raise RuntimeError("STUB encoding failure")
            return {"url":"data:image/webp;base64,U1RVQl9OT1RfQU5fSU1BR0U=","w":390,"h":844,"scale":1}
        if script==sg.SHEET_BOXES_JS:
            return [{"n":1,"x":0,"y":0,"w":400,"h":400}]
        if script==sg.CONTRAST_JS:
            return [{"el":"p","text":"STUB","measured":True,"ratio":2 if self.owner.bad_capture else 7,
                     "need":4.5,"fg":"#333333","bg":"#555555"}]
        if script==sg.LAYOUT_JS:
            return {"overflow_px":0,"overflow_from":[],"clipped":[]}
        if script==sg.TARGETS_JS: return []
        return True
    def screenshot(self,path,**kwargs):
        if self.owner.screenshot_error or self.owner.sheet_error:
            raise RuntimeError("STUB screenshot/export failure")
        Path(path).write_bytes(b"STUB_NOT_A_REAL_PNG")
class Browser:
    def __init__(self, **config):
        self.encoding_error=config.get("encoding_error",False)
        self.screenshot_error=config.get("screenshot_error",False)
        self.sheet_error=config.get("sheet_error",False)
        self.bad_capture=config.get("bad_capture",False)
        self.close_error=config.get("close_error",False)
    def new_page(self,**kwargs): return Page(self)
    def new_context(self,**kwargs):
        return NS(new_page=lambda:Page(self),close=lambda:None)
    def close(self):
        if self.close_error: raise RuntimeError("STUB late browser close failure")
class Manager:
    def __init__(self,browser,launch_error=False,context_error=False):
        self.browser=browser; self.launch_error=launch_error; self.context_error=context_error
    def launch(self):
        if self.launch_error: raise RuntimeError("STUB missing Chromium")
        return self.browser
    def __enter__(self): return NS(chromium=NS(launch=self.launch))
    def __exit__(self,*args):
        if self.context_error: raise RuntimeError("STUB late context exit failure")

def run(out):
    out.mkdir(parents=True,exist_ok=False)
    results=[]
    def record(name, fn):
        try:
            evidence=fn()
            results.append({"test":name,"ok":True,"evidence":evidence})
        except Exception as exc:
            results.append({"test":name,"ok":False,"error":type(exc).__name__+": "+str(exc)})
    def need(value,message):
        if not value: raise AssertionError(message)
    def fixture(kind):
        def capture(browser,p,state,theme,size,png):
            if kind=="exception": raise RuntimeError("STUB capture exception")
            if kind=="unreached" or (kind=="mixed" and size["width"]==1280):
                return sg.missing_frame(state,theme,size,"STUB state not reached","state")
            bad=kind in ("bad","mixed")
            f=sg.missing_frame(state,theme,size,"","")
            f.update(reached=True,why_not="",facts=facts(bad),problems=sg.problems_of(facts(bad)),png=png.name)
            f["measured_facts"]=copy.deepcopy(f["facts"])
            f["measured_problems"]=list(f["problems"])
            png.write_bytes(b"STUB_NOT_A_REAL_PNG")
            return f
        return capture
    def build_case(name,kind="clean",expected="completed",exit_code=0,flags=None,actual_capture=False,durable_expected=True,**config):
        destination=out/name
        options={"--out":str(destination),"_states_path":str(out/"input.json"),
                 "_maxw":1280,"_quality":70,"_scale":1}
        use_flags={"--json"}|set(flags or ())
        browser=Browser(**config)
        module=ModuleType("playwright.sync_api")
        module.sync_playwright=lambda:Manager(browser,config.get("launch_error",False),config.get("context_error",False))
        root_module=ModuleType("playwright")
        root_module.sync_api=module
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.dict(sys.modules,{"playwright":root_module,"playwright.sync_api":module}), \
             contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr), \
             patch.object(sg,"capture_frame",sg.capture_frame if actual_capture else fixture(kind)):
            code=sg.build(plan(),options,use_flags)
        (out/(name+"-stdout.txt")).write_text(stdout.getvalue(),encoding="utf-8")
        (out/(name+"-stderr.txt")).write_text(stderr.getvalue(),encoding="utf-8")
        payload=json.loads(stdout.getvalue())
        need(code==exit_code,f"exit {code}, expected {exit_code}")
        need(payload["status"]==expected,f"status {payload['status']}, expected {expected}")
        need(payload["receipt"]["exit"]==code,"receipt exit differs")
        rows=[line for line in stderr.getvalue().splitlines() if line.startswith("RECEIPT ")]
        need(len(rows)==1,"exactly one receipt")
        need(json.loads(rows[0][8:])==payload["receipt"],"stdout/stderr receipt mismatch")
        if expected!="runner-error":
            durable=json.loads((destination/"gallery.json").read_text(encoding="utf-8")) if durable_expected else payload
            if not durable_expected:
                need(not payload["output"]["final_record_written"],"failed write claimed durable")
                need(len(payload["receipt"]["frame_evidence"])==2,"stderr receipt lost observed frames")
            need(durable["receipt"]==payload["receipt"],"durable receipt differs")
            need(durable["output"]==payload["output"],"durable output absent or stale")
            need(len(durable["frames"])==2,"requested combinations dropped")
            need(len({sg.frame_key(f) for f in durable["frames"]})==2,"duplicate frame keys")
            return {"status":expected,"exit":code,"coverage":payload["receipt"]["coverage"],
                    "summary":durable["summary"],"frames":durable["frames"]}
        return payload

    record("clean-completed-durable-output",lambda:build_case("clean"))
    record("known-defect-dominates-missing",lambda:build_case("mixed","mixed","failed"))
    record("unreached-only-partial",lambda:build_case("unreached","unreached","partial"))
    record("legacy-fail-on-problems-exit",lambda:build_case("bad-flag","bad","failed",1,{"--fail-on-problems"}))
    record("legacy-unreached-flag-stays-partial",lambda:build_case("unreached-flag","unreached","partial",1,{"--fail-on-problems"}))
    record("capture-exceptions-retain-combinations",lambda:build_case("capture-exception","exception","partial"))
    record("encoding-failure-retains-combinations",lambda:build_case("encoding","clean","partial",encoding_error=True))
    record("encoding-failure-retains-measured-defect",lambda:build_case("encoding-bad","bad","failed",encoding_error=True))
    record("sheet-failure-is-partial-and-durable",lambda:build_case("sheets","clean","partial",sheet_error=True))
    record("sheet-failure-does-not-hide-measured-defect",lambda:build_case("sheets-bad","bad","failed",sheet_error=True))
    record("no-sheets-explicit-not-applicable",lambda:build_case("no-sheets",flags={"--no-sheets"}))
    def screenshot_evidence():
        r=build_case("screenshot","clean","failed",actual_capture=True,screenshot_error=True,bad_capture=True)
        need(all(f["facts"] is None and f["measured_facts"]["contrast_below"]==1 for f in r["frames"]),
             "measured facts lost when screenshot failed")
        need(all(f["measured_problems"] and not f["reached"] for f in r["frames"]),"problem provenance lost")
        return r
    record("real-capture-function-preserves-facts-after-screenshot-error",screenshot_evidence)
    record("missing-chromium-runner-error",lambda:build_case("launch",expected="runner-error",exit_code=3,launch_error=True))
    def missing_package():
        output=io.StringIO(); errors=io.StringIO()
        with patch.dict(sys.modules,{"playwright":None,"playwright.sync_api":None}), \
             contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
            code=sg.build(plan(),{},{"--json"})
        payload=json.loads(output.getvalue())
        need(code==3 and payload["status"]=="runner-error","missing package not runner-error")
        return payload
    record("missing-playwright-runner-error-json",missing_package)
    record("known-defect-survives-late-close-error",lambda:build_case("late-close-bad","bad","failed",3,close_error=True))
    record("clean-captures-late-close-are-partial",lambda:build_case("late-close-clean","clean","partial",3,close_error=True))
    record("known-defect-survives-late-context-error",lambda:build_case("late-context-bad","bad","failed",3,context_error=True))
    record("clean-captures-late-context-are-partial",lambda:build_case("late-context-clean","clean","partial",3,context_error=True))
    def write_error():
        original=Path.write_text
        def fail_json(path,*args,**kwargs):
            if path.name=="gallery.json": raise OSError("STUB final JSON write denied")
            return original(path,*args,**kwargs)
        with patch.object(Path,"write_text",fail_json):
            return build_case("write-error",expected="partial",exit_code=3,durable_expected=False)
    record("final-json-write-failure-not-completed",write_error)
    def measured_write_error():
        original=Path.write_text
        def fail_json(path,*args,**kwargs):
            if path.name=="gallery.json": raise OSError("STUB final JSON write denied")
            return original(path,*args,**kwargs)
        with patch.object(Path,"write_text",fail_json):
            return build_case("write-error-bad","bad","failed",3,durable_expected=False)
    record("final-json-write-failure-preserves-measured-defect",measured_write_error)
    receipt={"scope":"Offline controlled stubs only. No browser, network, real images or deletion.",
             "script":str(HERE/"state_gallery.py"),
             "script_sha256":hashlib.sha256((HERE/"state_gallery.py").read_bytes()).hexdigest(),
             "harness_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"tests":results,
             "passed":sum(r["ok"] for r in results),"failed":sum(not r["ok"] for r in results)}
    (out/"results.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))
    return 1 if receipt["failed"] else 0
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(run(args.out))

