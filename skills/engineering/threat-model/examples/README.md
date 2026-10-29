# Examples

One worked example, made by the session that wrote this skill by following the skill's own procedure. It has not been run or reviewed independently.

## stock-count

A threat model of the forge skill's reference app (`assets/reference-app/server.py` and `index.html` in that skill): one page, one API, one SQLite file, no login. The question modelled is what happens if its server is bound to a network address so a phone can reach it, which that app's README says is not built. The app's files were read and run, and not changed.

| File | What it is |
|---|---|
| `threat-model.json` | The model: 3 zones, 8 elements, 9 flows, 13 threats, 13 mitigations, 13 verifications. Nine threats are open, because the app has no login, allows any origin, has no request limit and no backup |
| `threat-check-output.txt` | What `threat_check.py` printed for it on 9 Oct 2026: PASS, 0 errors, 4 advisory notes |
| `verify_stock_count.py` | The verifications as one script. It starts the app on loopback with a throwaway database, runs 10 checks and one baseline, and stops the app |
| `verification-output.txt` | What that script printed on 9 Oct 2026 against the unmodified app: 7 pass, 4 fail. The 4 failures are the tests for controls the app does not have; they are recorded in the model as `fail` and their threats are open |
| `diagram.html` | The drawing made by `threat_diagram.py`. Open it in a browser |
| `diagram-steps.txt` | The reading journey used to check the drawing in a tab and in a sandboxed frame |
| `reply.md` | The reply the skill's Output section asks for, written from the files above |

### Regenerate

From the skill folder, with `APP` set to the folder that holds the reference app's `server.py` and `SCRATCH` to an empty folder:

```bash
python examples/stock-count/verify_stock_count.py --app "$APP" --port 8220 --scratch "$SCRATCH"
python scripts/threat_check.py examples/stock-count/threat-model.json
python scripts/threat_diagram.py examples/stock-count/threat-model.json --out examples/stock-count/diagram.html
```

The verification script exits 1 today, because four of its checks fail on purpose: they are the tests for mitigations that are not built. If the results differ from `verification-output.txt`, update `last_result` and `last_run` in the model before running the checker.

The drawing embeds the checker's result, which depends on the day (verifications go stale after 90 days). Pass `--today 2026-10-09` to both scripts to reproduce the shipped files byte for byte.

### What was shown to fail

- The same verification script against a scratch copy of the app with six controls removed: all six passing checks failed.
- The baseline against a scratch copy listening on every address: failed.
- `threat_check.py` on this model with T1 marked mitigated and the threat on F5 removed: two errors, and `threat_diagram.py` refused to draw it.
