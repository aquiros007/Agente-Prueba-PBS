"""
Aplicación web del Auditor Conciliador.

Página con dos zonas de carga:
  - Proveeduría sube la Orden de Compra (Excel o PDF).
  - Recibo sube la Factura (Excel o PDF).

Al enviar, se ejecuta el motor de conciliación (mismo código del CLI) y se
muestra el dashboard comparativo directamente en el navegador.

Ejecutar:
    python app.py
Luego abrir en el navegador:  http://localhost:5000
"""

import os
import tempfile

from flask import Flask, request, render_template, Response
from werkzeug.utils import secure_filename

from auditor.extractores import extraer
from auditor.conciliador import conciliar
from auditor.dashboard import generar_html

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB por archivo

EXTENSIONES_OK = {".xlsx", ".xlsm", ".xls", ".pdf"}


def _extension_valida(nombre):
    return os.path.splitext(nombre)[1].lower() in EXTENSIONES_OK


def _guardar_temporal(archivo):
    """Guarda el archivo subido en una ruta temporal conservando la extensión."""
    nombre = secure_filename(archivo.filename) or "archivo"
    ext = os.path.splitext(nombre)[1].lower()
    fd, ruta = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    archivo.save(ruta)
    return ruta


@app.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")


@app.route("/conciliar", methods=["POST"])
def conciliar_web():
    arch_a = request.files.get("proveeduria")
    arch_b = request.files.get("recibo")
    nombre_a = (request.form.get("nombre_a") or "Proveeduría").strip()
    nombre_b = (request.form.get("nombre_b") or "Recibo").strip()
    titulo = (request.form.get("titulo") or "Comparativo Orden de Compra vs Factura").strip()

    faltantes = []
    if not arch_a or not arch_a.filename:
        faltantes.append("la Orden de Compra (Proveeduría)")
    if not arch_b or not arch_b.filename:
        faltantes.append("la Factura (Recibo)")
    if faltantes:
        return _pagina_error(
            "Falta cargar " + " y ".join(faltantes) + ".",
            "Regresa y adjunta ambos archivos (Excel o PDF) antes de conciliar."
        )

    for archivo, etiqueta in ((arch_a, "Orden de Compra"), (arch_b, "Factura")):
        if not _extension_valida(archivo.filename):
            return _pagina_error(
                f"El archivo de {etiqueta} no tiene un formato soportado.",
                "Solo se aceptan archivos Excel (.xlsx) o PDF (.pdf)."
            )

    ruta_a = ruta_b = None
    try:
        ruta_a = _guardar_temporal(arch_a)
        ruta_b = _guardar_temporal(arch_b)
        reg_a = extraer(ruta_a)
        reg_b = extraer(ruta_b)

        if not reg_a and not reg_b:
            return _pagina_error(
                "No se pudo leer información conciliable de los archivos.",
                "Verifica que cada archivo tenga columnas de número de documento "
                "(factura/OC) y de monto."
            )

        resultado = conciliar(reg_a, reg_b, nombre_a, nombre_b)
        html = generar_html(resultado, titulo)
        html = _inyectar_barra_volver(html)
        return Response(html, mimetype="text/html")
    except Exception as e:  # noqa: BLE001 - se muestra un error legible al usuario
        return _pagina_error(
            "Ocurrió un error al procesar los archivos.",
            f"Detalle técnico: {e}"
        )
    finally:
        for ruta in (ruta_a, ruta_b):
            if ruta and os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    pass


def _inyectar_barra_volver(html):
    """Agrega un botón flotante 'Nueva conciliación' al dashboard generado."""
    barra = (
        '<a href="/" style="position:fixed;top:16px;right:18px;z-index:99;'
        'font:600 13px system-ui,sans-serif;text-decoration:none;padding:8px 14px;'
        'border-radius:20px;background:#2a78d6;color:#fff;'
        'box-shadow:0 2px 8px rgba(0,0,0,.2)">↻ Nueva conciliación</a>'
    )
    return html.replace("</body>", barra + "</body>", 1)


def _pagina_error(titulo, detalle):
    cuerpo = render_template("error.html", titulo=titulo, detalle=detalle)
    return Response(cuerpo, mimetype="text/html", status=400)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print(f"\n  Auditor Conciliador — abre http://localhost:{puerto} en tu navegador\n")
    app.run(host="0.0.0.0", port=puerto, debug=False)
