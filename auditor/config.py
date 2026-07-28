"""
Configuración central del auditor conciliador.

Aquí se definen:
 - Los sinónimos de columnas (para mapear encabezados de Excel/PDF a un esquema
   canónico sin importar cómo los nombre cada departamento).
 - Las tolerancias de comparación de montos.
 - Etiquetas de estado de conciliación.

Todo está en español porque los documentos provienen de Proveeduría y
Contabilidad (contexto Costa Rica / LatAm).
"""

# ---------------------------------------------------------------------------
# Esquema canónico
# ---------------------------------------------------------------------------
# Cada registro extraído (venga de Excel o PDF) se normaliza a estos campos.
CAMPOS_CANONICOS = ["documento", "proveedor", "fecha", "monto", "descripcion"]

# Sinónimos de encabezados. La detección es tolerante a mayúsculas, tildes y
# espacios: el encabezado real se normaliza y se busca por coincidencia parcial.
SINONIMOS = {
    "documento": [
        "documento", "no documento", "n documento", "nro documento",
        "num documento", "numero documento", "factura", "no factura",
        "n factura", "nro factura", "num factura", "numero factura",
        "no fac", "fac", "comprobante", "no comprobante",
        "oc", "no oc", "orden", "orden de compra", "no orden",
        "consecutivo", "referencia", "ref", "id", "doc", "folio",
    ],
    "proveedor": [
        "proveedor", "suplidor", "beneficiario", "nombre proveedor",
        "razon social", "nombre", "vendor", "acreedor", "cliente",
    ],
    "fecha": [
        "fecha", "fecha factura", "fecha emision", "fecha documento",
        "fecha de emision", "emision", "date", "fecha registro",
    ],
    "monto": [
        "monto", "monto total", "total", "importe", "valor", "monto neto",
        "amount", "subtotal", "total factura", "monto factura",
        "total a pagar", "gran total", "valor total",
    ],
    "descripcion": [
        "descripcion", "detalle", "concepto", "glosa", "description",
        "observaciones", "observacion", "detalle documento",
    ],
}

# ---------------------------------------------------------------------------
# Parámetros de conciliación
# ---------------------------------------------------------------------------
# Tolerancia absoluta (en unidades de la moneda) para considerar dos montos
# "iguales". Se toma el mayor entre la tolerancia absoluta y la relativa.
TOLERANCIA_ABSOLUTA = 0.01
# Tolerancia relativa (fracción del monto). 0.005 = 0.5 %.
TOLERANCIA_RELATIVA = 0.005

# ---------------------------------------------------------------------------
# Estados de conciliación
# ---------------------------------------------------------------------------
ESTADO_CONFIRMADO = "CONFIRMADO"          # existe en ambos y los montos cuadran
ESTADO_VARIACION = "VARIACION_MONTO"      # existe en ambos pero difieren montos
ESTADO_SOLO_A = "SOLO_PROVEEDURIA"        # solo en el lado A
ESTADO_SOLO_B = "SOLO_CONTABILIDAD"       # solo en el lado B
ESTADO_DUPLICADO = "DUPLICADO"            # documento repetido dentro de un lado

# Etiquetas legibles para el dashboard.
ETIQUETAS_ESTADO = {
    ESTADO_CONFIRMADO: "Confirmado",
    ESTADO_VARIACION: "Con variación",
    ESTADO_SOLO_A: "Solo en Proveeduría",
    ESTADO_SOLO_B: "Solo en Contabilidad",
    ESTADO_DUPLICADO: "Documento duplicado",
}

# Nombres por defecto de los dos lados de la conciliación.
LADO_A = "Proveeduría"
LADO_B = "Contabilidad"
