@echo off
rem Starts Plant Round from source, the way a developer runs it. Needs Python 3.11 or newer.
rem Data goes in the data folder here. Close the server window to stop.
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py -3
if not exist data mkdir data
start "Plant Round server (close to stop)" %PY% app\server.py --port 8710 --db data\plants.db
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8710/
