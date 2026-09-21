"""Escritura del modelo estrella en un libro independiente."""

from pathlib import Path
from typing import Dict

import pandas as pd


class ExcelExporter:
    """Exporta tablas sin tocar nunca el archivo fuente."""

    def export(self, destination: Path, fact: pd.DataFrame, dimensions: Dict[str, pd.DataFrame],
               dictionary: pd.DataFrame, log: pd.DataFrame, validation: pd.DataFrame) -> Path:
        """Guarda todas las hojas requeridas y aplica filtros sencillos."""
        with pd.ExcelWriter(destination, engine="openpyxl") as writer:
            fact.to_excel(writer, sheet_name="FactMetas", index=False)
            for name, dimension in dimensions.items():
                dimension.to_excel(writer, sheet_name=name[:31], index=False)
            dictionary.to_excel(writer, sheet_name="DiccionarioDatos", index=False)
            log.to_excel(writer, sheet_name="LogTransformacion", index=False)
            validation.to_excel(writer, sheet_name="Validacion", index=False)
            for worksheet in writer.book.worksheets:
                worksheet.freeze_panes = "A2"
                worksheet.auto_filter.ref = worksheet.dimensions
                for column in worksheet.columns:
                    letter = column[0].column_letter
                    worksheet.column_dimensions[letter].width = min(max(len(str(cell.value or "")) for cell in column) + 2, 40)
        return destination
