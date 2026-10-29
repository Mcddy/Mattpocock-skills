#!/bin/sh
# Full verification run, from forge's assets/reference-app-plants. Starts its own servers on 8711-8716 and stops each by PID.
mkdir -p "$(dirname "$0")/../data" "$(dirname "$0")/render"
cd "$(dirname "$0")/.." || exit 2
S=$(cd ../../scripts && pwd); R=$PWD/checks/render; AXE_DIR=${AXE_DIR:-$PWD}  # a folder with node_modules/axe-core, if you have one
python3 checks/make_api_steps.py >/dev/null
rm -f data/api-check.db* data/clock-*.db*
python3 $S/api_check.py http://127.0.0.1:8711 checks/api-steps.json --start "python3 app/server.py --port 8711 --db data/api-check.db --faults" > checks/api-check.txt 2>&1; echo "api_check main: exit $? $(tail -1 checks/api-check.txt)"
python3 $S/api_check.py http://127.0.0.1:8711 checks/api-clock-a.json --start "python3 app/server.py --port 8711 --db data/clock-a.db --now 2026-10-23T13:59:59+00:00" > checks/api-clock-a.txt 2>&1; echo "api_check clock a: exit $? $(tail -1 checks/api-clock-a.txt)"
python3 $S/api_check.py http://127.0.0.1:8711 checks/api-clock-b.json --start "python3 app/server.py --port 8711 --db data/clock-b.db --now 2026-10-23T14:00:00+00:00" > checks/api-clock-b.txt 2>&1; echo "api_check clock b: exit $? $(tail -1 checks/api-clock-b.txt)"
for mode in plain reduced blocked; do
  rm -f data/ui-$mode.db*; python3 app/server.py --port 8712 --db data/ui-$mode.db > data/server-8712.log 2>&1 & PID=$!; sleep 0.8
  flag=""; [ $mode = reduced ] && flag="--reduced-motion"; [ $mode = blocked ] && flag="--block-outside"
  python3 $S/delivery_check.py http://127.0.0.1:8712/ --steps checks/ui-steps.txt --tab-only $flag > checks/delivery-$mode.txt 2>&1; echo "delivery_check $mode: exit $? $(tail -1 checks/delivery-$mode.txt)"
  kill $PID; wait $PID 2>/dev/null
done
rm -f data/sample.db*; python3 checks/seed_sample.py data/sample.db >/dev/null; python3 app/server.py --port 8713 --db data/sample.db > data/server-8713.log 2>&1 & SPID=$!
rm -f data/empty.db*; python3 app/server.py --port 8716 --db data/empty.db > data/server-8716.log 2>&1 & EPID=$!; sleep 0.8
( cd "$AXE_DIR"
  python3 $S/render_gate.py http://127.0.0.1:8713/ $R/populated --label "populated morning" > $R/populated.txt 2>&1; echo "render_gate populated: exit $?"
  python3 $S/render_gate.py http://127.0.0.1:8716/ $R/empty --label "empty, no plants" > $R/empty.txt 2>&1; echo "render_gate empty: exit $?"
  python3 $S/render_gate.py http://127.0.0.1:8713/ $R/error --label "load error" --prep-js "window.fetch = () => Promise.reject(new TypeError('blocked')); S.phase = 'loading'; await loadAll();" > $R/error.txt 2>&1; echo "render_gate error: exit $?"
  python3 $S/render_gate.py http://127.0.0.1:8713/ $R/refused --label "refused: duplicate name" --prep-js "document.getElementById('add-open').click(); document.getElementById('f-name').value='Monstera'; document.getElementById('f-every').value='7'; document.getElementById('k-split').checked=true; document.getElementById('add-go').click(); await new Promise(r=>setTimeout(r,700));" > $R/refused.txt 2>&1; echo "render_gate refused: exit $?"
  python3 $S/render_gate.py http://127.0.0.1:8713/ $R/success --label "after ticking Monstera" --prep-js "const b=[...document.querySelectorAll('#needs [data-act=water]')].find(x=>x.getAttribute('aria-label')==='Watered Monstera'); if (b) { b.click(); await new Promise(r=>setTimeout(r,800)); }" > $R/success.txt 2>&1; echo "render_gate success: exit $?" )
python3 $S/contrast_check.py http://127.0.0.1:8713/ --set "html@data-dir=fresh-green" > checks/contrast-fresh-green.txt 2>&1; echo "contrast populated: exit $? $(grep -c BELOW checks/contrast-fresh-green.txt) below"
python3 $S/contrast_check.py http://127.0.0.1:8713/ --set "html@data-dir=fresh-green" --click "#add-open" --click "#add-go" > checks/contrast-form-errors.txt 2>&1; echo "contrast form errors: exit $? $(grep -c BELOW checks/contrast-form-errors.txt) below"
python3 $S/contrast_check.py http://127.0.0.1:8716/ --click "#add-go" > checks/contrast-empty-errors.txt 2>&1; echo "contrast empty+errors: exit $? $(grep -c BELOW checks/contrast-empty-errors.txt) below"
python3 $S/target_size.py --page http://127.0.0.1:8713/ --width 390 > checks/target-size.txt 2>&1; echo "target_size populated: exit $? $(grep '^target_size' checks/target-size.txt)"
python3 $S/target_size.py --page http://127.0.0.1:8716/ --width 390 > checks/target-size-empty.txt 2>&1; echo "target_size empty/form: exit $? $(grep '^target_size' checks/target-size-empty.txt)"
python3 $S/ui_candidates.py app/index.html app/plant-art.js > checks/ui-candidates.txt 2>&1; echo "ui_candidates: exit $? $(tail -1 checks/ui-candidates.txt)"
kill $SPID $EPID; wait $SPID $EPID 2>/dev/null
rm -f data/dead.db* data/dead-empty.db*; python3 checks/seed_sample.py data/dead.db >/dev/null
python3 app/server.py --port 8714 --db data/dead.db > data/server-8714.log 2>&1 & DPID=$!; sleep 0.8
python3 $S/dead_controls.py http://127.0.0.1:8714/ --keyboard > checks/dead-controls.txt 2>&1; echo "dead_controls populated: exit $? $(grep '^dead_controls' checks/dead-controls.txt)"
kill $DPID; wait $DPID 2>/dev/null
python3 app/server.py --port 8714 --db data/dead-empty.db > data/server-8714.log 2>&1 & DPID=$!; sleep 0.8
python3 $S/dead_controls.py http://127.0.0.1:8714/ --keyboard > checks/dead-controls-empty.txt 2>&1; echo "dead_controls empty/form: exit $? $(grep '^dead_controls' checks/dead-controls-empty.txt)"
kill $DPID; wait $DPID 2>/dev/null
python3 -c "import sys; sys.path.insert(0,'app'); import server; server.migrate('data/shots.db')"
python3 app/server.py --port 8715 --db data/shots.db > data/server-8715.log 2>&1 & HPID=$!; sleep 0.8
python3 checks/shots.py 8715 > checks/shots-log.txt 2>&1; echo "shots: exit $?"
kill $HPID; wait $HPID 2>/dev/null
true
