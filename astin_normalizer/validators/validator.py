"""Validación y trazabilidad de cantidades procesadas."""

import pandas as pd


class Validator:
    """Emite controles que permiten revisar el resultado en Power BI."""

    def validate(self, fact: pd.DataFrame, discarded_log: pd.DataFrame, original_total: float | None = None) -> pd.DataFrame:
        """Calcula indicadores de proceso y suma final de metas."""
        discarded = int((discarded_log.get("Accion", pd.Series(dtype=str)) == "Descartada").sum())
        fact_total = float(fact["ValorMeta"].sum()) if not fact.empty else 0
        original_status = "SIN TOTAL DETECTABLE" if original_total is None else ("OK" if abs(original_total - fact_total) < 0.0001 else "REVISAR")
        rows = [
            {"Control": "Registros atómicos", "Valor": len(fact), "Estado": "OK"},
            {"Control": "Filas descartadas", "Valor": discarded, "Estado": "REVISAR" if discarded else "OK"},
            {"Control": "Suma de metas (FactMetas)", "Valor": fact_total, "Estado": "OK"},
            {"Control": "Total original detectable", "Valor": original_total, "Estado": original_status},
            {"Control": "Valores nulos en hechos", "Valor": int(fact.isna().sum().sum()), "Estado": "REVISAR" if fact.isna().any().any() else "OK"},
        ]
        return pd.DataFrame(rows)
