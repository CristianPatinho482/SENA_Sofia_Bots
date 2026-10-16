"""Limpiador ETL de Inasistencias basado en FSM.

Implementa la especificacion formal del documento
`documento-especificacion-fsm-inasistencias`:
  - Automata determinista M = (Q, Sigma, delta_fsm, q0, F) con 8 estados.
  - Invariante de desplazamiento Dynamic Phase-Shift (delta_i dinamico por fila).
  - Operador de fision atomica alpha("Apellidos, Nombres", ",").
  - Memoria auxiliar acotada O(1): solo fila actual + variables de estado.

El reporte origen presenta dos plantillas (fases) de fila entremezcladas:
  - DISPERSA: campos en columnas (2,5,7,9,13,14,15,18)  -> fase canonica d=2.
  - COMPACTA: campos en columnas (0,3,4,6,8,10,11,12)  -> fase canonica d=0.
  - DENSA:    fila compacta de 4 celdas (ID, nombre, fecha, estado), usada en
    pruebas y reportes resumidos -> fase canonica d=0.
La deteccion es semantica (por predicados, no por indice absoluto): para cada
fila se localizan las celdas ancla (ficha / documento) y se elige la
(plantilla, delta) con maximo Ajuste; sin anclas ni ajuste suficiente la fila
va a ERROR_RECOVERY.

Esquema relacional de salida (directamente consumible por Power Query/PBI):
  ["Instructor", "Ficha", "Programa", "Apellidos", "Nombres",
   "Identificacion Aprendiz", "Fecha Inicio", "Fecha Fin",
   "Cant.horas", "Justificacion"]

Notas de mapeo:
  - "Ficha" ("3411438 - COORDINACION...") se proyecta en numero (Ficha) y
    nombre del programa (Programa) sin perdida de informacion.
  - "Aprendiz" se somete a fision alpha por ","; los nombres del reporte real
    no traen coma, caso en que alpha retorna (nombre_completo, "").
  - Encabezados normalizados sin tildes para maxima compatibilidad.
  - Formatos de entrada soportados: .xls, .xlsx, .csv (separador ";").

Uso:
  python fsm_inasistencias_cleaner.py [entrada [salida]]
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, date
from enum import Enum, auto

import pandas as pd

ENTRADA_PREDETERMINADA = (
    r"C:\Users\capatino\OneDrive - Servicio Nacional de Aprendizaje"
    r"\Equipo ASTIN-DESAROLLOS POWER-BI - RAPS ASTIN 2026\Inasistencias.xls"
)
SALIDA_PREDETERMINADA = (
    r"C:\Users\capatino\OneDrive - Servicio Nacional de Aprendizaje"
    r"\BACKUP DISCO\Mis programas\AREA LABORAL\AREA LABORAL\SENA"
    r"\RPAS - ASTIN 2026\Proyecto Limpiador Inasistencias"
    r"\Inasistencias_Limpio.xlsx"
)


class EstadoFSM(Enum):
    """Conjunto de estados Q del automata (8 estados segun especificacion)."""

    INIT = auto()
    SCAN_ROW = auto()
    IGNORE_NOISE = auto()
    REALIGN = auto()
    SPLIT_FIELDS = auto()
    EMIT_RECORD = auto()
    ERROR_RECOVERY = auto()
    FINISH = auto()


# Esquema relacional objetivo (orden fijo, una sola fila de encabezado).
COLUMNAS_SALIDA = [
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

# Plantillas: offsets relativos a delta de los 8 campos
# (ficha, instructor, documento, aprendiz, fecha_ini, fecha_fin, horas, just).
PLANTILLA_DISPERSA = (0, 3, 5, 7, 11, 12, 13, 16)  # fase canonica d=2
PLANTILLA_COMPACTA = (0, 3, 4, 6, 8, 10, 11, 12)  # fase canonica d=0
PLANTILLA_DENSA = (0, 1, 2, 3)  # fila resumida (id, nombre, fecha, estado)

UMBRAL_REAL = 7  # sobre 10 puntos ponderados
UMBRAL_DENSA = 4  # sobre 5 puntos ponderados

# Firma de encabezados / metadatos parasitos S_meta (con y sin tildes).
_PALABRAS_META = (
    r"INSTRUCTOR|FICHA|APRENDIZ|IDENTIFICACI[OÓ]N|FECHA\s*INICIO|FECHA\s*FIN|"
    r"CANT\.?\s*HORAS|JUSTIFICACI[OÓ]N|CONSOLIDADO|ID\b|DOCUMENTO|ESTUDIANTE|"
    r"REPORTE|P[AÁ]GINA|T[IÍ]TULO|TOTAL|LISTADO|REGISTRO"
)

_RE_META = re.compile(rf"^({_PALABRAS_META})", re.IGNORECASE)
_RE_ID = re.compile(r"^(\d{4,12}|[A-Z]{2,4}\s*-\s*\d{4,12})$")
_RE_FICHA = re.compile(r"^\d{4,12}\s*-")
_RE_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")
_RE_FECHA_ES = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")


def _a_texto(celda) -> str:
    """Normaliza una celda a texto sin convertir NaN/None en 'nan'/'None'."""
    if celda is None:
        return ""
    try:
        if pd.isna(celda):  # NaN, NaT, None
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(celda, float) and celda.is_integer():
        return str(int(celda))
    if isinstance(celda, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(celda).strftime("%Y-%m-%d")
    texto = str(celda).strip()
    if texto.lower() in ("nan", "nat", "none"):
        return ""
    return texto


class LimpiadorInasistenciasFSM:
    """Controlador stream-driven que procesa el archivo fila por fila."""

    def __init__(self, archivo_entrada: str, archivo_salida: str):
        self.archivo_entrada = archivo_entrada
        self.archivo_salida = archivo_salida
        self.estado_actual = EstadoFSM.INIT
        self.registros_procesados: list[dict] = []
        self.log_errores: list[dict] = []
        self.filas_ignoradas = 0
        self.patron_meta = _RE_META

    # ------------------------------------------------------------------
    # Predicados semanticos P_t
    # ------------------------------------------------------------------
    def es_celda_vacia(self, val) -> bool:
        return _a_texto(val) == ""

    def es_id_valido(self, val) -> bool:
        """Documento: digitos puros o prefijo tipo 'CC - 1151969122'."""
        return bool(_RE_ID.match(_a_texto(val).strip()))

    def es_ficha_valida(self, val) -> bool:
        """Ficha: numero seguido de guion y nombre del programa."""
        return bool(_RE_FICHA.match(_a_texto(val).strip()))

    def es_texto_valido(self, val) -> bool:
        texto = _a_texto(val)
        if not texto or self.es_id_valido(texto) or self.es_ficha_valida(texto):
            return False
        return bool(re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", texto))

    def es_fecha_valida(self, val) -> bool:
        if isinstance(val, (datetime, date, pd.Timestamp)):
            return not (isinstance(val, pd.Timestamp) and pd.isna(val))
        texto = _a_texto(val)
        if not texto or not re.search(r"\d", texto):
            return False
        if _RE_FECHA_ISO.match(texto) or _RE_FECHA_ES.match(texto):
            return True
        try:
            pd.to_datetime(texto, errors="raise")
            return True
        except (ValueError, TypeError, OverflowError):
            return False

    def es_horas_valido(self, val) -> bool:
        texto = _a_texto(val).replace(",", ".")
        try:
            return bool(texto) and float(texto) >= 0
        except ValueError:
            return False

    def es_booleano_justificacion(self, val) -> bool:
        return not self.es_celda_vacia(val)

    # ------------------------------------------------------------------
    # Logica de filtrado S_meta
    # ------------------------------------------------------------------
    def es_ruido_o_cabecera(self, fila: list) -> bool:
        """True si la fila es vacia, titulo de impresion o encabezado repetido."""
        if not fila:
            return True
        if all(self.es_celda_vacia(c) for c in fila):
            return True
        primer = next((_a_texto(c) for c in fila if not self.es_celda_vacia(c)), "")
        if not primer:
            return True
        if self.patron_meta.search(primer):
            return True
        # Encabezado intermedio aunque no empiece por palabra meta.
        celdas = [_a_texto(c) for c in fila if not self.es_celda_vacia(c)]
        if len(celdas) >= 3:
            hits = sum(1 for c in celdas if self.patron_meta.search(c))
            if hits >= 3 and hits / len(celdas) >= 0.5:
                return True
        return False

    # ------------------------------------------------------------------
    # Modelo dinamico Phase-Shift: Ajuste + (plantilla, delta_i) optimos
    # ------------------------------------------------------------------
    def _ajuste_real(self, fila: list, d: int, offsets: tuple) -> int:
        """Compatibilidad 0..10 de la fila desplazada d con plantilla real."""
        c = lambda k: fila[d + offsets[k]] if (d + offsets[k]) < len(fila) else None
        puntaje = 0
        if self.es_ficha_valida(c(0)):
            puntaje += 2  # ancla principal
        if self.es_texto_valido(c(1)):
            puntaje += 1
        if self.es_id_valido(c(2)):
            puntaje += 2  # ancla secundaria
        if self.es_texto_valido(c(3)):
            puntaje += 1
        if self.es_fecha_valida(c(4)):
            puntaje += 1
        if self.es_fecha_valida(c(5)):
            puntaje += 1
        if self.es_horas_valido(c(6)):
            puntaje += 1
        if self.es_booleano_justificacion(c(7)):
            puntaje += 1
        return puntaje

    def _ajuste_densa(self, fila: list, d: int) -> int:
        """Compatibilidad 0..5 con fila resumida (id, nombre, fecha, estado)."""
        c = lambda k: fila[d + k] if (d + k) < len(fila) else None
        puntaje = 0
        if self.es_id_valido(c(0)):
            puntaje += 2
        nombre = _a_texto(c(1))
        if nombre and ("," in nombre or self.es_texto_valido(nombre)):
            puntaje += 1
        if self.es_fecha_valida(c(2)):
            puntaje += 1
        if not self.es_celda_vacia(c(3)):
            puntaje += 1
        return puntaje

    def _candidatos_delta(self, fila: list) -> set[int]:
        """Deltas plausibles derivados de las celdas ancla (ficha/documento)."""
        candidatos = {0}
        for i, celda in enumerate(fila):
            if self.es_ficha_valida(celda):
                candidatos.add(i)  # offset 0 en ambas plantillas reales
            if self.es_id_valido(celda):
                candidatos.update({i, i - 4, i - 5})  # offsets del documento
        return {d for d in candidatos if 0 <= d < len(fila)}

    def _detectar(self, fila: list) -> tuple[int, tuple | None]:
        """Retorna (delta_i, plantilla). (-1, None) si no alineable."""
        if not fila:
            return -1, None
        mejor = (-1, None, -1)  # (puntajeCmp, plantilla, d) con desempate
        for d in sorted(self._candidatos_delta(fila)):
            for plantilla in (PLANTILLA_DISPERSA, PLANTILLA_COMPACTA):
                puntaje = self._ajuste_real(fila, d, plantilla)
                if puntaje >= UMBRAL_REAL and (
                    puntaje > mejor[0]
                    or (puntaje == mejor[0] and mejor[1] == PLANTILLA_DENSA)
                ):
                    mejor = (puntaje, plantilla, d)
            puntaje_d = self._ajuste_densa(fila, d)
            if puntaje_d >= UMBRAL_DENSA and puntaje_d > mejor[0] and mejor[1] is None:
                mejor = (puntaje_d, PLANTILLA_DENSA, d)
        if mejor[1] is None:
            return -1, None
        return mejor[2], mejor[1]

    def calcular_desfase_optimo(self, fila: list) -> int:
        """Halla delta_i dinamico. Retorna -1 si la fila no es alineable."""
        delta, _ = self._detectar(fila)
        return delta

    # ------------------------------------------------------------------
    # Operador de fision atomica alpha(c, ",")
    # ------------------------------------------------------------------
    def separar_apellidos_nombres(self, texto_compuesto) -> tuple[str, str]:
        """Fisiona 'Apellidos, Nombres' por el delimitador ','."""
        texto = _a_texto(texto_compuesto)
        if "," in texto:
            izq, der = texto.split(",", 1)
            return izq.strip(), der.strip()
        return texto, ""

    # Alias del mismo operador (nombre usado en el documento de especificacion).
    def separar_nombres(self, texto_compuesto) -> tuple[str, str]:
        return self.separar_apellidos_nombres(texto_compuesto)

    # ------------------------------------------------------------------
    # Transicion fila-a-fila (usada por pruebas unitarias y por ejecutar())
    # ------------------------------------------------------------------
    def procesar_siguiente(self, fila_raw: list):
        """Avanza la FSM con una fila. Retorna el registro o None.

        Estados resultantes: EMIT_RECORD (exito), IGNORE_NOISE (ruido),
        ERROR_RECOVERY (basura recuperable).
        """
        self.estado_actual = EstadoFSM.SCAN_ROW
        if self.es_ruido_o_cabecera(fila_raw):
            self.estado_actual = EstadoFSM.IGNORE_NOISE
            self.filas_ignoradas += 1
            return None
        self.estado_actual = EstadoFSM.REALIGN
        delta, plantilla = self._detectar(list(fila_raw))
        if delta == -1:
            self.estado_actual = EstadoFSM.ERROR_RECOVERY
            try:
                contenido = list(fila_raw)
            except TypeError:
                contenido = fila_raw
            self.log_errores.append({"contenido": contenido})
            return None
        self.estado_actual = EstadoFSM.SPLIT_FIELDS
        registro = self._construir_registro(list(fila_raw), delta, plantilla)
        self.estado_actual = EstadoFSM.EMIT_RECORD
        self.registros_procesados.append(registro)
        return registro

    # Alias de compatibilidad con el pseudocodigo del documento.
    def procesar_fila(self, fila_raw: list):
        return self.procesar_siguiente(fila_raw)

    @staticmethod
    def _normalizar_fecha(val):
        try:
            ts = pd.to_datetime(val, errors="raise")
            if pd.isna(ts):
                return None
            return ts.normalize().to_pydatetime()
        except (ValueError, TypeError, OverflowError):
            return None

    @staticmethod
    def _normalizar_horas(val):
        try:
            return float(_a_texto(val).replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _partir_ficha(texto: str) -> tuple[str, str]:
        """'3411438 - PROGRAMA' -> ('3411438', 'PROGRAMA')."""
        texto = _a_texto(texto)
        if "-" in texto:
            num, prog = texto.split("-", 1)
            num = num.strip()
            if re.fullmatch(r"\d{4,12}", num):
                return num, prog.strip()
        return texto, ""

    def _construir_registro(self, fila: list, delta: int, plantilla: tuple) -> dict:
        """Proyeccion pi + fision alpha sobre la tupla realineada tau_delta."""

        def col(offset: int) -> str:
            i = delta + offset
            return _a_texto(fila[i]) if i < len(fila) else ""

        def raw(offset: int):
            i = delta + offset
            return fila[i] if i < len(fila) else None

        if plantilla == PLANTILLA_DENSA:
            apellidos, nombres = self.separar_apellidos_nombres(raw(1))
            return {
                "Instructor": "",
                "Ficha": "",
                "Programa": "",
                "Apellidos": apellidos,
                "Nombres": nombres,
                "Identificacion Aprendiz": col(0),
                "Fecha Inicio": self._normalizar_fecha(raw(2)),
                "Fecha Fin": None,
                "Cant.horas": None,
                "Justificacion": col(3),
            }
        o = plantilla
        ficha_num, programa = self._partir_ficha(raw(o[0]))
        apellidos, nombres = self.separar_apellidos_nombres(raw(o[3]))
        return {
            "Instructor": col(o[1]),
            "Ficha": ficha_num,
            "Programa": programa,
            "Apellidos": apellidos,
            "Nombres": nombres,
            "Identificacion Aprendiz": col(o[2]),
            "Fecha Inicio": self._normalizar_fecha(raw(o[4])),
            "Fecha Fin": self._normalizar_fecha(raw(o[5])),
            "Cant.horas": self._normalizar_horas(raw(o[6])),
            "Justificacion": col(o[7]),
        }

    # ------------------------------------------------------------------
    # Lectura multiformato + bucle principal de la FSM + exportacion
    # ------------------------------------------------------------------
    def _leer_entrada(self) -> pd.DataFrame:
        ext = os.path.splitext(self.archivo_entrada)[1].lower()
        if ext == ".xls":
            return pd.read_excel(self.archivo_entrada, header=None, engine="xlrd")
        if ext == ".csv":
            for encoding in ("utf-8-sig", "latin-1"):
                try:
                    return pd.read_csv(
                        self.archivo_entrada, header=None, sep=";",
                        encoding=encoding, dtype=str,
                    )
                except UnicodeDecodeError:
                    continue
            return pd.read_csv(
                self.archivo_entrada, header=None, sep=";",
                encoding="latin-1", dtype=str,
            )
        return pd.read_excel(self.archivo_entrada, header=None, engine="openpyxl")

    def ejecutar(self) -> str:
        """Procesa el archivo de entrada fila por fila (memoria auxiliar O(1))."""
        print("[FSM] Iniciando maquina de estados...")
        self.estado_actual = EstadoFSM.INIT
        # INIT: esquema objetivo T cargado (plantillas + predicados).
        self.estado_actual = EstadoFSM.SCAN_ROW
        try:
            df_raw = self._leer_entrada()
        except FileNotFoundError:
            self.estado_actual = EstadoFSM.FINISH
            print(f"[FSM] ERROR: no se encontro el archivo '{self.archivo_entrada}'.")
            raise
        total = len(df_raw)
        # Bucle MIENTRAS + SEGUN: solo la fila actual vive en memoria auxiliar.
        for idx, fila_series in df_raw.iterrows():
            fila = fila_series.tolist()
            if self.estado_actual == EstadoFSM.SCAN_ROW:
                if self.es_ruido_o_cabecera(fila):
                    self.estado_actual = EstadoFSM.IGNORE_NOISE
                else:
                    self.estado_actual = EstadoFSM.REALIGN
            if self.estado_actual == EstadoFSM.IGNORE_NOISE:
                self.filas_ignoradas += 1
                self.estado_actual = EstadoFSM.SCAN_ROW
                continue
            if self.estado_actual == EstadoFSM.REALIGN:
                delta, plantilla = self._detectar(fila)
                if delta != -1:
                    registro = self._construir_registro(fila, delta, plantilla)
                    self.estado_actual = EstadoFSM.SPLIT_FIELDS
                else:
                    self.estado_actual = EstadoFSM.ERROR_RECOVERY
            if self.estado_actual == EstadoFSM.ERROR_RECOVERY:
                self.log_errores.append({"fila_index": idx, "contenido": fila})
                self.estado_actual = EstadoFSM.SCAN_ROW
                continue
            if self.estado_actual == EstadoFSM.SPLIT_FIELDS:
                self.estado_actual = EstadoFSM.EMIT_RECORD
            if self.estado_actual == EstadoFSM.EMIT_RECORD:
                self.registros_procesados.append(registro)
                self.estado_actual = EstadoFSM.SCAN_ROW
            if (idx + 1) % 5000 == 0:
                print(f"[FSM] ... {idx + 1}/{total} filas revisadas")
        self.estado_actual = EstadoFSM.FINISH
        self._exportar_resultados()
        return "Procesamiento FSM Finalizado Exitosamente"

    def _exportar_resultados(self) -> None:
        df_limpio = pd.DataFrame(self.registros_procesados, columns=COLUMNAS_SALIDA)
        if not df_limpio.empty:
            for col_fecha in ("Fecha Inicio", "Fecha Fin"):
                df_limpio[col_fecha] = pd.to_datetime(
                    df_limpio[col_fecha], errors="coerce"
                )
        # Salida estandarizada: una sola fila de encabezado, sin indice,
        # sin celdas combinadas -> abre sin advertencias en Power Query/PBI.
        df_limpio.to_excel(self.archivo_salida, index=False, engine="openpyxl")
        print(
            f"[FSM] Proceso finalizado. Registros validos: {len(df_limpio)} | "
            f"Filas anomalas: {len(self.log_errores)} | "
            f"Filas de ruido ignoradas: {self.filas_ignoradas}"
        )


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else ENTRADA_PREDETERMINADA
    salida = sys.argv[2] if len(sys.argv) > 2 else SALIDA_PREDETERMINADA
    limpiador = LimpiadorInasistenciasFSM(entrada, salida)
    limpiador.ejecutar()
