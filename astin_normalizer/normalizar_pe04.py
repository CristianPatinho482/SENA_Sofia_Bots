"""Comando de línea para normalizar un reporte PE-04."""

import argparse
from pathlib import Path

from pe04.normalizer import Pe04Normalizer


def main() -> None:
    """Procesa PE-04 y enlaza sus dimensiones compartidas con ASTIN."""
    parser = argparse.ArgumentParser(description="Normaliza un reporte PE-04 para Power BI.")
    parser.add_argument("pe04", type=Path, help="Ruta del archivo PE-04 de origen.")
    parser.add_argument("astin_model", type=Path, help="Ruta de ASTIN_Modelo_Estrella.xlsx.")
    parser.add_argument("output_folder", type=Path, help="Carpeta donde se guardará el resultado.")
    args = parser.parse_args()
    output = args.output_folder / "PE04_Modelo_Estrella.xlsx"
    result = Pe04Normalizer().run(args.pe04, args.astin_model, output)
    print(f"Archivo creado: {result}")


if __name__ == "__main__":
    main()
