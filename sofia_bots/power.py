from __future__ import annotations

import ctypes
import platform
import time


def suspend_windows(delay_seconds: int = 30) -> None:
    """Espera unos segundos y solicita suspender Windows."""
    if platform.system() != "Windows":
        raise RuntimeError("La suspension automatica solo esta implementada para Windows.")

    if delay_seconds > 0:
        print(f"\nEl equipo se suspendera en {delay_seconds} segundos...")
        time.sleep(delay_seconds)

    result = ctypes.windll.PowrProf.SetSuspendState(False, False, False)
    if result == 0:
        raise RuntimeError("Windows rechazo la solicitud de suspension.")
