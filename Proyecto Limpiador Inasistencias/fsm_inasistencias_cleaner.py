"""Punto de entrada independiente del limpiador FSM de inasistencias.

La implementacion vive en `sofia_bots.inasistencias_cleaner` para que el bot
pueda integrarla y para que PyInstaller la empaquete en el ejecutable.
Este archivo conserva la compatibilidad con el proyecto original:

  python fsm_inasistencias_cleaner.py [entrada [salida]]
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
if str(_RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_PROYECTO))

from sofia_bots.inasistencias_cleaner import (  # noqa: E402
    COLUMNAS_SALIDA,
    ENTRADA_PREDETERMINADA,
    SALIDA_PREDETERMINADA,
    EstadoFSM,
    LimpiadorInasistenciasFSM,
    limpiar_inasistencias,
    main,
)

__all__ = [
    "COLUMNAS_SALIDA",
    "ENTRADA_PREDETERMINADA",
    "SALIDA_PREDETERMINADA",
    "EstadoFSM",
    "LimpiadorInasistenciasFSM",
    "limpiar_inasistencias",
    "main",
]

if __name__ == "__main__":
    raise SystemExit(main())
