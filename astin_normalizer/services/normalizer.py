"""Transformación de registros enriquecidos al modelo lógico."""

import pandas as pd

from config import NormalizerConfig


class Normalizer:
    """Estandariza los campos de negocio antes de construir dimensiones."""

    def __init__(self, config: NormalizerConfig) -> None:
        self.config = config

    def normalize(self, records: pd.DataFrame) -> pd.DataFrame:
        """Produce una fila por medida numérica para mantener primera forma normal."""
        contexts = ["programa", "categoria", "estrategia", "nivel", "modalidad", "periodo", "indicador", "descripcion"]
        numeric = [column for column in records.columns if column not in contexts and records[column].map(self._is_number).any()]
        if not numeric:
            return pd.DataFrame(columns=contexts + ["indicador", "valor"])
        melted = records.melt(id_vars=[field for field in contexts if field in records], value_vars=numeric,
                              var_name="medida_origen", value_name="valor")
        # Un indicador explícito prevalece; de no existir, el nombre de medida es el indicador.
        if "indicador" in melted:
            melted["indicador"] = melted["indicador"].fillna(melted["medida_origen"])
        else:
            melted["indicador"] = melted["medida_origen"]
        melted["valor"] = pd.to_numeric(melted["valor"], errors="coerce")
        return melted.dropna(subset=["valor"])

    @staticmethod
    def _is_number(value: object) -> bool:
        return pd.notna(pd.to_numeric(value, errors="coerce"))
