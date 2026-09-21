"""Inferencia de contrato dimensional desde el archivo normalizado de referencia."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd


@dataclass(frozen=True)
class BusinessModel:
    """Contrato inferido a partir de la estructura, no de datos copiados."""

    tables: Dict[str, List[str]]
    fact_name: str = "FactMetas"


class BusinessModelInferencer:
    """Lee sólo el esquema del modelo de referencia para validar la salida."""

    def infer(self, reference_path: Path | None) -> BusinessModel | None:
        """Extrae nombres de hojas y columnas de un libro modelo opcional."""
        if reference_path is None:
            return None
        sheets = pd.read_excel(reference_path, sheet_name=None, nrows=0)
        return BusinessModel({name: [str(column) for column in data.columns] for name, data in sheets.items()})

    @staticmethod
    def compare(expected: BusinessModel | None, generated: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Reporta diferencias de contrato sin copiar ni modificar el referente."""
        if expected is None:
            return pd.DataFrame([{"Control": "Modelo de referencia", "Valor": "No proporcionado", "Estado": "SIN COMPARACIÓN"}])
        rows = []
        for table, columns in expected.tables.items():
            if table not in generated:
                rows.append({"Control": f"Tabla {table}", "Valor": "Ausente", "Estado": "REVISAR"})
                continue
            absent = sorted(set(columns) - set(generated[table].columns))
            rows.append({"Control": f"Esquema {table}", "Valor": ", ".join(absent) if absent else "Coincide", "Estado": "REVISAR" if absent else "OK"})
        return pd.DataFrame(rows)
