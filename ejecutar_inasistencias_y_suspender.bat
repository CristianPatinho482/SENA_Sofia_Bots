@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m bots.descargar_inasistencias --reintentos-servidor 120 --espera-servidor 60 --suspender-al-final --espera-suspension 60
) else (
    python -m bots.descargar_inasistencias --reintentos-servidor 120 --espera-servidor 60 --suspender-al-final --espera-suspension 60
)

endlocal
