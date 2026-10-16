"""Suite de pruebas unitarias de la FSM de limpieza de inasistencias (unittest)."""

import unittest

from fsm_inasistencias_cleaner import EstadoFSM, LimpiadorInasistenciasFSM


def _limpiador():
    return LimpiadorInasistenciasFSM("Inasistencias.xls", "Inasistencias_Limpio.xlsx")


# Fila dispersa real: campos en (2,5,7,9,13,14,15,18) -> fase d=2.
FILA_DISPERSA = [
    None, None, "3411438 - COORDINACION EN SISTEMAS INTEGRADOS DE GESTION",
    None, None, "JOSE DIMAS VELASCO HERRERA", None, "CC - 1151969122",
    None, "JUAN PABLO MORENO LASPRILLA", None, None, None,
    "2026-05-04 00:00:00", "2026-05-04 00:00:00", 3.0, None, None,
    "NO ASISTIO A LA FORMACION",
]

# Fila compacta real: campos en (0,3,4,6,8,10,11,12) -> fase d=0.
FILA_COMPACTA = [
    "2990494 - GESTION DE PROYECTOS", None, None,
    "GLORIA PATRICIA MUNOZ MONTOYA", "CC - 1111670073", None,
    "ANGEL HANNS QUINTERO MURILLO", None, "2026-02-17 00:00:00",
    None, "2026-02-17 00:00:00", "4", "SIN JUSTIFICACION",
]


class TestFSMInasistencias(unittest.TestCase):
    def setUp(self):
        self.fsm = _limpiador()

    def test_01_fila_normal_alineada(self):
        """Fila densa con delta_i = 0 se emite alineada."""
        fila = ["1001", "Perez, Juan", "2026-10-01", "Justificada"]
        self.assertEqual(self.fsm.calcular_desfase_optimo(list(fila)), 0)
        resultado = self.fsm.procesar_siguiente(list(fila))
        self.assertEqual(self.fsm.estado_actual, EstadoFSM.EMIT_RECORD)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["Identificacion Aprendiz"], "1001")
        self.assertEqual(resultado["Apellidos"], "Perez")
        self.assertEqual(resultado["Nombres"], "Juan")

    def test_02_fila_desplazada_shift_1(self):
        """Fila densa con delta_i = 1 se realinea dinamicamente (tau_delta)."""
        fila = ["", "1002", "Gomez, Maria", "2026-10-02", "Injustificada"]
        self.assertEqual(self.fsm.calcular_desfase_optimo(list(fila)), 1)
        resultado = self.fsm.procesar_siguiente(list(fila))
        self.assertEqual(self.fsm.estado_actual, EstadoFSM.EMIT_RECORD)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["Identificacion Aprendiz"], "1002")
        self.assertEqual(resultado["Apellidos"], "Gomez")
        self.assertEqual(resultado["Nombres"], "Maria")

    def test_03_descarte_de_encabezados_y_ruido(self):
        """Titulos, encabezados y filas vacias -> IGNORE_NOISE."""
        casos_ruido = [
            [None, "Consolidado de Inasistencias - Aprendices por Ficha"],
            ["FICHA", None, None, "INSTRUCTOR",
             "IDENTIFICACION APRENDIZ", None, "APRENDIZ", None,
             "FECHA INICIO", None, "FECHA FIN", "CANT. HORAS",
             "JUSTIFICACION"],
            ["REPORTE DE INASISTENCIAS", "", "", ""],
            ["", "", None, ""],
            ["Pagina 1 de 5", "", "", ""],
        ]
        for fila in casos_ruido:
            with self.subTest(fila=fila):
                resultado = self.fsm.procesar_siguiente(list(fila))
                self.assertEqual(self.fsm.estado_actual, EstadoFSM.IGNORE_NOISE)
                self.assertIsNone(resultado)
        self.assertEqual(len(self.fsm.registros_procesados), 0)

    def test_04_fision_nombres_compuestos(self):
        """Operador alpha: 'Apellidos, Nombres' se divide por ','."""
        apellidos, nombres = self.fsm.separar_apellidos_nombres(
            "Rodriguez Silva, Ana Sofia"
        )
        self.assertEqual(apellidos, "Rodriguez Silva")
        self.assertEqual(nombres, "Ana Sofia")
        # Sin delimitador (caso del reporte real): todo a apellidos.
        apellidos, nombres = self.fsm.separar_apellidos_nombres(
            "JUAN PABLO MORENO LASPRILLA"
        )
        self.assertEqual(apellidos, "JUAN PABLO MORENO LASPRILLA")
        self.assertEqual(nombres, "")

    def test_05_recuperacion_de_errores(self):
        """Basura irrecuperable -> ERROR_RECOVERY sin detener el proceso."""
        resultado = self.fsm.procesar_siguiente(
            ["TextoInvalido", "SinNumeros", "###"]
        )
        self.assertEqual(self.fsm.estado_actual, EstadoFSM.ERROR_RECOVERY)
        self.assertIsNone(resultado)
        self.assertEqual(len(self.fsm.log_errores), 1)
        # La FSM sigue operativa tras el error (aislamiento de errores).
        resultado_ok = self.fsm.procesar_siguiente(list(FILA_COMPACTA))
        self.assertEqual(self.fsm.estado_actual, EstadoFSM.EMIT_RECORD)
        self.assertIsNotNone(resultado_ok)

    def test_06_fila_dispersa_real(self):
        """Plantilla dispersa del reporte real: fase d=2 y extraccion total."""
        self.assertEqual(self.fsm.calcular_desfase_optimo(list(FILA_DISPERSA)), 2)
        resultado = self.fsm.procesar_siguiente(list(FILA_DISPERSA))
        self.assertEqual(self.fsm.estado_actual, EstadoFSM.EMIT_RECORD)
        self.assertEqual(resultado["Ficha"], "3411438")
        self.assertIn("COORDINACION", resultado["Programa"])
        self.assertEqual(resultado["Instructor"], "JOSE DIMAS VELASCO HERRERA")
        self.assertEqual(resultado["Identificacion Aprendiz"], "CC - 1151969122")
        self.assertEqual(resultado["Apellidos"], "JUAN PABLO MORENO LASPRILLA")
        self.assertEqual(resultado["Cant.horas"], 3.0)
        self.assertEqual(resultado["Justificacion"], "NO ASISTIO A LA FORMACION")

    def test_07_fila_compacta_real(self):
        """Plantilla compacta del reporte real: fase d=0 y fechas como texto."""
        self.assertEqual(self.fsm.calcular_desfase_optimo(list(FILA_COMPACTA)), 0)
        resultado = self.fsm.procesar_siguiente(list(FILA_COMPACTA))
        self.assertEqual(self.fsm.estado_actual, EstadoFSM.EMIT_RECORD)
        self.assertEqual(resultado["Ficha"], "2990494")
        self.assertEqual(
            resultado["Identificacion Aprendiz"], "CC - 1111670073"
        )
        self.assertEqual(resultado["Apellidos"], "ANGEL HANNS QUINTERO MURILLO")
        self.assertEqual(resultado["Cant.horas"], 4.0)
        self.assertIsNotNone(resultado["Fecha Inicio"])
        self.assertIsNotNone(resultado["Fecha Fin"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
