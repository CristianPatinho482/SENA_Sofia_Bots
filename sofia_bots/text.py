from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def safe_filename(value: str, replacement: str = "_") -> str:
    cleaned = strip_accents(str(value)).strip()
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", cleaned)
    cleaned = re.sub(r"\s+", replacement, cleaned)
    cleaned = re.sub(rf"{re.escape(replacement)}+", replacement, cleaned)
    return cleaned.strip(replacement)


def dated_filename(prefix: str, fecha_inicio: str, fecha_fin: str, suffix: str) -> str:
    extension = suffix if suffix.startswith(".") else f".{suffix}"
    return (
        f"{safe_filename(prefix)}_"
        f"{fecha_inicio.replace('/', '-')}_"
        f"{fecha_fin.replace('/', '-')}"
        f"{extension}"
    )


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

