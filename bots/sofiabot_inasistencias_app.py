from __future__ import annotations

import sys
import traceback
from tkinter import messagebox

from bots.descargar_inasistencias import main


def run_app() -> None:
    """Entrada grafica para ejecutar el bot desde un icono o un .exe."""
    default_args = [
        "--pedir-credenciales",
        "--reintentos-servidor",
        "120",
        "--espera-servidor",
        "60",
    ]
    sys.argv = [sys.argv[0], *default_args, *sys.argv[1:]]

    try:
        main()
    except Exception as exc:
        messagebox.showerror(
            "SOFIABOT - Error",
            f"No fue posible completar la descarga.\n\n{exc}\n\n{traceback.format_exc()}",
        )


if __name__ == "__main__":
    run_app()
