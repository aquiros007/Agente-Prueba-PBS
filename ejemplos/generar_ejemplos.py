"""
Genera archivos de ejemplo para probar el auditor conciliador:

  - ejemplos/proveeduria.xlsx  (Excel, lado A)
  - ejemplos/contabilidad.pdf  (PDF con tabla, lado B)

Los dos usan encabezados y orden de columnas distintos a propósito, para
demostrar el mapeo robusto. Incluye casos de: confirmado, variación de monto,
faltante en cada lado y documento duplicado.
"""

import os

import openpyxl
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

AQUI = os.path.dirname(os.path.abspath(__file__))

# (documento, proveedor, fecha, monto_proveeduria, monto_contabilidad)
# None = no aparece en ese lado.
DATOS = [
    ("FAC-1001", "Suministros del Valle S.A.", "05/01/2026", 1250000.00, 1250000.00),  # confirmado
    ("FAC-1002", "Distribuidora Central",       "07/01/2026",  845300.50,  845300.50),  # confirmado
    ("FAC-1003", "Ferretería El Roble",         "09/01/2026",  432100.00,  432100.00),  # confirmado
    ("FAC-1004", "TecnoOficina CR",             "12/01/2026", 2100000.00, 2085000.00),  # variación
    ("FAC-1005", "Papelería Nacional",          "14/01/2026",  158900.00,  159400.00),  # variación pequeña -> dentro? no, 0.3%
    ("FAC-1006", "Transportes Rápidos",         "16/01/2026",  675000.00,       None),  # solo proveeduría
    ("FAC-1007", "Consultores Asociados",       "18/01/2026", 3400000.00,       None),  # solo proveeduría
    ("FAC-1008", "Servicios Generales Ltda.",   "20/01/2026",       None, 920000.00),   # solo contabilidad
    ("FAC-1009", "Importadora del Este",        "22/01/2026", 1875500.00, 1875500.00),  # confirmado
    ("FAC-1010", "Grupo Logístico CR",          "24/01/2026",  540000.00,  540000.75),  # confirmado (dentro de tolerancia)
    ("OC-2050",  "Equipos Médicos S.A.",        "26/01/2026", 4200000.00, 4200000.00),  # confirmado (orden de compra)
    ("OC-2051",  "Mobiliario Corporativo",      "28/01/2026",  980000.00,  998000.00),  # variación
]

# Duplicado en contabilidad: FAC-1002 dividido en dos líneas que suman igual.
DUPLICADO_CONTA = ("FAC-1002", "Distribuidora Central", "07/01/2026", 400000.50)


def generar_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Proveeduria"
    # Fila de título (ruido) para probar detección de encabezado.
    ws.append(["Departamento de Proveeduría - Registro de Compras Enero 2026"])
    ws.append([])
    # Encabezados propios de Proveeduría (orden y nombres distintos a Contabilidad).
    ws.append(["N° Orden/Factura", "Proveedor", "Fecha Emisión", "Detalle", "Monto Total"])
    for doc, prov, fecha, monto_a, _ in DATOS:
        if monto_a is None:
            continue
        ws.append([doc, prov, fecha, "Compra de bienes/servicios", monto_a])
    ruta = os.path.join(AQUI, "proveeduria.xlsx")
    wb.save(ruta)
    return ruta


def generar_pdf():
    ruta = os.path.join(AQUI, "contabilidad.pdf")
    doc = SimpleDocTemplate(ruta, pagesize=LETTER,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph("Departamento de Contabilidad", estilos["Title"]),
        Paragraph("Libro Auxiliar de Cuentas por Pagar — Enero 2026", estilos["Normal"]),
        Spacer(1, 0.6 * cm),
    ]

    # Encabezados propios de Contabilidad (distintos a Proveeduría).
    tabla = [["Comprobante", "Beneficiario", "Fecha Registro", "Importe (₡)"]]
    for doc_, prov, fecha, _, monto_b in DATOS:
        if monto_b is None:
            continue
        # FAC-1002 se parte en dos líneas (duplicado) que suman el total.
        if doc_ == "FAC-1002":
            tabla.append([doc_, prov, fecha, f"{DUPLICADO_CONTA[3]:,.2f}"])
            resto = monto_b - DUPLICADO_CONTA[3]
            tabla.append([doc_, prov, fecha, f"{resto:,.2f}"])
        else:
            tabla.append([doc_, prov, fecha, f"{monto_b:,.2f}"])

    t = Table(tabla, colWidths=[3 * cm, 6 * cm, 3.2 * cm, 3.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a78d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c3c2b7")),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(t)
    doc.build(elementos)
    return ruta


if __name__ == "__main__":
    rx = generar_excel()
    rp = generar_pdf()
    print(f"✓ Excel de Proveeduría : {rx}")
    print(f"✓ PDF de Contabilidad  : {rp}")
