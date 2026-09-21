from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class ProcessingRecord:
    key: str
    status: str
    details: str = ""


class ExcelControlLog:
    def __init__(self, path: str | Path, key_column: str = "CLAVE") -> None:
        self.path = Path(path)
        self.key_column = key_column
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=[self.key_column, "ESTADO", "DETALLE", "FECHA"])
        try:
            return pd.read_excel(self.path)
        except Exception:
            return pd.DataFrame(columns=[self.key_column, "ESTADO", "DETALLE", "FECHA"])

    def processed_keys(self, statuses: Iterable[str] = ("OK",)) -> set[str]:
        df = self._read()
        if self.key_column not in df.columns:
            return set()
        if "ESTADO" in df.columns:
            df = df[df["ESTADO"].astype(str).str.upper().isin({s.upper() for s in statuses})]
        return set(df[self.key_column].astype(str).str.strip())

    def has_success(self, key: str) -> bool:
        return str(key).strip() in self.processed_keys()

    def append(self, record: ProcessingRecord) -> None:
        df = self._read()
        row = pd.DataFrame(
            [
                {
                    self.key_column: record.key,
                    "ESTADO": record.status.upper(),
                    "DETALLE": record.details,
                    "FECHA": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            ]
        )
        pd.concat([df, row], ignore_index=True).to_excel(self.path, index=False)

    def success(self, key: str, details: str = "") -> None:
        self.append(ProcessingRecord(key=key, status="OK", details=details))

    def error(self, key: str, error: Exception | str) -> None:
        self.append(ProcessingRecord(key=key, status="ERROR", details=str(error)))

