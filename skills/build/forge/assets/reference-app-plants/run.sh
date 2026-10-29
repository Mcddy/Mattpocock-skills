#!/bin/sh
# Starts Plant Round from source on macOS or Linux. Data goes in ./data. Ctrl+C stops it.
cd "$(dirname "$0")" || exit 1
mkdir -p data
python3 app/server.py --port 8710 --db data/plants.db &
PID=$!
trap 'kill $PID 2>/dev/null' INT TERM EXIT
sleep 1
(xdg-open http://127.0.0.1:8710/ || open http://127.0.0.1:8710/) >/dev/null 2>&1 &
echo "Plant Round on http://127.0.0.1:8710/  (Ctrl+C stops it)"
wait $PID
