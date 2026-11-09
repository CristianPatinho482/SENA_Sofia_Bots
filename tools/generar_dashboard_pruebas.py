"""Genera un dashboard HTML con el resultado de las pruebas del proyecto.

Uso:
    python tools/generar_dashboard_pruebas.py

Salidas:
    reportes/dashboard_pruebas.html
    reportes/resultados_pruebas.json

El dashboard es autocontenido (sin CDN ni dependencias externas) y se puede
abrir en cualquier navegador o compartir como archivo unico.
"""

from __future__ import annotations

import html
import io
import json
import platform
import subprocess
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORTES = ROOT / "reportes"
DASHBOARD = REPORTES / "dashboard_pruebas.html"
JSON_SALIDA = REPORTES / "resultados_pruebas.json"
FSM_DIR = ROOT / "Proyecto Limpiador Inasistencias"

NOMBRES_SUITE = {
    "test_limpieza_integrada": "Integracion del limpiador",
    "test_fsm_inasistencias": "FSM original del limpiador",
}

ESTADOS = {
    "PASS": ("Aprobada", "ok"),
    "FAIL": ("Fallida", "fail"),
    "ERROR": ("Error", "error"),
    "SKIP": ("Omitida", "skip"),
}


class ResultadoConTiempos(unittest.TextTestResult):
    """ResultTest que registra estado y duracion por prueba."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.registros: list[dict] = []
        self._inicio: dict[str, float] = {}
        self._estado: dict[str, tuple[str, str]] = {}

    def startTest(self, test) -> None:  # noqa: N802 (API de unittest)
        self._inicio[test.id()] = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test) -> None:  # noqa: N802
        super().stopTest(test)
        duracion = time.perf_counter() - self._inicio.pop(
            test.id(), time.perf_counter()
        )
        estado, detalle = self._estado.pop(test.id(), ("ERROR", "Sin resultado"))
        modulo = test.id().split(".")[0]
        self.registros.append(
            {
                "id": test.id(),
                "nombre": test.id().split(".")[-1],
                "descripcion": test.shortDescription() or "",
                "suite": NOMBRES_SUITE.get(modulo, modulo),
                "modulo": modulo,
                "estado": estado,
                "detalle": detalle,
                "duracion": duracion,
            }
        )

    def addSuccess(self, test) -> None:  # noqa: N802
        self._estado[test.id()] = ("PASS", "")
        super().addSuccess(test)

    def addFailure(self, test, err) -> None:  # noqa: N802
        self._estado[test.id()] = ("FAIL", self._exc_info_to_string(err, test))
        super().addFailure(test, err)

    def addError(self, test, err) -> None:  # noqa: N802
        self._estado[test.id()] = ("ERROR", self._exc_info_to_string(err, test))
        super().addError(test, err)

    def addSkip(self, test, reason) -> None:  # noqa: N802
        self._estado[test.id()] = ("SKIP", reason)
        super().addSkip(test, reason)


def ejecutar_suite(suite: unittest.TestSuite) -> dict:
    """Ejecuta una suite y devuelve sus registros y totales."""
    stream = io.StringIO()
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=2,
        resultclass=ResultadoConTiempos,
    )
    inicio = time.perf_counter()
    resultado = runner.run(suite)
    duracion = time.perf_counter() - inicio
    return {
        "registros": resultado.registros,
        "total": resultado.testsRun,
        "fallidas": len(resultado.failures),
        "errores": len(resultado.errors),
        "omitidas": len(resultado.skipped),
        "duracion": duracion,
        "salida": stream.getvalue(),
    }


def ejecutar_compileall() -> dict:
    """Verifica que todos los modulos del proyecto compilen."""
    carpetas = ["bots", "sofia_bots", "tests", "Proyecto Limpiador Inasistencias"]
    inicio = time.perf_counter()
    proceso = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", *carpetas],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "nombre": "Compilacion de modulos (compileall)",
        "ok": proceso.returncode == 0,
        "detalle": (proceso.stdout + proceso.stderr).strip()
        or "Todos los modulos compilan sin errores.",
        "duracion": time.perf_counter() - inicio,
    }


def ejecutar_smoke_import() -> dict:
    """Verifica la importacion del limpiador y su esquema de salida."""
    inicio = time.perf_counter()
    try:
        from sofia_bots.inasistencias_cleaner import COLUMNAS_SALIDA

        esperadas = [
            "Instructor",
            "Ficha",
            "Programa",
            "Apellidos",
            "Nombres",
            "Identificacion Aprendiz",
            "Fecha Inicio",
            "Fecha Fin",
            "Cant.horas",
            "Justificacion",
        ]
        ok = COLUMNAS_SALIDA == esperadas
        detalle = (
            "Esquema de 10 columnas verificado."
            if ok
            else f"Esquema inesperado: {COLUMNAS_SALIDA}"
        )
    except Exception as exc:  # noqa: BLE001
        ok = False
        detalle = f"{type(exc).__name__}: {exc}"
    return {
        "nombre": "Importacion y esquema del limpiador",
        "ok": ok,
        "detalle": detalle,
        "duracion": time.perf_counter() - inicio,
    }


def datos_git() -> dict:
    """Obtiene rama y commit actuales, sin fallar si Git no esta disponible."""
    def _git(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""

    return {
        "rama": _git("branch", "--show-current") or "desconocida",
        "commit": _git("rev-parse", "--short", "HEAD") or "desconocido",
    }


def _formato_duracion(segundos: float) -> str:
    if segundos < 1:
        return f"{segundos * 1000:.0f} ms"
    return f"{segundos:.2f} s"


def _badge(estado: str) -> str:
    etiqueta, clase = ESTADOS.get(estado, (estado, "error"))
    return f'<span class="badge {clase}">{html.escape(etiqueta)}</span>'


def construir_html(datos: dict) -> str:
    resumen = datos["resumen"]
    total = resumen["total"]
    correctas = total - resumen["fallidas"] - resumen["errores"] - resumen["omitidas"]
    todo_ok = resumen["fallidas"] == 0 and resumen["errores"] == 0 and all(
        c["ok"] for c in datos["chequeos"]
    )
    estado_general = "Ejecucion satisfactoria" if todo_ok else "Hay fallos por revisar"
    clase_general = "ok" if todo_ok else "fail"

    tarjetas = [
        ("Pruebas", total, "neutral"),
        ("Aprobadas", correctas, "ok"),
        ("Fallidas", resumen["fallidas"], "fail"),
        ("Errores", resumen["errores"], "error"),
        ("Omitidas", resumen["omitidas"], "skip"),
        ("Tiempo total", _formato_duracion(resumen["duracion"]), "neutral"),
    ]
    html_tarjetas = "\n".join(
        f'<div class="card {clase}"><span class="value">{html.escape(str(valor))}</span>'
        f'<span class="label">{html.escape(etiqueta)}</span></div>'
        for etiqueta, valor, clase in tarjetas
    )

    secciones = []
    for suite in datos["suites"]:
        filas = []
        for registro in suite["registros"]:
            detalle = ""
            if registro["detalle"]:
                detalle = (
                    '<details><summary>Ver detalle</summary><pre>'
                    f'{html.escape(registro["detalle"])}</pre></details>'
                )
            filas.append(
                "<tr>"
                f'<td><code>{html.escape(registro["nombre"])}</code></td>'
                f'<td>{html.escape(registro["descripcion"])}</td>'
                f'<td>{_badge(registro["estado"])}{detalle}</td>'
                f'<td class="num">{_formato_duracion(registro["duracion"])}</td>'
                "</tr>"
            )
        secciones.append(
            f"""
            <section class="suite">
              <h2>{html.escape(suite["nombre"])}</h2>
              <p class="muted">{suite["total"]} pruebas &middot;
                 {_formato_duracion(suite["duracion"])} &middot;
                 {suite["fallidas"]} fallidas &middot; {suite["errores"]} errores</p>
              <table>
                <thead><tr><th>Prueba</th><th>Descripcion</th><th>Estado</th><th class="num">Duracion</th></tr></thead>
                <tbody>{''.join(filas)}</tbody>
              </table>
            </section>
            """
        )

    chequeos = "\n".join(
        f'<li><span class="badge {"ok" if c["ok"] else "fail"}">'
        f'{"OK" if c["ok"] else "FALLO"}</span> '
        f'<strong>{html.escape(c["nombre"])}</strong> '
        f'<span class="muted">{html.escape(c["detalle"])}</span></li>'
        for c in datos["chequeos"]
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard de pruebas - SOFIABOT</title>
<style>
  :root {{
    --bg: #f4f6fb; --panel: #ffffff; --text: #172033; --muted: #6b7690;
    --line: #e3e8f2; --ok: #0f9d58; --ok-bg: #e6f6ec;
    --fail: #d93025; --fail-bg: #fdeceb; --error: #b06000; --error-bg: #fff4e0;
    --skip: #5f6368; --skip-bg: #eef0f4; --accent: #1a56db;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
  }}
  header {{
    background: linear-gradient(135deg, #123a8f, #1a56db 60%, #2f7cf6);
    color: #fff; padding: 32px 40px 28px;
  }}
  header h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: .2px; }}
  header p {{ margin: 0; opacity: .9; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 10px 24px; margin-top: 18px; font-size: 13px; }}
  .meta span {{ background: rgba(255,255,255,.14); padding: 6px 10px; border-radius: 6px; }}
  main {{ max-width: 1180px; margin: -18px auto 40px; padding: 0 24px; }}
  .banner {{
    background: var(--panel); border-radius: 12px; padding: 16px 20px;
    box-shadow: 0 6px 24px rgba(23,32,51,.08); font-weight: 600;
    border-left: 6px solid var(--ok);
  }}
  .banner.fail {{ border-left-color: var(--fail); }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; margin: 18px 0; }}
  .card {{
    background: var(--panel); border-radius: 12px; padding: 16px 18px;
    box-shadow: 0 4px 16px rgba(23,32,51,.06); display: flex; flex-direction: column; gap: 4px;
    border-top: 4px solid var(--line);
  }}
  .card.ok {{ border-top-color: var(--ok); }}
  .card.fail {{ border-top-color: var(--fail); }}
  .card.error {{ border-top-color: var(--error); }}
  .card.skip {{ border-top-color: var(--skip); }}
  .card .value {{ font-size: 26px; font-weight: 700; }}
  .card .label {{ color: var(--muted); font-size: 13px; }}
  .suite {{ background: var(--panel); border-radius: 12px; padding: 20px 22px; margin: 18px 0; box-shadow: 0 4px 16px rgba(23,32,51,.06); }}
  .suite h2 {{ margin: 0 0 4px; font-size: 18px; }}
  .muted {{ color: var(--muted); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
  th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
  th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .4px; }}
  td.num, th.num {{ text-align: right; white-space: nowrap; }}
  tr:last-child td {{ border-bottom: none; }}
  code {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 12.5px; }}
  .badge {{ display: inline-block; padding: 3px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .badge.ok {{ color: var(--ok); background: var(--ok-bg); }}
  .badge.fail {{ color: var(--fail); background: var(--fail-bg); }}
  .badge.error {{ color: var(--error); background: var(--error-bg); }}
  .badge.skip {{ color: var(--skip); background: var(--skip-bg); }}
  details {{ margin-top: 6px; }}
  summary {{ cursor: pointer; color: var(--accent); font-size: 12px; }}
  pre {{ white-space: pre-wrap; background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 8px; font-size: 12px; overflow-x: auto; }}
  .checks ul {{ list-style: none; padding: 0; margin: 0; }}
  .checks li {{ padding: 10px 0; border-bottom: 1px solid var(--line); }}
  .checks li:last-child {{ border-bottom: none; }}
  .pending {{ border-left: 4px solid var(--accent); }}
  footer {{ max-width: 1180px; margin: 0 auto 40px; padding: 0 24px; color: var(--muted); font-size: 12px; }}
  footer code {{ background: var(--skip-bg); padding: 2px 6px; border-radius: 4px; }}
</style>
</head>
<body>
<header>
  <h1>Dashboard de pruebas</h1>
  <p>SOFIABOT Inasistencias &middot; resultados de la ejecucion automatizada</p>
  <div class="meta">
    <span>Fecha: {html.escape(datos["generado"])}</span>
    <span>Rama: {html.escape(datos["git"]["rama"])}</span>
    <span>Commit: {html.escape(datos["git"]["commit"])}</span>
    <span>Python: {html.escape(datos["python"])}</span>
    <span>Sistema: {html.escape(datos["sistema"])}</span>
  </div>
</header>
<main>
  <div class="banner {clase_general}">{html.escape(estado_general)}</div>
  <section class="cards">{html_tarjetas}</section>
  {''.join(secciones)}
  <section class="suite checks">
    <h2>Chequeos adicionales</h2>
    <ul>{chequeos}</ul>
  </section>
  <section class="suite pending">
    <h2>Pruebas no ejecutadas en esta corrida</h2>
    <ul>
      <li><strong>Navegacion real contra Sofia Plus:</strong> requiere credenciales y red; se valida manualmente con el bot.</li>
      <li><strong>Actualizacion de Power BI:</strong> requiere Power BI Desktop y el archivo de salida sincronizado.</li>
    </ul>
  </section>
</main>
<footer>
  Generado con <code>python tools/generar_dashboard_pruebas.py</code>.
  Para repetir las suites: <code>python -m unittest discover -s tests -v</code>.
</footer>
</body>
</html>
"""


