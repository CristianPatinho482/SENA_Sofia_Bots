from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, TimeoutError

from .settings import BrowserSettings, RESOURCE_ROOT


T = TypeVar("T")


@dataclass
class BrowserSession:
    """Agrupa navegador, contexto y pagina para poder cerrarlos juntos."""

    playwright: Playwright
    settings: BrowserSettings
    browser: Browser | None = None
    context: BrowserContext | None = None
    page: Page | None = None

    def start(self) -> Page:
        """Abre una sesion limpia de Chromium preparada para descargar archivos."""
        self.close()
        bundled_browsers = RESOURCE_ROOT / "ms-playwright"
        if bundled_browsers.exists():
            import os

            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browsers)

        self.browser = self.playwright.chromium.launch(
            headless=self.settings.headless,
            slow_mo=self.settings.slow_mo,
        )
        self.context = self.browser.new_context(accept_downloads=True)
        self.context.set_default_timeout(self.settings.action_timeout_ms)
        self.context.set_default_navigation_timeout(self.settings.navigation_timeout_ms)
        self.page = self.context.new_page()
        return self.page

    def close(self) -> None:
        """Cierra recursos abiertos sin fallar si alguno ya estaba cerrado."""
        for resource in (self.context, self.browser):
            if resource is None:
                continue
            try:
                resource.close()
            except Exception:
                pass
        self.browser = None
        self.context = None
        self.page = None


class RestartingRunner(Generic[T]):
    """Ejecuta pasos con reintentos y reconstruye el navegador si algo falla."""

    def __init__(
        self,
        session: BrowserSession,
        bootstrap: Callable[[Page], None],
        max_attempts: int = 3,
        retry_delay_seconds: int = 60,
    ) -> None:
        self.session = session
        self.bootstrap = bootstrap
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds

    def restart(self, attempts: int | None = None) -> Page:
        """Reabre navegador y ejecuta login/menu; puede esperar a Sofia Plus."""
        max_attempts = attempts if attempts is not None else self.max_attempts
        attempt = 1
        last_error: Exception | None = None

        while max_attempts == 0 or attempt <= max_attempts:
            print("\n===================================")
            print("REINICIANDO NAVEGADOR")
            if max_attempts == 0:
                print(f"INTENTO {attempt}/SIN LIMITE")
            else:
                print(f"INTENTO {attempt}/{max_attempts}")
            print("===================================")

            try:
                page = self.session.start()
                self.bootstrap(page)
                return page
            except Exception as exc:
                last_error = exc
                self.session.close()
                print(f"\nNo fue posible iniciar sesion o abrir el modulo: {exc}")

                if max_attempts != 0 and attempt >= max_attempts:
                    break

                print(f"Esperando {self.retry_delay_seconds} segundos antes de reintentar...")
                time.sleep(self.retry_delay_seconds)
                attempt += 1

        raise RuntimeError("No fue posible reiniciar el navegador y preparar Sofia Plus.") from last_error

    def run_step(self, label: str, step: Callable[[Page], T]) -> T:
        """Ejecuta una accion del bot y reinicia la sesion si encuentra errores."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            page = self.session.page or self.restart()
            try:
                return step(page)
            except (TimeoutError, Exception) as exc:
                last_error = exc
                print(f"\nError en {label}. Intento {attempt}/{self.max_attempts}: {exc}")
                if attempt < self.max_attempts:
                    try:
                        self.restart()
                    except Exception as restart_error:
                        last_error = restart_error
        raise RuntimeError(f"No fue posible completar: {label}") from last_error
