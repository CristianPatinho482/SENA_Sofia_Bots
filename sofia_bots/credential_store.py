"""Persistencia local de las credenciales de Sofia Plus.

Las credenciales se guardan en el archivo ``.env`` del proyecto (ignorado por
Git) para que el bot solo las solicite la primera vez o cuando Sofia Plus
obligue a cambiar la contrasena. La contrasena nunca se imprime en consola ni
se escribe en los logs.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .settings import DEFAULT_ENV_FILE, SofiaCredentials, load_env_file


def _quote_env_value(value: str) -> str:
    """Entrecomilla valores que puedan romper el formato CLAVE=VALOR."""
    value = value.replace("\r", " ").replace("\n", " ").strip()
    if not value:
        return '""'
    if any(char.isspace() for char in value) or any(
        char in value for char in "\"'#"
    ):
        return f'"{value}"'
    return value


def _read_env_lines(env_file: Path) -> list[str]:
    if not env_file.exists():
        return []
    return env_file.read_text(encoding="utf-8").splitlines()


def _set_env_value(lines: list[str], key: str, value: str) -> list[str]:
    """Reemplaza o agrega una clave conservando comentarios y otras claves."""
    new_line = f"{key}={_quote_env_value(value)}"
    result: list[str] = []
    replaced = False

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            existing_key = stripped.split("=", 1)[0].strip()
            if existing_key == key:
                if not replaced:
                    result.append(new_line)
                    replaced = True
                continue
        result.append(line)

    if not replaced:
        result.append(new_line)

    return result


def save_credentials(
    credentials: SofiaCredentials,
    env_file: str | Path = DEFAULT_ENV_FILE,
) -> Path:
    """Guarda usuario y contrasena en ``.env`` de forma atomica.

    Retorna la ruta del archivo actualizado. No registra la contrasena en
    ningun log.
    """
    path = Path(env_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = _read_env_lines(path)
    lines = _set_env_value(lines, "SOFIA_USUARIO", credentials.usuario)
    lines = _set_env_value(lines, "SOFIA_PASSWORD", credentials.password)

    contenido = "\n".join(lines) + "\n"
    fd, temporal = tempfile.mkstemp(
        prefix=".env.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(contenido)
        os.replace(temporal, path)
    except Exception:
        try:
            os.unlink(temporal)
        except OSError:
            pass
        raise

    # La sesion actual debe usar de inmediato las credenciales nuevas.
    os.environ["SOFIA_USUARIO"] = credentials.usuario
    os.environ["SOFIA_PASSWORD"] = credentials.password
    return path


VALORES_PLANTILLA = {"tu_documento", "tu_clave"}


def load_saved_credentials(
    env_file: str | Path = DEFAULT_ENV_FILE,
) -> SofiaCredentials | None:
    """Devuelve las credenciales guardadas o ``None`` si no existen."""
    load_env_file(env_file)
    usuario = os.getenv("SOFIA_USUARIO", "").strip()
    password = os.getenv("SOFIA_PASSWORD", "").strip()
    if (
        not usuario
        or not password
        or usuario.lower() in VALORES_PLANTILLA
        or password.lower() in VALORES_PLANTILLA
    ):
        return None
    return SofiaCredentials(usuario=usuario, password=password)
