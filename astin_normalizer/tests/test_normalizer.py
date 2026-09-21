"""Pruebas básicas de las reglas de depuración."""

import pandas as pd

from config import NormalizerConfig
from parsers.atomic_record_detector import AtomicRecordDetector


def test_detector_discards_totals_and_keeps_numeric_rows() -> None:
    """Las reglas no deben incluir filas con subtotal."""
    data = pd.DataFrame({"Meta": [10, 10], "Descripcion": ["Registro", "TOTAL programa"]})
    atomic, log = AtomicRecordDetector(NormalizerConfig()).detect(data, set())
    assert len(atomic) == 1
    assert log.iloc[1]["Accion"] == "Descartada"
