@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m bots.sofiabot_inasistencias_app
) else (
    python -m bots.sofiabot_inasistencias_app
)

endlocal
