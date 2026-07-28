"""
Extracción de registros desde archivos Excel y PDF hacia el esquema canónico.

La estrategia es tolerante a estructuras distintas: cada departamento puede
entregar sus columnas con nombres y orden diferentes. Se detecta la fila de
encabezado y se mapean las columnas por sinónimos (ver config.SINONIMOS).
"""

import os

import openpyxl
import pdfplumber

from . import config
from .utils import (
    normalizar_encabezado,
    normalizar_clave,
    parsear_monto,
    parsear_fecha,
)


# ---------------------------------------------------------------------------
# Mapeo de columnas por sinónimos
# ---------------------------------------------------------------------------
def _mapear_columnas(encabezados):
    """
    Dada una lista de encabezados crudos, devuelve {campo_canonico: indice}.

    Se prioriza la coincidencia exacta del encabezado normalizado; si no la hay,
    se acepta coincidencia por 'contiene'. Un mismo índice no se asigna dos veces.
    """
    normalizados = [normalizar_encabezado(h) for h in encabezados]
    mapa = {}
    usados = set()

    for campo in config.CAMPOS_CANONICOS:
        sinonimos = config.SINONIMOS[campo]
        indice = None
        # 1) coincidencia exacta
        for i, h in enumerate(normalizados):
            if i in usados or not h:
                continue
            if h in sinonimos:
                indice = i
                break
        # 2) coincidencia por contención (encabezado contiene el sinónimo o viceversa)
        if indice is None:
            for i, h in enumerate(normalizados):
                if i in usados or not h:
                    continue
                if any(
                    (s in h or h in s) and len(s) >= 3 for s in sinonimos
                ):
                    indice = i
                    break
        if indice is not None:
            mapa[campo] = indice
            usados.add(indice)
    return mapa


def _fila_a_registro(fila, mapa, origen, fila_num):
    """Convierte una fila cruda (lista) en un registro canónico o None."""
    def val(campo):
        idx = mapa.get(campo)
        if idx is None or idx >= len(fila):
            return None
        return fila[idx]

    documento_raw = val("documento")
    clave = normalizar_clave(documento_raw)
    monto = parsear_monto(val("monto"))

    # Se descartan filas sin documento y sin monto (probablemente vacías o totales).
    if not clave and monto is None:
        return None

    return {
        "documento": str(documento_raw).strip() if documento_raw is not None else "",
        "clave": clave,
        "proveedor": (str(val("proveedor")).strip() if val("proveedor") is not None else ""),
        "fecha": parsear_fecha(val("fecha")),
        "monto": monto,
        "descripcion": (str(val("descripcion")).strip() if val("descripcion") is not None else ""),
        "_origen": origen,
        "_fila": fila_num,
    }


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def extraer_excel(ruta):
    """
    Lee la primera hoja con datos de un archivo .xlsx y devuelve una lista de
    registros canónicos. Detecta automáticamente la fila de encabezado.
    """
    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    registros = []
    origen = os.path.basename(ruta)

    for ws in wb.worksheets:
        filas = [
            list(fila)
            for fila in ws.iter_rows(values_only=True)
            if fila is not None and any(c is not None and str(c).strip() != "" for c in fila)
        ]
        if not filas:
            continue

        # Buscar la fila de encabezado en las primeras 15 filas: la que mejor
        # mapee a nuestros campos canónicos (al menos documento o monto).
        mejor_idx, mejor_mapa, mejor_puntaje = None, {}, 0
        for i, fila in enumerate(filas[:15]):
            encabezados = [c if c is not None else "" for c in fila]
            mapa = _mapear_columnas(encabezados)
            puntaje = len(mapa)
            if ("documento" in mapa or "monto" in mapa) and puntaje > mejor_puntaje:
                mejor_idx, mejor_mapa, mejor_puntaje = i, mapa, puntaje

        if mejor_idx is None:
            continue  # esta hoja no parece tener datos conciliables

        for j, fila in enumerate(filas[mejor_idx + 1:], start=mejor_idx + 2):
            reg = _fila_a_registro(fila, mejor_mapa, origen, j)
            if reg:
                registros.append(reg)
        if registros:
            break  # usamos la primera hoja que produjo registros

    wb.close()
    return registros


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def extraer_pdf(ruta):
    """
    Extrae registros de un PDF. Primero intenta detectar tablas; si no hay
    tablas utilizables, cae a un parseo por texto línea a línea.
    """
    origen = os.path.basename(ruta)
    registros = []

    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables() or []
            usó_tabla = False
            for tabla in tablas:
                filas = [
                    [("" if c is None else str(c).strip()) for c in fila]
                    for fila in tabla
                    if fila is not None and any(c not in (None, "") for c in fila)
                ]
                if len(filas) < 2:
                    continue
                # Buscar encabezado dentro de la tabla.
                idx_enc, mapa = None, {}
                for i, fila in enumerate(filas[:5]):
                    m = _mapear_columnas(fila)
                    if "documento" in m or "monto" in m:
                        idx_enc, mapa = i, m
                        break
                if idx_enc is None:
                    continue
                for j, fila in enumerate(filas[idx_enc + 1:], start=idx_enc + 2):
                    reg = _fila_a_registro(fila, mapa, origen, j)
                    if reg:
                        registros.append(reg)
                        usó_tabla = True

            # Fallback por texto si la página no aportó registros por tabla.
            if not usó_tabla:
                texto = pagina.extract_text() or ""
                registros.extend(_parsear_texto_pdf(texto, origen))

    return registros


def _parsear_texto_pdf(texto, origen):
    """
    Parseo de respaldo: busca líneas con un código de documento y un monto.

    Patrón típico de línea de factura:
        FAC-0001  Proveedor XYZ  25/01/2026  ₡1.234.567,89
    Se toma el primer token tipo código como documento y el último número
    con formato monetario como monto.
    """
    import re

    registros = []
    patron_monto = re.compile(r"[₡$]?\s?\d[\d.,]*\d")
    patron_codigo = re.compile(r"\b[A-Z]{1,5}[- ]?\d{2,}\b|\b\d{4,}\b")

    for linea in texto.splitlines():
        l = linea.strip()
        if not l:
            continue
        cod = patron_codigo.search(l)
        montos = patron_monto.findall(l)
        if not cod or not montos:
            continue
        monto = parsear_monto(montos[-1])
        clave = normalizar_clave(cod.group())
        if not clave or monto is None:
            continue
        # Proveedor aproximado: texto entre el código y el primer número.
        resto = l[cod.end():].strip()
        prov = re.split(r"\d", resto, 1)[0].strip(" -\t") if resto else ""
        registros.append({
            "documento": cod.group().strip(),
            "clave": clave,
            "proveedor": prov,
            "fecha": "",
            "monto": monto,
            "descripcion": "",
            "_origen": origen,
            "_fila": None,
        })
    return registros


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
def extraer(ruta):
    """Extrae registros según la extensión del archivo (.xlsx/.xls o .pdf)."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        return extraer_excel(ruta)
    if ext == ".pdf":
        return extraer_pdf(ruta)
    raise ValueError(
        f"Formato no soportado: '{ext}'. Use archivos .xlsx o .pdf."
    )
