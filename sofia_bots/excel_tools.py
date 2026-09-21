from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def rename_first_worksheet(workbook_path: str | Path, sheet_name: str) -> Path:
    """Renombra la primera hoja usando Excel instalado en Windows.

    Los reportes de Sofia Plus suelen descargarse como .xls. Ese formato no se
    puede modificar con openpyxl, asi que usamos automatizacion COM mediante
    Windows Script Host para que Excel haga el guardado.
    """
    workbook = Path(workbook_path)
    if not workbook.exists():
        raise FileNotFoundError(f"No existe el archivo Excel: {workbook}")

    if not sheet_name or len(sheet_name) > 31 or any(ch in sheet_name for ch in r'[]:*?/\\'):
        raise ValueError("El nombre de hoja no es valido para Excel.")

    script = r'''
Option Explicit

Dim workbookPath, desiredName
Dim excel, workbook, worksheet, index, tempName

workbookPath = WScript.Arguments.Item(0)
desiredName = WScript.Arguments.Item(1)

On Error Resume Next

Set excel = CreateObject("Excel.Application")
If Err.Number <> 0 Then
    WScript.Echo "No fue posible iniciar Microsoft Excel: " & Err.Description
    WScript.Quit 1
End If

excel.Visible = False
excel.DisplayAlerts = False

Set workbook = excel.Workbooks.Open(workbookPath)
If Err.Number <> 0 Then
    WScript.Echo "No fue posible abrir el archivo: " & Err.Description
    excel.Quit
    WScript.Quit 1
End If

For index = 1 To workbook.Worksheets.Count
    Set worksheet = workbook.Worksheets(index)
    If LCase(worksheet.Name) = LCase(desiredName) And index <> 1 Then
        tempName = Left("__tmp_" & CStr(index) & "_" & Replace(CStr(Timer), ".", ""), 31)
        worksheet.Name = tempName
    End If
Next

workbook.Worksheets(1).Name = desiredName
If Err.Number <> 0 Then
    WScript.Echo "No fue posible renombrar la hoja: " & Err.Description
    workbook.Close False
    excel.Quit
    WScript.Quit 1
End If

workbook.Save
workbook.Close False
excel.Quit
WScript.Quit 0
'''

    with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="utf-8") as handle:
        script_path = Path(handle.name)
        handle.write(script)

    try:
        result = subprocess.run(
            ["cscript.exe", "//nologo", str(script_path), str(workbook), sheet_name],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    finally:
        try:
            script_path.unlink()
        except OSError:
            pass

    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()
        raise RuntimeError(f"No se pudo renombrar la hoja de Excel. {output}")

    return workbook
