"""Detección de registros que representan una meta atómica."""

import re

import pandas as pd

from config import NormalizerConfig


class SubtotalDetector:
    """Descarta totales mediante texto, fórmulas y densidad de valores."""

    def __init__(self, config: NormalizerConfig) -> None:
        self.pattern = re.compile("|".join(config.total_patterns), re.IGNORECASE)

    def is_subtotal(self, row: pd.Series, has_formula: bool) -> bool:
        """Indica si la fila no debe considerarse un dato base."""
        values = " ".join(str(value) for value in row.dropna())
        return has_formula or bool(self.pattern.search(values))

    def reported_total(self, row: pd.Series) -> float | None:
        """Obtiene la mayor medida de una fila explícitamente marcada como total."""
        values = " ".join(str(value) for value in row.dropna())
        if not self.pattern.search(values):
            return None
        measures = pd.to_numeric(row, errors="coerce").dropna()
        return float(measures.max()) if not measures.empty else None


class AtomicRecordDetector:
    """Conserva filas con al menos una medida numérica y sin rasgos de resumen."""

    def __init__(self, config: NormalizerConfig) -> None:
        self.config = config

    def detect(self, rows: pd.DataFrame, formula_rows: set[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Devuelve filas atómicas y bitácora de descartes."""
        kept, events = [], []
        subtotal = SubtotalDetector(self.config)
        numeric_columns = self._numeric_columns(rows)
        for index, row in rows.iterrows():
            has_formula = index in formula_rows
            reason = ""
            if row.dropna().empty:
                reason = "Fila vacía"
            elif subtotal.is_subtotal(row, has_formula):
                reason = "Total, subtotal o fórmula"
            elif not any(pd.notna(pd.to_numeric(row[column], errors="coerce")) for column in numeric_columns):
                reason = "Sin medida numérica"
            if reason:
                events.append({"FilaOrigen": index + 1, "Accion": "Descartada", "Motivo": reason})
            else:
                kept.append(index)
                events.append({"FilaOrigen": index + 1, "Accion": "Conservada", "Motivo": "Registro atómico"})
        return rows.loc[kept].copy(), pd.DataFrame(events)

    def _numeric_columns(self, rows: pd.DataFrame) -> list[str]:
        alias_columns = [column for column in rows.columns if any(alias in str(column).lower() for alias in self.config.aliases["medida"])]
        return alias_columns or list(rows.columns)
