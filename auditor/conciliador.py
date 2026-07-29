"""
Motor de conciliación: cruza los registros de dos lados (Proveeduría vs
Contabilidad) por número de documento y clasifica cada caso.

Salida: una lista de "líneas de conciliación" y un resumen agregado listos para
alimentar el dashboard.
"""

from collections import defaultdict

from . import config


def _tolerancia(monto_a, monto_b):
    """Tolerancia efectiva = máx(absoluta, relativa * mayor monto)."""
    base = max(abs(monto_a or 0), abs(monto_b or 0))
    return max(config.TOLERANCIA_ABSOLUTA, base * config.TOLERANCIA_RELATIVA)


def _agrupar_por_clave(registros):
    """Agrupa registros por su clave de documento. Ignora los sin clave."""
    grupos = defaultdict(list)
    sin_clave = []
    for r in registros:
        if r["clave"]:
            grupos[r["clave"]].append(r)
        else:
            sin_clave.append(r)
    return grupos, sin_clave


def _consolidar(regs):
    """Suma montos de registros con la misma clave y detecta duplicados."""
    monto = sum(r["monto"] for r in regs if r["monto"] is not None)
    return {
        "documento": regs[0]["documento"],
        "proveedor": next((r["proveedor"] for r in regs if r["proveedor"]), ""),
        "fecha": next((r["fecha"] for r in regs if r["fecha"]), ""),
        "monto": monto,
        "descripcion": next((r["descripcion"] for r in regs if r["descripcion"]), ""),
        "duplicado": len(regs) > 1,
        "n_lineas": len(regs),
    }


def conciliar(registros_a, registros_b,
              nombre_a=config.LADO_A, nombre_b=config.LADO_B):
    """
    Concilia dos conjuntos de registros por número de documento.

    Devuelve un dict con:
      - 'lineas': lista de líneas de conciliación (una por documento).
      - 'resumen': totales y conteos por estado.
      - 'sin_clave': registros que no tenían número de documento.
    """
    grupos_a, sin_clave_a = _agrupar_por_clave(registros_a)
    grupos_b, sin_clave_b = _agrupar_por_clave(registros_b)
    claves = sorted(set(grupos_a) | set(grupos_b))

    lineas = []
    for clave in claves:
        en_a = clave in grupos_a
        en_b = clave in grupos_b
        ca = _consolidar(grupos_a[clave]) if en_a else None
        cb = _consolidar(grupos_b[clave]) if en_b else None

        monto_a = ca["monto"] if ca else None
        monto_b = cb["monto"] if cb else None

        if en_a and en_b:
            diff = (monto_a or 0) - (monto_b or 0)
            if abs(diff) <= _tolerancia(monto_a, monto_b):
                estado = config.ESTADO_CONFIRMADO
            else:
                estado = config.ESTADO_VARIACION
        elif en_a:
            estado = config.ESTADO_SOLO_A
            diff = monto_a
        else:
            estado = config.ESTADO_SOLO_B
            diff = -(monto_b or 0)

        base = ca or cb
        duplicado = (ca and ca["duplicado"]) or (cb and cb["duplicado"])
        pct = None
        if monto_a not in (None, 0) and monto_b is not None:
            pct = (diff / monto_a) * 100

        lineas.append({
            "clave": clave,
            "documento": base["documento"],
            "proveedor": base["proveedor"],
            "fecha": base["fecha"],
            "descripcion": base["descripcion"],
            "monto_a": monto_a,
            "monto_b": monto_b,
            "diferencia": diff,
            "diferencia_pct": pct,
            "estado": estado,
            "duplicado": bool(duplicado),
        })

    resumen = _resumir(lineas, registros_a, registros_b,
                       sin_clave_a, sin_clave_b, nombre_a, nombre_b)
    return {
        "lineas": lineas,
        "resumen": resumen,
        "sin_clave": {"a": sin_clave_a, "b": sin_clave_b},
        "nombre_a": nombre_a,
        "nombre_b": nombre_b,
    }


def _resumir(lineas, registros_a, registros_b, sin_clave_a, sin_clave_b,
             nombre_a, nombre_b):
    conteo = defaultdict(int)
    monto_variacion = 0.0
    for ln in lineas:
        conteo[ln["estado"]] += 1
        if ln["estado"] == config.ESTADO_VARIACION:
            monto_variacion += abs(ln["diferencia"] or 0)

    total_a = sum(r["monto"] for r in registros_a if r["monto"] is not None)
    total_b = sum(r["monto"] for r in registros_b if r["monto"] is not None)

    n_conf = conteo[config.ESTADO_CONFIRMADO]
    total_docs = len(lineas)
    pct_conf = (n_conf / total_docs * 100) if total_docs else 0.0

    return {
        "nombre_a": nombre_a,
        "nombre_b": nombre_b,
        "total_documentos": total_docs,
        "registros_a": len(registros_a),
        "registros_b": len(registros_b),
        "confirmados": n_conf,
        "con_variacion": conteo[config.ESTADO_VARIACION],
        "solo_a": conteo[config.ESTADO_SOLO_A],
        "solo_b": conteo[config.ESTADO_SOLO_B],
        "duplicados": sum(1 for ln in lineas if ln["duplicado"]),
        "sin_clave_a": len(sin_clave_a),
        "sin_clave_b": len(sin_clave_b),
        "pct_conciliado": pct_conf,
        "monto_total_a": total_a,
        "monto_total_b": total_b,
        "diferencia_neta": total_a - total_b,
        "monto_en_variacion": monto_variacion,
    }
