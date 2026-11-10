from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from sofia_bots.browser import (
    BrowserLaunchError,
    BrowserSession,
    RestartingRunner,
    configure_bundled_browsers,
)
from sofia_bots.control import ExcelControlLog
from sofia_bots.credential_store import load_saved_credentials, save_credentials
from sofia_bots.credentials_dialog import ask_credentials
from sofia_bots.downloads import save_download
from sofia_bots.excel_tools import rename_first_worksheet
from sofia_bots.inasistencias_cleaner import limpiar_inasistencias
from sofia_bots.power import suspend_windows
from sofia_bots.settings import (
    DEFAULT_ENV_FILE,
    BrowserSettings,
    SofiaCredentials,
    SofiaSettings,
    default_inasistencias_dir,
    load_env_file,
)
from sofia_bots.sofia import (
    SofiaLoginError,
    bootstrap_sofia,
    content_frame,
    session_is_alive,
)


DEFAULT_START_DATE = "15/01/2026"
DEFAULT_LOG_NAME = "control_inasistencias.xlsx"

# Ruta de menus que se abre despues del login y la seleccion de rol.
MODULE_PATH = (
    "Gestion de Tiempos",
    "Consultar Consolidado de",
    "Consolidado de Inasistencias",
)

MAX_REINTENTOS_CREDENCIALES = 3


def parse_args() -> argparse.Namespace:
    """Define parametros configurables sin tocar el codigo del bot."""
    load_env_file()
    default_output_dir = Path(
        os.getenv("INASISTENCIAS_SALIDA") or default_inasistencias_dir()
    )

    parser = argparse.ArgumentParser(
        description="Descarga el consolidado de inasistencias desde Sofia Plus."
    )
    parser.add_argument("--fecha-inicio", default=DEFAULT_START_DATE)
    # La fecha final se calcula al ejecutar el bot; por eso sirve para tareas diarias.
    parser.add_argument("--fecha-fin", default=datetime.now().strftime("%d/%m/%Y"))
    parser.add_argument(
        "--salida",
        type=Path,
        default=default_output_dir,
        help=(
            "Carpeta donde se guarda Inasistencias.xls. Por defecto es "
            "<Escritorio>\\Inasistencias."
        ),
    )
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
        help=(
            "Permite mostrar el cuadro de credenciales cuando no hay datos "
            "guardados en .env. Si ya existen, se reutilizan."
        ),
    )
    parser.add_argument(
        "--forzar-credenciales",
        action="store_true",
        help=(
            "Muestra el cuadro de credenciales aunque ya existan datos en .env. "
            "Usalo cuando Sofia Plus solicite cambiar la contrasena."
        ),
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


def ensure_output_dir(output_dir: Path) -> Path:
    """Crea la carpeta de salida si no existe (por ejemplo, Escritorio\\Inasistencias)."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"No fue posible crear la carpeta de salida: {output_dir}"
        ) from exc
    return output_dir


def resolve_credentials(
    args: argparse.Namespace,
    env_file: str | Path = DEFAULT_ENV_FILE,
) -> SofiaCredentials | None:
    """Recupera credenciales guardadas o las pide si el modo es interactivo."""
    saved = load_saved_credentials(env_file)

    if args.forzar_credenciales or saved is None:
        if not args.pedir_credenciales:
            if args.forzar_credenciales:
                raise RuntimeError(
                    "--forzar-credenciales requiere ejecutar en modo interactivo "
                    "(--pedir-credenciales)."
                )
            raise RuntimeError(
                "Faltan credenciales. Ejecuta el bot con --pedir-credenciales, "
                "o define SOFIA_USUARIO y SOFIA_PASSWORD en el archivo .env."
            )

        credentials = ask_credentials(
            usuario_inicial=saved.usuario if saved is not None else ""
        )
        if credentials is None:
            return None
        save_credentials(credentials, env_file)
        print("\nCredenciales guardadas en .env para las proximas ejecuciones.")
        return credentials

    return saved


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


def _descargar_una_vez(
    args: argparse.Namespace,
    credentials: SofiaCredentials,
    output_dir: Path,
) -> Path | None:
    """Ejecuta el ciclo completo de navegacion, descarga y limpieza."""
    settings = SofiaSettings(
        credentials=credentials,
        browser=BrowserSettings(headless=args.headless, slow_mo=args.slow_mo),
    )

    # Debe ejecutarse antes de sync_playwright: el driver lee la ruta al arrancar.
    configure_bundled_browsers()

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
            fatal_exceptions=(SofiaLoginError, BrowserLaunchError),
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

            return saved_path
        finally:
            session.close()


def main() -> None:
    """Orquesta configuracion, credenciales, descarga, limpieza y registro."""
    args = parse_args()
    output_dir = ensure_output_dir(args.salida)
    control = ExcelControlLog(output_dir / DEFAULT_LOG_NAME, key_column="REPORTE")
    report_key = f"inasistencias:{args.fecha_inicio}:{args.fecha_fin}"
    saved_path: Path | None = None

    try:
        credentials = resolve_credentials(args)
    except Exception as exc:
        control.error(report_key, exc)
        raise

    if credentials is None:
        print("\nEjecucion cancelada por el usuario.")
        return

    intento_credenciales = 0
    while True:
        try:
            saved_path = _descargar_una_vez(args, credentials, output_dir)
            break
        except SofiaLoginError as exc:
            intento_credenciales += 1
            puede_reintentar = (
                args.pedir_credenciales
                and intento_credenciales < MAX_REINTENTOS_CREDENCIALES
            )
            if not puede_reintentar:
                control.error(report_key, exc)
                raise

            print(f"\n{exc}")
            print("Ingresa de nuevo las credenciales actualizadas.")
            nuevas = ask_credentials(usuario_inicial=credentials.usuario)
            if nuevas is None:
                print("\nEjecucion cancelada por el usuario.")
                return
            save_credentials(nuevas)
            credentials = nuevas
        except Exception as exc:
            control.error(report_key, exc)
            raise

    control.success(report_key, str(saved_path))

    print("\n===================================")
    print("DESCARGA Y LIMPIEZA COMPLETADAS")
    print("===================================")
    print(f"\nArchivo listo para Power BI:\n{saved_path}")

    if args.suspender_al_final and saved_path is not None:
        suspend_windows(args.espera_suspension)


if __name__ == "__main__":
    main()
