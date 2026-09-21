"""Transforma el reporte de metas conforme a un libro modelo de referencia."""

from pathlib import Path
import re
from typing import Dict, Iterable

import pandas as pd

from exporters.excel_exporter import ExcelExporter
from models.domain import TransformationResult


class ReferenceModelTransformer:
    """Genera exactamente las tablas presentes en el modelo de referencia."""

    _AGGREGATION_PATTERN = re.compile(r"(?:^|\b)total(?:es)?\b|=\s*\(", re.IGNORECASE)

    def run(self, source: Path, reference: Path, output_folder: Path, filename: str) -> TransformationResult:
        """Elimina filas agregadas y construye el esquema del libro de referencia.

        Args:
            source: Libro de metas en formato de reporte humano.
            reference: Libro que define nombres de hojas, columnas y dimensiones base.
            output_folder: Carpeta destino.
            filename: Nombre del archivo Excel de salida.

        Returns:
            Modelo dimensional y archivo exportado.
        """
        reference_tables = pd.read_excel(reference, sheet_name=None)
        required = {"DimCentro", "DimPeriodo", "DimCategoria", "DimIndicador", "FactMetas"}
        missing = required - set(reference_tables)
        if missing:
            raise ValueError(f"El modelo de referencia no contiene: {', '.join(sorted(missing))}.")
        dimensions = {name: reference_tables[name].copy() for name in required if name != "FactMetas"}
        records, removed = self._extract_atomic_records(source, dimensions["DimCategoria"])
        dimensions["DimIndicador"] = pd.DataFrame({
            "IdIndicador": range(1, len(records) + 1),
            "Indicador": records["Indicador"].tolist(),
        })
        fact = self._build_fact(records, dimensions, reference_tables["FactMetas"].columns.tolist())
        self._assert_foreign_keys(fact, dimensions)
        log = pd.DataFrame({"IndicadorEliminado": removed})
        validation = pd.DataFrame([
            {"Control": "Registros atómicos", "Valor": len(fact), "Estado": "OK"},
            {"Control": "Filas de suma eliminadas", "Valor": len(removed), "Estado": "OK"},
            {"Control": "Claves foráneas", "Valor": "Válidas", "Estado": "OK"},
        ])
        dictionary = self._dictionary(fact, dimensions)
        output_folder.mkdir(parents=True, exist_ok=True)
        output = self._export_exact_schema(output_folder / filename, fact, dimensions)
        return TransformationResult(fact, dimensions, dictionary, log, validation, output)

    def _extract_atomic_records(self, source: Path, categories: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Lee la hoja de reporte, ignorando encabezados y sumas visibles."""
        raw = pd.read_excel(source, sheet_name=0, header=None, dtype=object)
        records: list[dict[str, object]] = []
        removed: list[str] = []
        section = ""
        for _, row in raw.iterrows():
            values = [self._clean(value) for value in row.tolist()]
            label = next((value for value in values if isinstance(value, str) and value), None)
            if label is None:
                continue
            numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
            texts = [value for value in values if isinstance(value, str) and value]
            if any(text.lower() == "meta" for text in texts) and any("ejecuci" in text.lower() for text in texts):
                section = label
                continue
            if len(values) < 5 or not numeric and not any("%" in text or text == "-" for text in texts):
                continue
            if self._AGGREGATION_PATTERN.search(label):
                removed.append(label)
                continue
            # En el reporte los cuatro últimos campos usados son indicador, meta, ejecución y porcentaje.
            non_empty = [value for value in values if value is not None and value != ""]
            if len(non_empty) < 2:
                continue
            indicator = str(non_empty[0])
            measures = non_empty[1:4]
            records.append({
                "Indicador": indicator,
                "IdCategoria": self._category_id(section, indicator, categories),
                "Meta": self._number(measures[0]) if len(measures) > 0 else None,
                "Ejecucion": self._number(measures[1]) if len(measures) > 1 else None,
                "Porcentaje": self._number(measures[2]) if len(measures) > 2 else None,
            })
        return pd.DataFrame(records), removed

    @staticmethod
    def _clean(value: object) -> object:
        """Normaliza espacios sin alterar tipos numéricos."""
        if pd.isna(value):
            return None
        return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else value

    @staticmethod
    def _number(value: object) -> float | int | None:
        """Convierte guiones en nulo y porcentajes a valores numéricos."""
        if value is None or pd.isna(value) or value == "-":
            return None
        if isinstance(value, str) and value.endswith("%"):
            return float(value[:-1].replace(",", ".")) / 100
        return float(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _category_id(section: str, indicator: str, categories: pd.DataFrame) -> int:
        """Clasifica un indicador usando las categorías disponibles en el referente."""
        values = {str(row.Categoria).lower(): int(row.IdCategoria) for row in categories.itertuples()}
        text = f"{section} {indicator}".lower()
        rules = [
            ("certificación de competencias", "certificación de competencias laborales"),
            ("desagregación", "desagregación otras poblaciones vulnerables"),
            ("poblaciones vulnerables", "poblaciones vulnerables"),
            ("emprendimiento", "emprendimiento y fortalecimiento"),
            ("contratos", "contratos de aprendizaje"),
            ("articulación", "articulación con la media"),
            ("campesena", "campesena"),
            (" fic", "fic"),
            ("full popular", "full popular"),
        ]
        for needle, category in rules:
            if needle in text and category in values:
                return values[category]
        return values["formación regular"]

    @staticmethod
    def _build_fact(records: pd.DataFrame, dimensions: Dict[str, pd.DataFrame], columns: list[str]) -> pd.DataFrame:
        """Crea hechos con las mismas columnas y orden del archivo modelo."""
        fact = records.copy()
        fact.insert(0, "IdIndicador", range(1, len(fact) + 1))
        fact.insert(0, "IdPeriodo", int(dimensions["DimPeriodo"].iloc[0]["IdPeriodo"]))
        fact.insert(0, "IdCentro", int(dimensions["DimCentro"].iloc[0]["IdCentro"]))
        return fact.reindex(columns=columns)

    @staticmethod
    def _assert_foreign_keys(fact: pd.DataFrame, dimensions: Dict[str, pd.DataFrame]) -> None:
        """Garantiza integridad referencial antes de exportar."""
        checks: Iterable[tuple[str, str]] = (("IdCentro", "DimCentro"), ("IdPeriodo", "DimPeriodo"),
                                               ("IdCategoria", "DimCategoria"), ("IdIndicador", "DimIndicador"))
        for key, dimension in checks:
            if not fact[key].isin(dimensions[dimension][key]).all():
                raise ValueError(f"La clave {key} contiene valores fuera de {dimension}.")

    @staticmethod
    def _dictionary(fact: pd.DataFrame, dimensions: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Genera metadatos internos sin agregarlos al libro contractual."""
        return pd.DataFrame([
            {"Tabla": name, "Campo": column, "Tipo": str(data[column].dtype)}
            for name, data in {"FactMetas": fact, **dimensions}.items() for column in data.columns
        ])

    @staticmethod
    def _export_exact_schema(path: Path, fact: pd.DataFrame, dimensions: Dict[str, pd.DataFrame]) -> Path:
        """Escribe sólo las cinco hojas establecidas por el contrato de referencia."""
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for name in ("DimCentro", "DimPeriodo", "DimCategoria", "DimIndicador"):
                dimensions[name].to_excel(writer, sheet_name=name, index=False)
            fact.to_excel(writer, sheet_name="FactMetas", index=False)
            for worksheet in writer.book.worksheets:
                worksheet.freeze_panes = "A2"
                worksheet.auto_filter.ref = worksheet.dimensions
                for column in worksheet.columns:
                    worksheet.column_dimensions[column[0].column_letter].width = min(
                        max(len(str(cell.value or "")) for cell in column) + 2, 72
                    )
        return path
