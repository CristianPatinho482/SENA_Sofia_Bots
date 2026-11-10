from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def detect_data_root(executable_dir: Path) -> Path:
    """Elige donde viven .env y logs cuando el bot corre como ejecutable.

    Si el .exe esta dentro de la carpeta ``dist`` del proyecto, se usa la raiz
    del proyecto para no duplicar credenciales ni logs. Si el .exe se copia a
    otra ubicacion, se usa su propia carpeta para mantenerlo portable.
    """
    candidate = executable_dir.parent
    if (candidate / "bots").is_dir() and (candidate / "sofia_bots").is_dir():
        return candidate
    return executable_dir


if getattr(sys, "frozen", False):
    EXE_DIR = Path(sys.executable).resolve().parent
    PROJECT_ROOT = detect_data_root(EXE_DIR)
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", EXE_DIR))
else:
    EXE_DIR = Path(__file__).resolve().parents[1]
    PROJECT_ROOT = EXE_DIR
    RESOURCE_ROOT = PROJECT_ROOT

DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
SOFIA_URL = "http://senasofiaplus.edu.co/sofia-public/"
DEFAULT_ROLE_LABEL = "Gestion Desarrollo Curricular"
DEFAULT_ROLE_VALUE = "17"
DEFAULT_INASISTENCIAS_FOLDER = "Inasistencias"


def desktop_dir() -> Path:
    """Devuelve el Escritorio real del usuario, incluso si OneDrive lo redirige.

    En Windows la ubicacion puede estar redirigida a OneDrive. Se consulta el
    registro para respetar esa configuracion; si no es posible, se usa
    ``~/Desktop``.
    """
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "Desktop")
            expanded = os.path.expandvars(value)
            if expanded:
                return Path(expanded)
        except Exception:
            pass
    return Path.home() / "Desktop"


def default_inasistencias_dir() -> Path:
    """Carpeta operativa donde el bot deja el reporte limpio para Power BI."""
    return desktop_dir() / DEFAULT_INASISTENCIAS_FOLDER


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
