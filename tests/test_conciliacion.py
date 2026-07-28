"""
Pruebas unitarias del auditor conciliador.

Ejecutar con:  python -m pytest tests/  (o)  python tests/test_conciliacion.py
No requiere pytest: si se ejecuta directo, corre un runner mínimo.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auditor import config
from auditor.utils import parsear_monto, normalizar_clave, normalizar_encabezado
from auditor.conciliador import conciliar


# --------------------------------------------------------------------------
# Parseo de montos
# --------------------------------------------------------------------------
def test_parsear_monto_latam():
    assert parsear_monto("1.234.567,89") == 1234567.89

def test_parsear_monto_us():
    assert parsear_monto("1,234,567.89") == 1234567.89

def test_parsear_monto_simbolo():
    assert parsear_monto("₡ 1.500,00") == 1500.00
    assert parsear_monto("$1,500.50") == 1500.50

def test_parsear_monto_negativo_parentesis():
    assert parsear_monto("(1.234,56)") == -1234.56

def test_parsear_monto_numerico():
    assert parsear_monto(2500) == 2500.0
    assert parsear_monto(2500.75) == 2500.75

def test_parsear_monto_invalido():
    assert parsear_monto("") is None
    assert parsear_monto("N/A") is None
    assert parsear_monto(None) is None

def test_parsear_monto_solo_coma_decimal():
    assert parsear_monto("1500,50") == 1500.50

def test_parsear_monto_solo_coma_miles():
    assert parsear_monto("1,500") == 1500.0


# --------------------------------------------------------------------------
# Normalización de clave de documento
# --------------------------------------------------------------------------
def test_clave_equivalentes():
    assert normalizar_clave("FAC-0001") == normalizar_clave("fac 0001")
    assert normalizar_clave("FAC-0001") == normalizar_clave("FAC0001")

def test_clave_vacia():
    assert normalizar_clave("") == ""
    assert normalizar_clave(None) == ""
    assert normalizar_clave("nan") == ""

def test_encabezado_con_tildes():
    assert normalizar_encabezado("Fecha Emisión") == "fecha emision"
    assert normalizar_encabezado("N° Factura") == "n factura"


# --------------------------------------------------------------------------
# Conciliación
# --------------------------------------------------------------------------
def _reg(doc, monto, prov="X"):
    return {
        "documento": doc, "clave": normalizar_clave(doc), "proveedor": prov,
        "fecha": "2026-01-01", "monto": monto, "descripcion": "",
        "_origen": "test", "_fila": 1,
    }

def test_confirmado():
    res = conciliar([_reg("F1", 1000)], [_reg("F1", 1000)])
    assert res["resumen"]["confirmados"] == 1
    assert res["lineas"][0]["estado"] == config.ESTADO_CONFIRMADO

def test_variacion():
    res = conciliar([_reg("F1", 1000)], [_reg("F1", 1200)])
    ln = res["lineas"][0]
    assert ln["estado"] == config.ESTADO_VARIACION
    assert ln["diferencia"] == -200

def test_dentro_de_tolerancia():
    # 0.3 % de diferencia -> dentro de la tolerancia relativa (0.5 %).
    res = conciliar([_reg("F1", 100000)], [_reg("F1", 100300)])
    assert res["lineas"][0]["estado"] == config.ESTADO_CONFIRMADO

def test_solo_a():
    res = conciliar([_reg("F1", 1000)], [])
    assert res["lineas"][0]["estado"] == config.ESTADO_SOLO_A
    assert res["resumen"]["solo_a"] == 1

def test_solo_b():
    res = conciliar([], [_reg("F1", 1000)])
    assert res["lineas"][0]["estado"] == config.ESTADO_SOLO_B
    assert res["resumen"]["solo_b"] == 1

def test_duplicado_se_suma():
    # F1 aparece dos veces en A y una vez en B; las dos de A suman el total de B.
    res = conciliar([_reg("F1", 600), _reg("F1", 400)], [_reg("F1", 1000)])
    ln = res["lineas"][0]
    assert ln["estado"] == config.ESTADO_CONFIRMADO
    assert ln["duplicado"] is True
    assert ln["monto_a"] == 1000

def test_diferencia_neta():
    res = conciliar([_reg("F1", 1000), _reg("F2", 500)], [_reg("F1", 1000)])
    assert res["resumen"]["diferencia_neta"] == 500
    assert res["resumen"]["monto_total_a"] == 1500
    assert res["resumen"]["monto_total_b"] == 1000

def test_sin_clave_no_cruza():
    res = conciliar([_reg("", 1000)], [_reg("", 1000)])
    assert res["resumen"]["total_documentos"] == 0
    assert res["resumen"]["sin_clave_a"] == 1
    assert res["resumen"]["sin_clave_b"] == 1


# --------------------------------------------------------------------------
# Runner mínimo sin pytest
# --------------------------------------------------------------------------
if __name__ == "__main__":
    pruebas = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fallos = 0
    for fn in pruebas:
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
        except AssertionError as e:
            fallos += 1
            print(f"  ✗ {fn.__name__}  ->  {e or 'assert falló'}")
    print(f"\n{len(pruebas) - fallos}/{len(pruebas)} pruebas OK")
    sys.exit(1 if fallos else 0)
