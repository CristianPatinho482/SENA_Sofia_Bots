from __future__ import annotations

import sys
import traceback
from datetime import datetime
from tkinter import messagebox

from bots.descargar_inasistencias import main
from sofia_bots.credential_store import load_saved_credentials
from sofia_bots.settings import PROJECT_ROOT


def _configurar_diagnostico():
    """Redirige la salida a un log, incluso en el ejecutable sin consola."""
    log_dir = PROJECT_ROOT / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handle = open(
            log_dir / "sofiabot_app.log",
            "a",
            encoding="utf-8",
            buffering=1,
        )
    except Exception:
        return None

    sys.stdout = handle
    sys.stderr = handle
    print("\n" + "=" * 70)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Ejecutable: {sys.executable}")
    print(f"Argumentos: {sys.argv}")
    print(f"Congelado: {getattr(sys, 'frozen', False)}")
    print(f"Carpeta del proyecto: {PROJECT_ROOT}")
    return handle


def run_app() -> None:
    """Entrada grafica para ejecutar el bot desde un icono o un .exe.

    El cuadro de credenciales solo aparece cuando no hay datos guardados en
    ``.env`` o cuando Sofia Plus rechaza la clave (por ejemplo, porque exige
    cambiarla). En ejecuciones posteriores el bot reutiliza las credenciales.
    """
    log_handle = _configurar_diagnostico()

    default_args = [
        "--pedir-credenciales",
        "--reintentos-servidor",
        "120",
        "--espera-servidor",
        "60",
    ]
    sys.argv = [sys.argv[0], *default_args, *sys.argv[1:]]

    try:
        if load_saved_credentials() is None:
            messagebox.showinfo(
                "SOFIABOT - Primer uso",
                "Este boton solo necesita ejecutarse la primera vez.\n\n"
                "Ingresa tu documento y contrasena de Sofia Plus. Se guardaran en "
                "el archivo .env del proyecto para reutilizarlas en las proximas "
                "ejecuciones.\n\nVuelve a ejecutarlo si Sofia Plus te pide cambiar "
                "la contrasena.",
            )

        main()
    except Exception as exc:
        traceback.print_exc()
        messagebox.showerror(
            "SOFIABOT - Error",
            f"No fue posible completar la descarga.\n\n{exc}\n\n"
            f"Revisa el log: {PROJECT_ROOT / 'logs' / 'sofiabot_app.log'}",
        )
    finally:
        if log_handle is not None:
            try:
                log_handle.flush()
                log_handle.close()
            except Exception:
                pass


if __name__ == "__main__":
    run_app()
