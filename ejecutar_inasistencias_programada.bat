@echo off
rem Lanzador autonomo para Programador de tareas de Windows.
rem No pide credenciales: usa .env (SOFIA_USUARIO / SOFIA_PASSWORD / INASISTENCIAS_SALIDA).
rem No modifica los lanzadores manuales existentes.
setlocal

cd /d "%~dp0"

if not exist ".env" (
    echo [ERROR] No se encontro .env en %CD%. Copia .env.example como .env con credenciales validas.
    exit /b 1
)

if not exist "logs" mkdir "logs" >nul 2>&1
for /f %%i in ('powershell -noprofile -command "Get-Date -Format yyyyMMdd"') do set FECHA=%%i
set LOG=logs\inasistencias_programada_%FECHA%.log

if exist ".venv\Scripts\python.exe" (
    set PY=.venv\Scripts\python.exe
) else (
    set PY=python
)

echo [%date% %time%] Inicio ejecucion programada >> "%LOG%" 2>&1
"%PY%" -m bots.descargar_inasistencias --reintentos-servidor 120 --espera-servidor 60 >> "%LOG%" 2>&1
set CODE=%ERRORLEVEL%
echo [%date% %time%] Fin con codigo %CODE% >> "%LOG%" 2>&1
exit /b %CODE%
