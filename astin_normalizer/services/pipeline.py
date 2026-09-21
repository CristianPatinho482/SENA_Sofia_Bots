"""Caso de uso principal de normalización."""

from pathlib import Path
from typing import List

import pandas as pd

from analyzers.business_model_inferencer import BusinessModelInferencer
from config import NormalizerConfig
from exporters.excel_exporter import ExcelExporter
from models.domain import TransformationResult
from parsers.atomic_record_detector import AtomicRecordDetector, SubtotalDetector
from parsers.hierarchy_parser import HierarchyParser
from parsers.structure_analyzer import StructureAnalyzer
from services.excel_reader import ExcelReader
from services.model_builder import DimensionBuilder, FactTableBuilder
from services.normalizer import Normalizer
from services.reference_model_transformer import ReferenceModelTransformer
from validators.validator import Validator


class NormalizationPipeline:
    """Coordina componentes independientes para procesar todas las hojas."""

    def __init__(self, config: NormalizerConfig | None = None, rules_path: Path | None = None) -> None:
        self.config = config or NormalizerConfig.from_json(rules_path or Path(__file__).parents[1] / "rules.json")
        self.reader = ExcelReader()
        self.analyzer = StructureAnalyzer(self.config)
        self.hierarchy = HierarchyParser(self.config)
        self.detector = AtomicRecordDetector(self.config)

    def run(self, source: Path, output_folder: Path, reference: Path | None = None) -> TransformationResult:
        """Procesa un libro Excel y devuelve sus artefactos de salida."""
        if reference is not None:
            return ReferenceModelTransformer().run(source, reference, output_folder, self.config.output_filename)
        formula_cells = self.reader.formula_cells(source)
        atomic_frames: List[pd.DataFrame] = []
        logs: List[pd.DataFrame] = []
        reported_totals: List[float] = []
        for sheet, raw in self.reader.read_all_sheets(source).items():
            analysis = self.analyzer.analyze(sheet, raw)
            enriched = self.hierarchy.enrich(analysis.rows)
            subtotal_detector = SubtotalDetector(self.config)
            reported_totals.extend(
                total for _, row in enriched.iterrows()
                if (total := subtotal_detector.reported_total(row)) is not None
            )
            # `analysis.rows` conserva el índice original de la hoja cruda.
            formula_rows = {row for row, _ in formula_cells.get(sheet, set()) if row > analysis.header_row}
            atomic, log = self.detector.detect(enriched, formula_rows)
            atomic_frames.append(atomic)
            log.insert(0, "Hoja", sheet)
            logs.append(log)
        records = pd.concat(atomic_frames, ignore_index=True) if atomic_frames else pd.DataFrame()
        normalized = Normalizer(self.config).normalize(records)
        dimensions = DimensionBuilder(self.config).build(normalized)
        fact = FactTableBuilder().build(normalized, dimensions)
        log = pd.concat(logs, ignore_index=True) if logs else pd.DataFrame(columns=["Hoja", "FilaOrigen", "Accion", "Motivo"])
        # El mayor total explícito suele corresponder al total general; se conserva además el log para auditoría.
        original_total = max(reported_totals) if reported_totals else None
        validation = Validator().validate(fact, log, original_total)
        reference_model = BusinessModelInferencer().infer(reference)
        generated = {"FactMetas": fact, **dimensions}
        validation = pd.concat([validation, BusinessModelInferencer.compare(reference_model, generated)], ignore_index=True)
        dictionary = self._dictionary(fact, dimensions)
        output_folder.mkdir(parents=True, exist_ok=True)
        output = ExcelExporter().export(output_folder / self.config.output_filename, fact, dimensions, dictionary, log, validation)
        return TransformationResult(fact, dimensions, dictionary, log, validation, output)

    @staticmethod
    def _dictionary(fact: pd.DataFrame, dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows = []
        for table, data in {"FactMetas": fact, **dimensions}.items():
            for column in data.columns:
                rows.append({"Tabla": table, "Campo": column, "TipoDatos": str(data[column].dtype), "Descripcion": "Clave" if column.startswith("Id") else "Atributo o medida"})
        return pd.DataFrame(rows)
