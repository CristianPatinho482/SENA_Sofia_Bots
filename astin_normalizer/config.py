"""Configuración y vocabulario extensible de la transformación."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class NormalizerConfig:
    """Centraliza reglas que pueden variar entre formatos de origen."""

    output_filename: str = "ASTIN_Modelo_Estrella.xlsx"
    center_name: str = "Centro ASTIN"
    total_patterns: List[str] = field(default_factory=lambda: [
        r"\btotal(?:es)?\b", r"\bsubtotal(?:es)?\b", r"\bacumulado\b",
    ])
    aliases: Dict[str, List[str]] = field(default_factory=lambda: {
        "programa": ["programa", "formacion", "área", "area"],
        "categoria": ["categoria", "categoría", "línea", "linea"],
        "estrategia": ["estrategia"],
        "nivel": ["nivel"],
        "modalidad": ["modalidad"],
        "periodo": ["periodo", "período", "mes", "fecha", "vigencia"],
        "medida": ["meta", "cantidad", "valor", "total", "número", "numero"],
        "descripcion": ["descripción", "descripcion", "actividad", "concepto"],
        "indicador": ["indicador", "meta", "nombre indicador"],
    })

    @classmethod
    def from_json(cls, path: Path | None = None) -> "NormalizerConfig":
        """Carga reglas externas, usando valores seguros cuando no existe archivo."""
        if path is None or not path.exists():
            return cls()
        with path.open(encoding="utf-8") as config_file:
            data = json.load(config_file)
        return cls(**data)
