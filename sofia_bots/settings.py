from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    RESOURCE_ROOT = PROJECT_ROOT

DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
SOFIA_URL = "http://senasofiaplus.edu.co/sofia-public/"
DEFAULT_ROLE_LABEL = "Gestion Desarrollo Curricular"
DEFAULT_ROLE_VALUE = "17"


def load_env_file(path: str | Path = DEFAULT_ENV_FILE) -> None:
    """Carga pares CLAVE=VALOR desde .env sin requerir librerias externas."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class SofiaCredentials:
    """Credenciales usadas por los bots de Sofia Plus."""

    usuario: str
    password: str

    @classmethod
    def from_env(cls, env_file: str | Path = DEFAULT_ENV_FILE) -> "SofiaCredentials":
        # Primero lee .env; si Windows ya tiene variables definidas, las respeta.
        load_env_file(env_file)
        usuario = os.getenv("SOFIA_USUARIO", "").strip()
        password = os.getenv("SOFIA_PASSWORD", "").strip()
        if not usuario or not password:
            raise RuntimeError(
                "Faltan credenciales. Define SOFIA_USUARIO y SOFIA_PASSWORD "
                "como variables de entorno o en el archivo .env del proyecto."
            )
        return cls(usuario=usuario, password=password)


@dataclass(frozen=True)
class BrowserSettings:
    """Parametros generales del navegador controlado por Playwright."""

    headless: bool = False
    slow_mo: int = 0
    navigation_timeout_ms: int = 120_000
    action_timeout_ms: int = 30_000
    download_timeout_ms: int = 120_000


@dataclass(frozen=True)
class SofiaSettings:
    """Configuracion completa que necesita una sesion de Sofia Plus."""

    credentials: SofiaCredentials
    browser: BrowserSettings = BrowserSettings()
    role_label: str = DEFAULT_ROLE_LABEL
    role_value: str = DEFAULT_ROLE_VALUE


def ensure_dir(path: str | Path) -> Path:
    """Garantiza que una carpeta exista y retorna su ruta como Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
