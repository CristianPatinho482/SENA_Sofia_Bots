@echo off
setlocal
cd /d "%~dp0"

if exist "C:\Python314\python.exe" (
    "C:\Python314\python.exe" "%~dp0renumerar_pdfs_primer_trimestre.py"
) else (
    py "%~dp0renumerar_pdfs_primer_trimestre.py"
)

echo.
pause
