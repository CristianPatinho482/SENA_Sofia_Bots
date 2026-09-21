@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No se encontro .venv\Scripts\python.exe
    echo Crea el entorno virtual e instala requirements.txt antes de generar el ejecutable.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Fallo instalando requirements.txt
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo Fallo instalando Chromium de Playwright
    pause
    exit /b 1
)

set ADD_ASSETS=--add-data "assets\SOFIABOT.png;assets" --add-data "assets\SOFIABOT.ico;assets"
if exist "assets\BOT_REPORTES.png" set ADD_ASSETS=%ADD_ASSETS% --add-data "assets\BOT_REPORTES.png;assets"

set ADD_BROWSERS=--add-data "%LOCALAPPDATA%\ms-playwright\chromium-1223;ms-playwright\chromium-1223" --add-data "%LOCALAPPDATA%\ms-playwright\chromium_headless_shell-1223;ms-playwright\chromium_headless_shell-1223" --add-data "%LOCALAPPDATA%\ms-playwright\ffmpeg-1011;ms-playwright\ffmpeg-1011" --add-data "%LOCALAPPDATA%\ms-playwright\winldd-1007;ms-playwright\winldd-1007"

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name SOFIABOT_Inasistencias_Completo --icon assets\SOFIABOT.ico %ADD_ASSETS% %ADD_BROWSERS% --collect-all playwright --collect-all greenlet --hidden-import greenlet --hidden-import pyee --hidden-import pandas --hidden-import openpyxl --hidden-import PIL bots\sofiabot_inasistencias_app.py

echo.
echo Ejecutable generado en:
echo dist\SOFIABOT_Inasistencias_Completo.exe
pause

endlocal
