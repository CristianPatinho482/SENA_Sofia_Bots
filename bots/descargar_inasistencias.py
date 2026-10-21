from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from sofia_bots.browser import BrowserSession, RestartingRunner
from sofia_bots.control import ExcelControlLog
from sofia_bots.credentials_dialog import ask_credentials
from sofia_bots.downloads import save_download
from sofia_bots.excel_tools import rename_first_worksheet
from sofia_bots.inasistencias_cleaner import limpiar_inasistencias
from sofia_bots.power import suspend_windows
from sofia_bots.settings import BrowserSettings, SofiaCredentials, SofiaSettings, load_env_file
from sofia_bots.sofia import bootstrap_sofia, content_frame, session_is_alive


DEFAULT_START_DATE = "15/01/2026"
DEFAULT_SHAREPOINT_DIR = Path(
    r"C:\Users\capatino\OneDrive - Servicio Nacional de Aprendizaje\Equipo ASTIN-DESAROLLOS POWER-BI - RAPS ASTIN 2026"
)
DEFAULT_LOG_NAME = "control_inasistencias.xlsx"

# Ruta de menus que se abre despues del login y la seleccion de rol.
MODULE_PATH = (
    "Gestion de Tiempos",
    "Consultar Consolidado de",
    "Consolidado de Inasistencias",
)


def parse_args() -> argparse.Namespace:
    """Define parametros configurables sin tocar el codigo del bot."""
    load_env_file()
    default_output_dir = Path(os.getenv("INASISTENCIAS_SALIDA", DEFAULT_SHAREPOINT_DIR))

    parser = argparse.ArgumentParser(
        description="Descarga el consolidado de inasistencias desde Sofia Plus."
    )
    parser.add_argument("--fecha-inicio", default=DEFAULT_START_DATE)
    # La fecha final se calcula al ejecutar el bot; por eso sirve para tareas diarias.
    parser.add_argument("--fecha-fin", default=datetime.now().strftime("%d/%m/%Y"))
    parser.add_argument("--salida", type=Path, default=default_output_dir)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=0)
    parser.add_argument("--intentos", type=int, default=3)
    parser.add_argument(
        "--reintentos-servidor",
        type=int,
        default=60,
        help="Intentos para esperar Sofia Plus durante el inicio. Usa 0 para reintentar sin limite.",
    )
    parser.add_argument(
        "--espera-servidor",
        type=int,
        default=60,
        help="Segundos de espera entre reintentos cuando Sofia Plus no esta disponible.",
    )
    parser.add_argument(
        "--suspender-al-final",
        action="store_true",
        help="Suspende Windows cuando el reporte termina correctamente.",
    )
    parser.add_argument(
        "--espera-suspension",
        type=int,
        default=60,
        help="Segundos de espera antes de suspender Windows al terminar.",
    )
    parser.add_argument(
        "--pedir-credenciales",
        action="store_true",
        help="Muestra un cuadro para ingresar usuario y contrasena antes de ejecutar.",
    )
    parser.add_argument(
        "--omitir-limpieza",
        action="store_true",
        help="Descarga el reporte pero no ejecuta el limpiador FSM.",
    )
    return parser.parse_args()


def build_target_path(output_dir: Path, fecha_inicio: str, fecha_fin: str) -> Path:
    """El reporte diario siempre queda con el mismo nombre operativo."""
    return output_dir / "Inasistencias.xls"


def validate_output_dir(output_dir: Path) -> Path:
    """Evita crear una carpeta falsa si OneDrive/SharePoint no esta sincronizado."""
    if not output_dir.exists():
        raise RuntimeError(
            "No se encontro la carpeta de salida. Verifica que OneDrive/SharePoint "
            f"este sincronizado y que la ruta exista: {output_dir}"
        )
    return output_dir


def fill_dates_and_download(page, output_dir: Path, fecha_inicio: str, fecha_fin: str) -> Path:
    """Llena fechas en Sofia Plus y descarga el consolidado de inasistencias."""
    iframe = content_frame(page)
    iframe.locator("#fechaInicioEvento").fill(fecha_inicio)
    iframe.locator("#fechaFinEvento").fill(fecha_fin)

    target_path = build_target_path(output_dir, fecha_inicio, fecha_fin)
    saved_path = save_download(
        page,
        trigger=lambda: iframe.get_by_role("button", name="Generar Informe").click(),
        target_path=target_path,
        overwrite=True,
    )
    # Si Sofia Plus cambia la extension sugerida, se conserva el nombre operativo
    # que consume Power BI (Inasistencias.xls).
    if saved_path != target_path:
        os.replace(saved_path, target_path)
        saved_path = target_path
    rename_first_worksheet(saved_path, "Inasistencias")
    return saved_path


def main() -> None:
    """Orquesta configuracion, login persistente, descarga y registro."""
    args = parse_args()
    output_dir = validate_output_dir(args.salida)
    control = ExcelControlLog(output_dir / DEFAULT_LOG_NAME, key_column="REPORTE")
    report_key = f"inasistencias:{args.fecha_inicio}:{args.fecha_fin}"
    saved_path: Path | None = None

    if args.pedir_credenciales:
        credentials = ask_credentials()
        if credentials is None:
            print("\nEjecucion cancelada por el usuario.")
            return
    else:
        credentials = SofiaCredentials.from_env()

    settings = SofiaSettings(
        credentials=credentials,
        browser=BrowserSettings(headless=args.headless, slow_mo=args.slow_mo),
    )

    with sync_playwright() as playwright:
        session = BrowserSession(playwright, settings.browser)

        def bootstrap(page) -> None:
            # Cada reinicio debe dejar el navegador listo en el modulo correcto.
            bootstrap_sofia(page, settings, MODULE_PATH)

        runner = RestartingRunner(
            session,
            bootstrap,
            max_attempts=args.intentos,
            retry_delay_seconds=args.espera_servidor,
        )

        try:
            runner.restart(attempts=args.reintentos_servidor)

            def job(page):
                # Si la sesion expiro entre el arranque y la descarga, se reconstruye.
                if not session_is_alive(page):
                    page = runner.restart()
                return fill_dates_and_download(
                    page,
                    output_dir=output_dir,
                    fecha_inicio=args.fecha_inicio,
                    fecha_fin=args.fecha_fin,
                )

            saved_path = runner.run_step("descarga de inasistencias", job)

            if args.omitir_limpieza:
                print("\nLimpieza omitida por --omitir-limpieza.")
            else:
                # La limpieza es obligatoria: si falla, el bot no reporta exito.
                print("\nLimpiando reporte de inasistencias...")
                saved_path = limpiar_inasistencias(saved_path)

            control.success(report_key, str(saved_path))

            print("\n===================================")
            print("DESCARGA Y LIMPIEZA COMPLETADAS")
            print("===================================")
            print(f"\nArchivo listo para Power BI:\n{saved_path}")

        except Exception as exc:
            control.error(report_key, exc)
            raise
        finally:
            session.close()

    if args.suspender_al_final and saved_path is not None:
        suspend_windows(args.espera_suspension)


if __name__ == "__main__":
    main()
