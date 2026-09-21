"""Lectura segura de libros Excel."""

from pathlib import Path
from typing import Dict

import openpyxl
import pandas as pd


class ExcelReader:
    """Obtiene los valores mostrados y detecta fórmulas sin editar el libro."""

    def read_all_sheets(self, path: Path) -> Dict[str, pd.DataFrame]:
        """Lee todas las hojas preservando filas sin encabezado."""
        return pd.read_excel(path, sheet_name=None, header=None, dtype=object)

    def formula_cells(self, path: Path) -> Dict[str, set[tuple[int, int]]]:
        """Retorna coordenadas (fila, columna) de celdas con fórmula."""
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
        found: Dict[str, set[tuple[int, int]]] = {}
        for sheet in workbook.worksheets:
            found[sheet.title] = {
                (cell.row - 1, cell.column - 1)
                for row in sheet.iter_rows() for cell in row
                if isinstance(cell.value, str) and cell.value.startswith("=")
            }
        workbook.close()
        return found
