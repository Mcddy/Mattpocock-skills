@echo off
rem Builds the Windows app: dist\%APP%\%APP%.exe, with its icon. Double-click this file.
rem Needs Python 3.11 or newer from python.org. Everything it installs goes into .venv-build in this folder.
setlocal
set APP=PlantRound
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Python is not installed. Get it from https://www.python.org/downloads/ and tick "Add python.exe to PATH", then run this again.
  goto fail
)
if not exist .venv-build ( %PY% -m venv .venv-build || goto fail )
call .venv-build\Scripts\activate.bat || goto fail
python -m pip install --disable-pip-version-check -q -r requirements-build.txt || goto fail
echo Checking the app starts from source...
python launcher.py --self-test || goto fail
echo Building %APP%.exe...
pyinstaller --noconfirm --clean app.spec || goto fail
echo Checking the built app starts...
start "" /wait "dist\%APP%\%APP%.exe" --self-test || goto fail
if errorlevel 1 goto fail
echo.
echo Built: %CD%\dist\%APP%\%APP%.exe
echo Double-click it to run, or right-click it and choose Send to, Desktop (create shortcut).
echo Windows may warn that the app is unrecognised because it is not code-signed: choose More info, then Run anyway.
pause
exit /b 0
:fail
echo.
echo The build stopped. Read the message above. Nothing outside this folder was changed.
pause
exit /b 1
