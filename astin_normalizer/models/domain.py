"""Modelos inmutables del proceso."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd


@dataclass
class AnalysisResult:
    """Resultado del análisis de una hoja de origen."""

    sheet_name: str
    header_row: int
    columns: List[str]
    rows: pd.DataFrame


@dataclass
class TransformationResult:
    """Modelo estrella y resultados de control."""

    fact: pd.DataFrame
    dimensions: Dict[str, pd.DataFrame]
    dictionary: pd.DataFrame
    log: pd.DataFrame
    validation: pd.DataFrame
    output_path: Path
