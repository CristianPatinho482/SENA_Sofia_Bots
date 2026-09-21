from __future__ import annotations

import re

from playwright.sync_api import Frame, Page, TimeoutError

from .settings import SOFIA_URL, SofiaSettings
from .text import strip_accents


def accent_tolerant_pattern(label: str) -> re.Pattern[str]:
    """Crea patrones que encuentran textos con o sin tildes en los menus."""
    replacements = {
        "a": f"[a{chr(225)}]",
        "e": f"[e{chr(233)}]",
        "i": f"[i{chr(237)}]",
        "o": f"[o{chr(243)}]",
        "u": f"[u{chr(250)}{chr(252)}]",
        "n": f"[n{chr(241)}]",
    }
    pieces: list[str] = []
    for char in strip_accents(label).lower():
        if char in replacements:
            pieces.append(replacements[char])
        elif char.isspace():
            pieces.append(r"\s+")
        else:
            pieces.append(re.escape(char))
    return re.compile("".join(pieces), re.I)


def find_login_frame(page: Page, timeout_ms: int = 120_000) -> Frame:
    """Abre Sofia Plus y busca el iframe donde viven los campos de login."""
    page.goto(SOFIA_URL, timeout=timeout_ms)

    field_names = [
        "Numero de Documento",
        f"N{chr(250)}mero de Documento",
    ]

    waited_ms = 0
    poll_ms = 500

    while waited_ms <= timeout_ms:
        for frame in page.frames:
            for field_name in field_names:
                try:
                    field = frame.get_by_role("textbox", name=field_name)
                    if field.count() > 0:
                        field.first.wait_for(timeout=1_000)
                        return frame
                except Exception:
                    continue
        page.wait_for_timeout(poll_ms)
        waited_ms += poll_ms

    raise RuntimeError("No se encontro el iframe de login de Sofia Plus.")


def login(page: Page, settings: SofiaSettings) -> None:
    """Ingresa usuario y clave en el portal de Sofia Plus."""
    print("\nIniciando sesion Sofia Plus...")
    frame = find_login_frame(page, timeout_ms=settings.browser.navigation_timeout_ms)

    frame.get_by_role("textbox", name=re.compile("Documento", re.I)).fill(
        settings.credentials.usuario
    )
    frame.get_by_role("textbox", name=re.compile("Contrase", re.I)).fill(
        settings.credentials.password
    )
    frame.get_by_role("button", name=re.compile("Ingresar", re.I)).click()
    page.locator('[id="seleccionRol:roles"]').wait_for(timeout=30_000)
    print("Sesion iniciada.")


def select_role(page: Page, settings: SofiaSettings) -> None:
    """Selecciona el rol funcional que permite entrar a los reportes."""
    print("\nSeleccionando rol...")
    role_selector = page.locator('[id="seleccionRol:roles"]')

    try:
        role_selector.select_option(label=settings.role_label)
    except Exception:
        role_selector.select_option(settings.role_value)

    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except TimeoutError:
        pass
    page.get_by_role("link", name=accent_tolerant_pattern("Gestion de Tiempos")).wait_for(
        timeout=30_000
    )
    print("Rol seleccionado.")


def open_menu_path(page: Page, *labels: str) -> None:
    """Abre una ruta de menu haciendo clic en cada etiqueta recibida."""
    for label in labels:
        pattern = accent_tolerant_pattern(label)
        link = page.get_by_role("link", name=pattern)
        link.wait_for(timeout=30_000)
        link.click()


def content_frame(page: Page):
    """Devuelve el iframe principal donde se cargan los formularios internos."""
    frame = page.frame_locator('iframe[name="contenido"]')
    frame.locator("body").wait_for(timeout=30_000)
    return frame


def session_is_alive(page: Page) -> bool:
    """Valida rapidamente si la sesion aun muestra elementos de Sofia Plus."""
    try:
        page.get_by_role(
            "link",
            name=re.compile(f"Gestion|Gesti{chr(243)}n|Consultar|Sofia", re.I),
        ).first.wait_for(timeout=5_000)
        return True
    except Exception:
        return False


def bootstrap_sofia(page: Page, settings: SofiaSettings, module_path: tuple[str, ...]) -> None:
    """Rutina comun de arranque: login, rol y apertura del modulo requerido."""
    login(page, settings)
    select_role(page, settings)
    open_menu_path(page, *module_path)
