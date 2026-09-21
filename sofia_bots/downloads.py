from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from .text import unique_path


def save_download(
    page: Page,
    trigger,
    target_path: Path,
    timeout_ms: int = 120_000,
    overwrite: bool = False,
) -> Path:
    """Ejecuta el clic de descarga y guarda el archivo en la ruta indicada."""
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with page.expect_download(timeout=timeout_ms) as download_info:
        trigger()

    download = download_info.value
    suffix = Path(download.suggested_filename).suffix or target_path.suffix
    final_path = target_path.with_suffix(suffix)
    if overwrite:
        # Para reportes diarios interesa reemplazar el archivo anterior.
        if final_path.exists():
            final_path.unlink()
    else:
        final_path = unique_path(final_path)
    download.save_as(final_path)
    return final_path
