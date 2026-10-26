@echo off
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"
set "HF_HOME=%ROOT%\.models"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Setting up Tasjeel for the first time. This takes a few minutes...
    python -m venv .venv || goto :failed
    ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :failed
    ".venv\Scripts\python.exe" -m pip install -e . || goto :failed
)

start "" ".venv\Scripts\pythonw.exe" -m tasjeel
exit /b 0

:failed
echo.
echo Tasjeel could not be set up. Check that Python 3.10+ is installed and online.
pause
exit /b 1
