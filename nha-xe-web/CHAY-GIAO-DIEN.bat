@echo off
cd /d "%~dp0"
if not exist node_modules (
  echo Run npm.cmd ci in this folder first.
  pause
  exit /b 1
)
echo Backend must be running on http://127.0.0.1:8765
call npm.cmd run dev
pause
