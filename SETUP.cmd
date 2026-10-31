@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Please install Python 3.10 or later from python.org, including the py launcher.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
call START.cmd
exit /b 0
:error
echo Setup failed. Please check your network and Python version.
pause
exit /b 1
