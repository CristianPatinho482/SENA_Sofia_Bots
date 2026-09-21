"""Identificación de encabezados en hojas no estructuradas."""

import re
from typing import List

import pandas as pd

from config import NormalizerConfig
from models.domain import AnalysisResult


class StructureAnalyzer:
    """Selecciona la fila que más se parece a una cabecera de datos."""

    def __init__(self, config: NormalizerConfig) -> None:
        self.config = config

    def analyze(self, sheet_name: str, raw: pd.DataFrame) -> AnalysisResult:
        """Convierte una hoja cruda en tabla, hallando una cabecera por puntuación."""
        if raw.empty:
            return AnalysisResult(sheet_name, 0, [], pd.DataFrame())
        header_row = max(range(min(len(raw), 30)), key=lambda idx: self._score(raw.iloc[idx]))
        headers = self._unique_headers(raw.iloc[header_row].tolist())
        rows = raw.iloc[header_row + 1:].copy()
        rows.columns = headers
        rows = rows.dropna(axis=1, how="all").dropna(how="all")
        return AnalysisResult(sheet_name, header_row, list(rows.columns), rows)

    def _score(self, row: pd.Series) -> int:
        text = " ".join(str(value).lower() for value in row.dropna())
        aliases = [item for values in self.config.aliases.values() for item in values]
        matches = sum(bool(re.search(rf"\b{re.escape(alias)}\b", text)) for alias in aliases)
        return matches * 10 + min(len(row.dropna()), 9)

    @staticmethod
    def _unique_headers(values: List[object]) -> List[str]:
        """Genera nombres de columna no vacíos y sin duplicados."""
        seen: dict[str, int] = {}
        result: List[str] = []
        for index, value in enumerate(values, start=1):
            base = str(value).strip() if pd.notna(value) else f"Columna_{index}"
            base = base or f"Columna_{index}"
            seen[base] = seen.get(base, 0) + 1
            result.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
        return result
