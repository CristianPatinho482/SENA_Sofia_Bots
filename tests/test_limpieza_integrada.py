"""Pruebas de integracion del limpiador FSM con el flujo de descarga.

Cubre el caso real del reporte de Sofia Plus: contenido XLSX guardado con
extension .xls, limpieza sobrescribiendo el mismo archivo y preservacion del
original cuando la limpieza falla.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from sofia_bots.inasistencias_cleaner import (
    COLUMNAS_SALIDA,
    LimpiadorInasistenciasFSM,
    limpiar_inasistencias,
)

FILA_COMPACTA = [
    "2990494 - GESTION DE PROYECTOS", None, None,
    "GLORIA PATRICIA MUNOZ MONTOYA", "CC - 1111670073", None,
    "ANGEL HANNS QUINTERO MURILLO", None, "2026-02-17 00:00:00",
    None, "2026-02-17 00:00:00", "4", "SIN JUSTIFICACION",
]

FILA_DISPERSA = [
    None, None, "3411438 - COORDINACION EN SISTEMAS INTEGRADOS DE GESTION",
    None, None, "JOSE DIMAS VELASCO HERRERA", None, "CC - 1151969122",
    None, "JUAN PABLO MORENO LASPRILLA", None, None, None,
    "2026-05-04 00:00:00", "2026-05-04 00:00:00", 3.0, None, None,
    "NO ASISTIO A LA FORMACION",
]


def _crear_reporte_crudo(ruta: Path) -> None:
    """Crea un XLSX con el formato crudo del reporte y lo guarda como .xls."""
    wb = Workbook()
    ws = wb.active
    ws.append(["Consolidado de Inasistencias - Aprendices por Ficha"])
    ws.append([
        "FICHA", None, None, "INSTRUCTOR", "IDENTIFICACION APRENDIZ",
        None, "APRENDIZ", None, "FECHA INICIO", None, "FECHA FIN",
        "CANT. HORAS", "JUSTIFICACION",
    ])
    ws.append(FILA_COMPACTA)
    ws.append(FILA_DISPERSA)
    tmp_xlsx = ruta.with_suffix(".xlsx")
    wb.save(tmp_xlsx)
    os.replace(tmp_xlsx, ruta)


class TestIntegracionLimpieza(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_01_sobrescribe_xls_con_contenido_xlsx(self) -> None:
        reporte = self.base / "Inasistencias.xls"
        _crear_reporte_crudo(reporte)

        resultado = limpiar_inasistencias(reporte)

        self.assertEqual(resultado, reporte)
        self.assertTrue(reporte.read_bytes().startswith(b"PK\x03\x04"))
        df = pd.read_excel(reporte, engine="openpyxl")
        self.assertEqual(list(df.columns), COLUMNAS_SALIDA)
        self.assertEqual(len(df), 2)
        self.assertEqual(str(df.iloc[0]["Ficha"]), "2990494")
        self.assertEqual(float(df.iloc[0]["Cant.horas"]), 4.0)
        self.assertEqual(str(df.iloc[1]["Ficha"]), "3411438")
        self.assertEqual(
            df.iloc[1]["Identificacion Aprendiz"], "CC - 1151969122"
        )

    def test_02_salida_en_archivo_separado(self) -> None:
        reporte = self.base / "Inasistencias.xls"
        limpio = self.base / "Inasistencias_Limpio.xlsx"
        _crear_reporte_crudo(reporte)

        limpiar_inasistencias(reporte, limpio)

        self.assertTrue(limpio.exists())
        self.assertEqual(len(pd.read_excel(limpio, engine="openpyxl")), 2)

    def test_03_fallo_no_destruye_el_original(self) -> None:
        reporte = self.base / "Inasistencias.xls"
        contenido = b"contenido invalido que no es excel"
        reporte.write_bytes(contenido)
        limpiador = LimpiadorInasistenciasFSM(str(reporte), str(reporte))

        with self.assertRaises(RuntimeError):
            limpiador.ejecutar()

        self.assertEqual(reporte.read_bytes(), contenido)

    def test_04_segunda_limpieza_es_idempotente(self) -> None:
        reporte = self.base / "Inasistencias.xls"
        _crear_reporte_crudo(reporte)

        limpiar_inasistencias(reporte)
        primera = reporte.read_bytes()
        limpiar_inasistencias(reporte)

        self.assertEqual(reporte.read_bytes(), primera)
        self.assertEqual(len(pd.read_excel(reporte, engine="openpyxl")), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
