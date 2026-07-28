"""Utilidades de normalización de texto, montos, fechas y claves de cruce."""

import re
import unicodedata
from datetime import datetime, date


def quitar_tildes(texto: str) -> str:
    """Elimina tildes/diacríticos para comparar encabezados de forma robusta."""
    if texto is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_encabezado(texto: str) -> str:
    """Normaliza un encabezado: sin tildes, minúsculas, espacios colapsados."""
    t = quitar_tildes(texto).lower().strip()
    t = re.sub(r"[°º#:.\-_/]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def normalizar_clave(valor) -> str:
    """
    Genera la clave de cruce a partir del número de documento/factura/OC.

    Se eliminan espacios y separadores y se pasa a mayúsculas para que
    'FAC-0001', 'fac 0001' y 'FAC0001' se traten como el mismo documento.
    Devuelve '' si no hay valor utilizable.
    """
    if valor is None:
        return ""
    s = str(valor).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return ""
    s = quitar_tildes(s).upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def parsear_monto(valor):
    """
    Convierte un valor a float manejando formatos LatAm/US y símbolos.

    Soporta '1.234,56' (europeo/LatAm), '1,234.56' (US), '₡1 234,50',
    '$1,234.56', paréntesis para negativos '(1.234,56)' y valores ya numéricos.
    Devuelve None si no se puede interpretar.
    """
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        try:
            f = float(valor)
            return f if f == f else None  # descarta NaN
        except (ValueError, TypeError):
            return None

    s = str(valor).strip()
    if s == "":
        return None

    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo = True
        s = s[1:-1]

    # Quitar símbolos de moneda y espacios (incluye separador de miles con espacio).
    s = re.sub(r"[₡$€£\s]", "", s)
    s = s.replace("CRC", "").replace("USD", "").replace("crc", "").replace("usd", "")
    if s.startswith("-"):
        negativo = True
        s = s[1:]

    if s == "" or not re.search(r"\d", s):
        return None

    tiene_coma = "," in s
    tiene_punto = "." in s

    if tiene_coma and tiene_punto:
        # El separador decimal es el que aparece de último.
        if s.rfind(",") > s.rfind("."):
            # formato LatAm: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            # formato US: 1,234.56
            s = s.replace(",", "")
    elif tiene_coma:
        # Solo coma. Si hay exactamente 2 decimales -> decimal; si no -> miles.
        partes = s.split(",")
        if len(partes) == 2 and len(partes[1]) in (1, 2):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    # Solo punto o solo dígitos: dejar tal cual.

    try:
        f = float(s)
    except ValueError:
        return None
    return -f if negativo else f


def parsear_fecha(valor):
    """Devuelve una fecha ISO (YYYY-MM-DD) o el texto original si no se logra."""
    if valor is None:
        return ""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")
    s = str(valor).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return ""
    formatos = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y",
        "%Y/%m/%d", "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s  # se conserva el texto original como referencia


def formato_moneda(valor, simbolo="₡") -> str:
    """Formatea un número como moneda legible (separador de miles)."""
    if valor is None:
        return "-"
    try:
        return f"{simbolo}{valor:,.2f}"
    except (ValueError, TypeError):
        return str(valor)