def main() -> int:
    inicio = time.perf_counter()
    REPORTES.mkdir(parents=True, exist_ok=True)

    # 1. Suites de pruebas.
    suite_integracion = unittest.defaultTestLoader.discover(
        str(ROOT / "tests")
    )
    resultado_integracion = ejecutar_suite(suite_integracion)

    if str(FSM_DIR) not in sys.path:
        sys.path.insert(0, str(FSM_DIR))
    suite_fsm = unittest.defaultTestLoader.loadTestsFromName(
        "test_fsm_inasistencias"
    )
    resultado_fsm = ejecutar_suite(suite_fsm)
    if str(FSM_DIR) in sys.path:
        sys.path.remove(str(FSM_DIR))

    suites = [
        {
            "nombre": NOMBRES_SUITE["test_limpieza_integrada"],
            **resultado_integracion,
        },
        {
            "nombre": NOMBRES_SUITE["test_fsm_inasistencias"],
            **resultado_fsm,
        },
    ]

    # 2. Chequeos estaticos.
    chequeos = [ejecutar_compileall(), ejecutar_smoke_import()]

    total = sum(s["total"] for s in suites)
    fallidas = sum(s["fallidas"] for s in suites)
    errores = sum(s["errores"] for s in suites)
    omitidas = sum(s["omitidas"] for s in suites)
    duracion = time.perf_counter() - inicio

    datos = {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "git": datos_git(),
        "python": platform.python_version(),
        "sistema": platform.platform(),
        "resumen": {
            "total": total,
            "fallidas": fallidas,
            "errores": errores,
            "omitidas": omitidas,
            "duracion": duracion,
        },
        "suites": suites,
        "chequeos": chequeos,
    }

    JSON_SALIDA.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    DASHBOARD.write_text(construir_html(datos), encoding="utf-8")

    print(f"Dashboard: {DASHBOARD}")
    print(f"JSON:      {JSON_SALIDA}")
    print(
        f"Resultado: {total - fallidas - errores - omitidas}/{total} aprobadas, "
        f"{fallidas} fallidas, {errores} errores, {omitidas} omitidas"
    )
    return 0 if fallidas == 0 and errores == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
