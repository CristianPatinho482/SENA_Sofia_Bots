"""Construcción de dimensiones conformadas y tabla de hechos."""

from typing import Dict

import pandas as pd

from config import NormalizerConfig


class DimensionBuilder:
    """Construye dimensiones con claves sustitutas estables dentro de la ejecución."""

    DIMENSIONS = {
        "Programa": "programa", "Categoria": "categoria", "Nivel": "nivel",
        "Modalidad": "modalidad", "Estrategia": "estrategia", "Periodo": "periodo",
        "Indicador": "indicador",
    }

    def __init__(self, config: NormalizerConfig) -> None:
        self.config = config

    def build(self, records: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Crea una dimensión por atributo contextual más el centro institucional."""
        dimensions: Dict[str, pd.DataFrame] = {}
        for name, source in self.DIMENSIONS.items():
            values = records[source] if source in records else pd.Series(dtype=object)
            frame = pd.DataFrame({source.capitalize(): values.fillna("No especificado").astype(str).unique()})
            frame.insert(0, f"Id{name}", range(1, len(frame) + 1))
            dimensions[f"Dim{name}"] = frame
        dimensions["DimCentro"] = pd.DataFrame({"IdCentro": [1], "Centro": [self.config.center_name]})
        return dimensions


class FactTableBuilder:
    """Reemplaza atributos de negocio por claves foráneas."""

    def build(self, records: pd.DataFrame, dimensions: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Genera FactMetas sin atributos repetidos de dimensión."""
        fact = records.copy().reset_index(drop=True)
        for dim_name, source in DimensionBuilder.DIMENSIONS.items():
            key, label = f"Id{dim_name}", source.capitalize()
            lookup = dimensions[f"Dim{dim_name}"].set_index(label)[key]
            fact[key] = fact[source].fillna("No especificado").astype(str).map(lookup)
        fact["IdCentro"] = 1
        final_columns = ["IdPrograma", "IdCategoria", "IdNivel", "IdModalidad", "IdEstrategia", "IdPeriodo", "IdCentro", "IdIndicador", "descripcion", "valor"]
        return fact.reindex(columns=final_columns).rename(columns={"descripcion": "Descripcion", "valor": "ValorMeta"})


# Alias de compatibilidad para las integraciones iniciales del MVP.
FactBuilder = FactTableBuilder
