"""Propagación de valores jerárquicos hacia registros inferiores."""

from typing import Dict

import pandas as pd

from config import NormalizerConfig


class HierarchyParser:
    """Reconstruye contexto mediante columnas explícitas y arrastre vertical."""

    CONTEXTS = ("programa", "categoria", "estrategia", "nivel", "modalidad", "periodo", "indicador")

    def __init__(self, config: NormalizerConfig) -> None:
        self.config = config

    def enrich(self, rows: pd.DataFrame) -> pd.DataFrame:
        """Añade campos canónicos y rellena hacia abajo valores de contexto."""
        result = rows.copy()
        for context in self.CONTEXTS:
            source = self._find_column(rows.columns, context)
            result[context] = rows[source] if source else pd.NA
            result[context] = result[context].replace(r"^\s*$", pd.NA, regex=True).ffill()
        description = self._find_column(rows.columns, "descripcion")
        result["descripcion"] = rows[description] if description else pd.NA
        return result

    def _find_column(self, columns: pd.Index, field: str) -> str | None:
        aliases = self.config.aliases[field]
        normalized: Dict[str, str] = {str(column).strip().lower(): str(column) for column in columns}
        return next((original for name, original in normalized.items() if any(alias in name for alias in aliases)), None)
