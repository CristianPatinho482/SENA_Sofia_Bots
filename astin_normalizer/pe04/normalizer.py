"""Conversión del reporte PE-04 en un modelo estrella compatible con ASTIN."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict

import pandas as pd


@dataclass
class Pe04Model:
    """Tablas que componen el modelo dimensional PE-04."""

    dimensions: Dict[str, pd.DataFrame]
    fact: pd.DataFrame
    validation: pd.DataFrame


class Pe04Normalizer:
    """Normaliza fichas PE-04 con dimensiones de centro y período conformadas."""

    FACT_COLUMNS = [
        "IdCentro", "IdPeriodo", "IdFicha", "IdPrograma", "IdNivel", "IdJornada",
        "IdModalidad", "IdEmpresa", "IdUbicacion", "IdSector", "EstadoCurso",
        "TipoFormacion", "EtapaFicha", "NumeroCursos", "TotalAprendicesMasculinos",
        "TotalAprendicesFemeninos", "TotalAprendicesNoBinario", "TotalAprendices",
        "HorasPlanta", "HorasContratistas", "HorasContratistasExternos", "HorasMonitores",
        "HorasInstitucionEmpresa", "TotalHoras", "TotalAprendicesActivos", "DuracionPrograma",
    ]

    def build_model(self, source: Path, astin_model: Path) -> Pe04Model:
        """Construye tablas PE-04 sin modificar los libros de entrada.

        Args:
            source: Archivo PE-04 original.
            astin_model: ASTIN_Modelo_Estrella.xlsx que aporta DimCentro y DimPeriodo.
        """
        raw, period_id = self._read_source(source)
        shared = self._read_shared_dimensions(astin_model, period_id)
        data = self._filter_center(raw, shared["DimCentro"])
        dimensions: Dict[str, pd.DataFrame] = {
            "DimCentro": shared["DimCentro"],
            "DimPeriodo": shared["DimPeriodo"],
            "DimFicha": self._dimension(data, ["IDENTIFICADOR_FICHA", "IDENTIFICADOR_UNICO_FICHA"],
                                        ["IdentificadorFicha", "IdentificadorUnicoFicha"], "IdFicha"),
            "DimPrograma": self._dimension(data, ["CODIGO_PROGRAMA", "VERSION_PROGRAMA", "NOMBRE_PROGRAMA_FORMACION"],
                                           ["CodigoPrograma", "VersionPrograma", "NombrePrograma"], "IdPrograma"),
            "DimNivel": self._dimension(data, ["CODIGO_NIVEL_FORMACION", "NIVEL_FORMACION"],
                                        ["CodigoNivel", "NivelFormacion"], "IdNivel"),
            "DimJornada": self._dimension(data, ["CODIGO_JORNADA", "NOMBRE_JORNADA"],
                                          ["CodigoJornada", "NombreJornada"], "IdJornada"),
            "DimModalidad": self._dimension(data, ["MODALIDAD_FORMACION"], ["ModalidadFormacion"], "IdModalidad"),
            "DimEmpresa": self._dimension(data, ["NUMERO_IDENTIFICACION_EMPRESA", "TIPO_IDENTIFICACION_EMPRESA", "NOMBRE_EMPRESA"],
                                          ["NumeroIdentificacion", "TipoIdentificacion", "NombreEmpresa"], "IdEmpresa"),
            "DimUbicacion": self._dimension(data, ["CODIGO_DEPARTAMENTO_CURSO", "NOMBRE_DEPARTAMENTO_CURSO", "CODIGO_MUNICIPIO_CURSO", "NOMBRE_MUNICIPIO_CURSO"],
                                            ["CodigoDepartamento", "Departamento", "CodigoMunicipio", "Municipio"], "IdUbicacion"),
            "DimSector": self._dimension(data, ["CODIGO_SECTOR_PROGRAMA", "NOMBRE_SECTOR_PROGRAMA", "NOMBRE_NUEVO_SECTOR"],
                                         ["CodigoSector", "NombreSector", "NuevoSector"], "IdSector"),
        }
        fact = self._build_fact(data, dimensions, period_id)
        validation = self._validate(fact, dimensions)
        return Pe04Model(dimensions, fact, validation)

    def export(self, model: Pe04Model, destination: Path) -> Path:
        """Exporta el modelo a un libro Power BI listo sin tocar los orígenes."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(destination, engine="openpyxl") as writer:
            for name, dimension in model.dimensions.items():
                dimension.to_excel(writer, sheet_name=name, index=False)
            model.fact.to_excel(writer, sheet_name="FactPE04", index=False)
            model.validation.to_excel(writer, sheet_name="Validacion", index=False)
            for sheet in writer.book.worksheets:
                sheet.freeze_panes = "A2"
                sheet.auto_filter.ref = sheet.dimensions
                for column in sheet.columns:
                    sheet.column_dimensions[column[0].column_letter].width = min(
                        max(len(str(cell.value or "")) for cell in column) + 2, 42
                    )
        return destination

    def run(self, source: Path, astin_model: Path, destination: Path) -> Path:
        """Construye y exporta el modelo PE-04."""
        return self.export(self.build_model(source, astin_model), destination)

    @staticmethod
    def _read_source(source: Path) -> tuple[pd.DataFrame, int]:
        raw = pd.read_excel(source, sheet_name=0, header=None, dtype=object)
        header_index = next(
            (index for index, row in raw.iterrows() if "CODIGO_REGIONAL" in set(row.dropna().astype(str))), None
        )
        if header_index is None:
            raise ValueError("No se encontró la cabecera CODIGO_REGIONAL en el archivo PE-04.")
        period_candidates = [
            int(str(value).strip()) for value in raw.iloc[:header_index].stack()
            if re.fullmatch(r"20\d{4}", str(value).strip())
        ]
        if not period_candidates:
            raise ValueError("No se encontró un período AAAAMM en el encabezado PE-04.")
        data = raw.iloc[header_index + 1:].copy()
        data.columns = raw.iloc[header_index].astype(str).str.strip()
        return data.dropna(how="all").reset_index(drop=True), period_candidates[0]

    @staticmethod
    def _read_shared_dimensions(astin_model: Path, period_id: int) -> Dict[str, pd.DataFrame]:
        tables = pd.read_excel(astin_model, sheet_name=["DimCentro", "DimPeriodo"])
        period = tables["DimPeriodo"].query("IdPeriodo == @period_id")
        if period.empty:
            raise ValueError(f"El modelo ASTIN no contiene el período {period_id}.")
        return {"DimCentro": tables["DimCentro"], "DimPeriodo": period.reset_index(drop=True)}

    @staticmethod
    def _filter_center(data: pd.DataFrame, centers: pd.DataFrame) -> pd.DataFrame:
        codes = set(pd.to_numeric(centers["CodigoCentro"], errors="coerce").dropna().astype(int))
        result = data[pd.to_numeric(data["CODIGO_CENTRO"], errors="coerce").isin(codes)].copy()
        if result.empty:
            raise ValueError("PE-04 no tiene registros del centro definido en DimCentro.")
        return result.reset_index(drop=True)

    @staticmethod
    def _dimension(data: pd.DataFrame, source: list[str], target: list[str], identifier: str) -> pd.DataFrame:
        frame = data[source].copy().fillna("Sin información")
        frame.columns = target
        frame = frame.drop_duplicates().sort_values(target).reset_index(drop=True)
        frame.insert(0, identifier, range(1, len(frame) + 1))
        return frame

    def _build_fact(self, data: pd.DataFrame, dimensions: Dict[str, pd.DataFrame], period_id: int) -> pd.DataFrame:
        fact = pd.DataFrame(index=data.index)
        fact["IdCentro"] = self._map_center(data, dimensions["DimCentro"])
        fact["IdPeriodo"] = period_id
        mappings = {
            "IdFicha": ("DimFicha", ["IDENTIFICADOR_FICHA", "IDENTIFICADOR_UNICO_FICHA"], ["IdentificadorFicha", "IdentificadorUnicoFicha"]),
            "IdPrograma": ("DimPrograma", ["CODIGO_PROGRAMA", "VERSION_PROGRAMA", "NOMBRE_PROGRAMA_FORMACION"], ["CodigoPrograma", "VersionPrograma", "NombrePrograma"]),
            "IdNivel": ("DimNivel", ["CODIGO_NIVEL_FORMACION", "NIVEL_FORMACION"], ["CodigoNivel", "NivelFormacion"]),
            "IdJornada": ("DimJornada", ["CODIGO_JORNADA", "NOMBRE_JORNADA"], ["CodigoJornada", "NombreJornada"]),
            "IdModalidad": ("DimModalidad", ["MODALIDAD_FORMACION"], ["ModalidadFormacion"]),
            "IdEmpresa": ("DimEmpresa", ["NUMERO_IDENTIFICACION_EMPRESA", "TIPO_IDENTIFICACION_EMPRESA", "NOMBRE_EMPRESA"], ["NumeroIdentificacion", "TipoIdentificacion", "NombreEmpresa"]),
            "IdUbicacion": ("DimUbicacion", ["CODIGO_DEPARTAMENTO_CURSO", "NOMBRE_DEPARTAMENTO_CURSO", "CODIGO_MUNICIPIO_CURSO", "NOMBRE_MUNICIPIO_CURSO"], ["CodigoDepartamento", "Departamento", "CodigoMunicipio", "Municipio"]),
            "IdSector": ("DimSector", ["CODIGO_SECTOR_PROGRAMA", "NOMBRE_SECTOR_PROGRAMA", "NOMBRE_NUEVO_SECTOR"], ["CodigoSector", "NombreSector", "NuevoSector"]),
        }
        for key, (name, source, target) in mappings.items():
            fact[key] = self._map_dimension(data, dimensions[name], source, target)
        fact["EstadoCurso"] = data["ESTADO_CURSO"]
        fact["TipoFormacion"] = data["TIPO_DE_FORMACION"]
        fact["EtapaFicha"] = data["ETAPA_FICHA"]
        measures = {
            "NumeroCursos": "NUMERO_CURSOS", "TotalAprendicesMasculinos": "TOTAL_APRENDICES_MASCULINOS",
            "TotalAprendicesFemeninos": "TOTAL_APRENDICES_FEMININOS", "TotalAprendicesNoBinario": "TOTAL_APRENDICES_NOBINARIO",
            "TotalAprendices": "TOTAL_APRENDICES", "HorasPlanta": "HORAS_PLANTA",
            "HorasContratistas": "HORAS_CONTRATISTAS", "HorasContratistasExternos": "HORAS_CONTRATISTAS_EXTERNOS",
            "HorasMonitores": "HORAS_MONITORES", "HorasInstitucionEmpresa": "HORAS_INST_EMPRESA",
            "TotalHoras": "TOTAL_HORAS", "TotalAprendicesActivos": "TOTAL_APRENDICES_ACTIVOS",
            "DuracionPrograma": "DURACION_PROGRAMA",
        }
        for target, source in measures.items():
            fact[target] = pd.to_numeric(data[source], errors="coerce")
        return fact.reindex(columns=self.FACT_COLUMNS)

    @staticmethod
    def _map_center(data: pd.DataFrame, centers: pd.DataFrame) -> pd.Series:
        lookup = centers.set_index("CodigoCentro")["IdCentro"]
        return pd.to_numeric(data["CODIGO_CENTRO"], errors="coerce").map(lookup)

    @staticmethod
    def _map_dimension(data: pd.DataFrame, dimension: pd.DataFrame, source: list[str], target: list[str]) -> pd.Series:
        left = data[source].copy().fillna("Sin información")
        left.columns = target
        identifier = dimension.columns[0]
        return left.merge(dimension[[identifier, *target]], on=target, how="left", sort=False)[identifier]

    @staticmethod
    def _validate(fact: pd.DataFrame, dimensions: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        foreign_keys = [column for column in fact.columns if column.startswith("Id")]
        nulls = int(fact[foreign_keys].isna().sum().sum())
        return pd.DataFrame([
            {"Control": "Registros FactPE04", "Valor": len(fact), "Estado": "OK"},
            {"Control": "Claves foráneas nulas", "Valor": nulls, "Estado": "REVISAR" if nulls else "OK"},
            {"Control": "Total aprendices", "Valor": float(fact["TotalAprendices"].sum()), "Estado": "OK"},
            {"Control": "Total horas", "Valor": float(fact["TotalHoras"].sum()), "Estado": "OK"},
        ])
