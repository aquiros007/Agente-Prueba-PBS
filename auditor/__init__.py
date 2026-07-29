"""
Auditor Conciliador Excel/PDF.

Cruza documentos de Proveeduría y Contabilidad (Excel o PDF) por número de
documento/factura y genera un dashboard HTML con confirmaciones y variaciones.
"""

from .extractores import extraer
from .conciliador import conciliar
from .dashboard import generar_html

__all__ = ["extraer", "conciliar", "generar_html"]
__version__ = "1.0.0"
