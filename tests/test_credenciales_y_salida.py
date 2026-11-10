"""Pruebas de credenciales persistentes, carpeta de salida y errores fatales."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from unittest.mock import patch

from bots.descargar_inasistencias import (
    build_target_path,
    ensure_output_dir,
    resolve_credentials,
)
from sofia_bots.browser import BrowserLaunchError, RestartingRunner
from sofia_bots.credential_store import load_saved_credentials, save_credentials
from sofia_bots.settings import (
    DEFAULT_INASISTENCIAS_FOLDER,
    SofiaCredentials,
    default_inasistencias_dir,
    desktop_dir,
    detect_data_root,
)
from sofia_bots.sofia import SofiaLoginError


class TestCredencialesPersistentes(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.env_file = self.base / ".env"
        os.environ.pop("SOFIA_USUARIO", None)
        os.environ.pop("SOFIA_PASSWORD", None)

    def tearDown(self) -> None:
        os.environ.pop("SOFIA_USUARIO", None)
        os.environ.pop("SOFIA_PASSWORD", None)
        self._tmp.cleanup()

    def test_01_guarda_y_recupera_credenciales(self) -> None:
        """El .env se crea y las credenciales se leen de vuelta."""
        guardado = save_credentials(
            SofiaCredentials(usuario="123456", password="clave secreta"),
            self.env_file,
        )

        self.assertEqual(guardado, self.env_file)
        credenciales = load_saved_credentials(self.env_file)
        self.assertIsNotNone(credenciales)
        self.assertEqual(credenciales.usuario, "123456")
        self.assertEqual(credenciales.password, "clave secreta")

    def test_02_conserva_otras_claves_y_comentarios(self) -> None:
        """Actualizar credenciales no borra el resto de la configuracion."""
        self.env_file.write_text(
            "# comentario\nOTRA_CLAVE=valor\nSOFIA_USUARIO=viejo\n",
            encoding="utf-8",
        )

        save_credentials(
            SofiaCredentials(usuario="nuevo", password="nueva"),
            self.env_file,
        )

        contenido = self.env_file.read_text(encoding="utf-8")
        self.assertIn("# comentario", contenido)
        self.assertIn("OTRA_CLAVE=valor", contenido)
        self.assertIn("SOFIA_USUARIO=nuevo", contenido)
        self.assertIn("SOFIA_PASSWORD=nueva", contenido)
        self.assertNotIn("SOFIA_USUARIO=viejo", contenido)

    def test_03_sin_datos_devuelve_none(self) -> None:
        """Si no hay .env o esta incompleto, no inventa credenciales."""
        self.assertIsNone(load_saved_credentials(self.env_file))
        self.env_file.write_text("SOFIA_USUARIO=solo_usuario\n", encoding="utf-8")
        self.assertIsNone(load_saved_credentials(self.env_file))

    def test_04_plantilla_de_ejemplo_no_cuenta_como_credencial(self) -> None:
        """Copiar .env.example no evita el cuadro de primer uso."""
        self.env_file.write_text(
            "SOFIA_USUARIO=tu_documento\nSOFIA_PASSWORD=tu_clave\n",
            encoding="utf-8",
        )
        self.assertIsNone(load_saved_credentials(self.env_file))

    def test_05_no_imprime_la_contrasena(self) -> None:
        """Guardar credenciales no escribe la clave en la salida estandar."""
        import contextlib
        import io

        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida):
            save_credentials(
                SofiaCredentials(usuario="123", password="secreto-no-log"),
                self.env_file,
            )

        self.assertNotIn("secreto-no-log", salida.getvalue())


class TestResolucionDeCredenciales(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.env_file = self.base / ".env"
        os.environ.pop("SOFIA_USUARIO", None)
        os.environ.pop("SOFIA_PASSWORD", None)

    def tearDown(self) -> None:
        os.environ.pop("SOFIA_USUARIO", None)
        os.environ.pop("SOFIA_PASSWORD", None)
        self._tmp.cleanup()

    @staticmethod
    def _args(pedir: bool, forzar: bool = False):
        from types import SimpleNamespace

        return SimpleNamespace(
            pedir_credenciales=pedir, forzar_credenciales=forzar
        )

    def test_01_sin_credenciales_falla_si_no_es_interactivo(self) -> None:
        """Una tarea programada sin .env debe fallar, no quedarse esperando."""
        with self.assertRaises(RuntimeError):
            resolve_credentials(self._args(pedir=False), self.env_file)

    def test_02_pide_y_guarda_si_es_interactivo(self) -> None:
        """En modo interactivo pide una vez y persiste en .env."""
        nuevas = SofiaCredentials(usuario="999", password="nueva-clave")
        with patch(
            "bots.descargar_inasistencias.ask_credentials",
            return_value=nuevas,
        ) as ask:
            resultado = resolve_credentials(self._args(pedir=True), self.env_file)

        self.assertEqual(resultado, nuevas)
        ask.assert_called_once()
        self.assertTrue(self.env_file.exists())
        self.assertIn("SOFIA_USUARIO=999", self.env_file.read_text(encoding="utf-8"))

    def test_03_reutiliza_sin_abrir_cuadro(self) -> None:
        """Si .env ya tiene credenciales, no se vuelve a preguntar."""
        save_credentials(
            SofiaCredentials(usuario="111", password="guardada"),
            self.env_file,
        )
        with patch(
            "bots.descargar_inasistencias.ask_credentials"
        ) as ask:
            resultado = resolve_credentials(self._args(pedir=True), self.env_file)

        self.assertEqual(resultado.usuario, "111")
        ask.assert_not_called()

    def test_04_forzar_abre_el_cuadro(self) -> None:
        """--forzar-credenciales permite actualizar la clave guardada."""
        save_credentials(
            SofiaCredentials(usuario="111", password="vieja"),
            self.env_file,
        )
        nuevas = SofiaCredentials(usuario="111", password="nueva")
        with patch(
            "bots.descargar_inasistencias.ask_credentials",
            return_value=nuevas,
        ) as ask:
            resultado = resolve_credentials(
                self._args(pedir=True, forzar=True), self.env_file
            )

        self.assertEqual(resultado.password, "nueva")
        ask.assert_called_once()
        self.assertIn(
            "SOFIA_PASSWORD=nueva", self.env_file.read_text(encoding="utf-8")
        )


class TestCarpetaDeSalida(unittest.TestCase):
    def test_01_crea_la_carpeta_si_no_existe(self) -> None:
        """ensure_output_dir crea Escritorio\\Inasistencias y es idempotente."""
        with tempfile.TemporaryDirectory() as tmp:
            objetivo = Path(tmp) / "Inasistencias"
            self.assertFalse(objetivo.exists())
            self.assertEqual(ensure_output_dir(objetivo), objetivo)
            self.assertTrue(objetivo.is_dir())
            self.assertEqual(ensure_output_dir(objetivo), objetivo)

    def test_02_ruta_operativa_del_reporte(self) -> None:
        """El archivo conserva el nombre exacto que consume Power BI."""
        ruta = build_target_path(Path("C:/salida"), "15/01/2026", "09/11/2026")
        self.assertEqual(ruta.name, "Inasistencias.xls")

    def test_03_escritorio_termina_en_inasistencias(self) -> None:
        """La carpeta por defecto cuelga del Escritorio real del usuario."""
        ruta = default_inasistencias_dir()
        self.assertEqual(ruta.name, DEFAULT_INASISTENCIAS_FOLDER)
        self.assertEqual(ruta.parent, desktop_dir())


class TestRaizDeDatos(unittest.TestCase):
    def test_01_exe_dentro_de_dist_usa_la_raiz_del_proyecto(self) -> None:
        """dist\\SOFIABOT.exe reutiliza el .env y logs del proyecto."""
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "bots").mkdir()
            (raiz / "sofia_bots").mkdir()
            dist = raiz / "dist"
            dist.mkdir()

            self.assertEqual(detect_data_root(dist), raiz)

    def test_02_exe_fuera_del_proyecto_usa_su_propia_carpeta(self) -> None:
        """Un .exe copiado a otra carpeta sigue siendo portable."""
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp) / "SOFIABOT portable"
            carpeta.mkdir()

            self.assertEqual(detect_data_root(carpeta), carpeta)


class _SesionFalsa:
    def start(self):
        return object()

    def close(self) -> None:
        pass


class TestErroresDeCredenciales(unittest.TestCase):
    def test_01_login_rechazado_no_se_reintenta(self) -> None:
        """Un error de credenciales sale de inmediato, sin agotar reintentos."""

        def bootstrap(_page):
            raise SofiaLoginError("clave rechazada")

        runner = RestartingRunner(
            _SesionFalsa(),
            bootstrap,
            max_attempts=10,
            retry_delay_seconds=0,
            fatal_exceptions=(SofiaLoginError,),
        )

        with self.assertRaises(SofiaLoginError):
            runner.restart(attempts=10)

    def test_02_fallo_de_chromium_no_se_reintenta(self) -> None:
        """Si Chromium no arranca, no tiene sentido esperar 120 reintentos."""

        def bootstrap(_page):
            raise BrowserLaunchError("no se encontro chrome.exe")

        runner = RestartingRunner(
            _SesionFalsa(),
            bootstrap,
            max_attempts=5,
            retry_delay_seconds=0,
            fatal_exceptions=(BrowserLaunchError,),
        )

        with self.assertRaises(BrowserLaunchError):
            runner.restart(attempts=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
