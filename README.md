# Auditor Conciliador Excel ↔ PDF

Herramienta de auditoría que **recibe documentos en Excel y en PDF**, **concilia**
la información de ambos por número de documento (factura / orden de compra) y
entrega un **dashboard HTML** con las **confirmaciones** y las **variaciones**
encontradas.

Pensada para cruzar documentos que provienen de dos áreas —por ejemplo
**Proveeduría** y **Contabilidad**— sin importar que cada departamento entregue
sus archivos con columnas, nombres y formatos distintos.

---

## ¿Qué hace?

1. **Lee** un archivo por cada lado. Cada lado puede ser **Excel (`.xlsx`)** o
   **PDF (`.pdf`)**, indistintamente.
2. **Detecta las columnas** automáticamente (número de documento, proveedor,
   fecha, monto, descripción) aunque los encabezados varíen, tengan tildes o
   estén en otro orden.
3. **Cruza por número de documento** (`FAC-1001`, `OC-2050`, etc.), tolerante a
   guiones, espacios y mayúsculas (`FAC-0001` = `fac 0001` = `FAC0001`).
4. **Clasifica** cada documento en:
   - ✓ **Confirmado** — existe en ambos y los montos cuadran.
   - ≠ **Con variación** — existe en ambos pero los montos difieren.
   - ◄ **Solo en Proveeduría** — falta en Contabilidad.
   - ► **Solo en Contabilidad** — falta en Proveeduría.
   - ⚑ **Duplicado** — el mismo documento aparece varias veces en un lado (los
     montos se suman y se marca para revisión).
5. **Genera un dashboard HTML** autocontenido (se abre en cualquier navegador,
   sin internet) con indicadores clave, distribución por estado y una tabla de
   detalle filtrable y ordenable.

---

## Instalación

```bash
pip install -r requirements.txt
```

Dependencias: `openpyxl` (Excel), `pdfplumber` (PDF), `Flask` (app web) y
`reportlab` (solo para generar los archivos de ejemplo).

---

## App web — carga de documentos (recomendado)

Página con **dos zonas de carga** donde cada área sube su documento y el
comparativo se genera solo:

- **Proveeduría** carga la **Orden de Compra** (Excel o PDF).
- **Recibo** carga la **Factura** (Excel o PDF).

```bash
python app.py
```

Luego abre **http://localhost:5000** en el navegador, arrastra los dos archivos
y presiona **“Conciliar y ver comparativo”**. Se muestra el dashboard con las
confirmaciones y variaciones.

Para que todo el equipo la use desde sus navegadores, basta con dejar `app.py`
corriendo en una computadora/servidor de la red; los demás entran a
`http://IP-DEL-SERVIDOR:5000`. Los archivos se procesan en memoria y no se
almacenan.

> Variable de entorno opcional: `PORT` para cambiar el puerto (por defecto 5000).

---

## Uso por línea de comandos (CLI)

Alternativa sin navegador, útil para automatizar:

```bash
python -m auditor.cli \
  --proveeduria  ruta/al/archivo_proveeduria.xlsx \
  --contabilidad ruta/al/archivo_contabilidad.pdf \
  --salida       output/dashboard.html
```

Cada lado acepta Excel **o** PDF. Los roles son intercambiables: si Proveeduría
manda PDF y Contabilidad manda Excel, solo se invierten las rutas.

### Opciones

| Opción | Descripción | Por defecto |
|--------|-------------|-------------|
| `-p`, `--proveeduria` | Archivo del lado A (`.xlsx` o `.pdf`). **Requerido.** | — |
| `-c`, `--contabilidad` | Archivo del lado B (`.xlsx` o `.pdf`). **Requerido.** | — |
| `-o`, `--salida` | Ruta del dashboard HTML de salida. | `output/dashboard.html` |
| `-t`, `--titulo` | Título del dashboard. | `Auditoría de Conciliación` |
| `--nombre-a` | Etiqueta del lado A. | `Proveeduría` |
| `--nombre-b` | Etiqueta del lado B. | `Contabilidad` |
| `--json` | Exporta también el resultado en JSON a la ruta indicada. | — |

---

## Prueba rápida con datos de ejemplo

```bash
# 1) Genera un Excel (Proveeduría) y un PDF (Contabilidad) de muestra
python ejemplos/generar_ejemplos.py

# 2) Concilia y genera el dashboard
python -m auditor.cli \
  -p ejemplos/proveeduria.xlsx \
  -c ejemplos/contabilidad.pdf \
  -o output/dashboard.html

# 3) Abre output/dashboard.html en tu navegador
```

Los archivos de ejemplo usan **encabezados y orden de columnas distintos** entre
sí a propósito, e incluyen casos de confirmación, variación, faltantes en cada
lado y un documento duplicado, para mostrar todo el comportamiento.

---

## Cómo se ven tus documentos (recomendado)

La herramienta reconoce muchos nombres de columna en español, pero funciona
mejor si cada archivo tiene, como mínimo, una columna de **número de documento**
y una de **monto**. Sinónimos reconocidos (parcial):

- **Documento:** `N° Factura`, `No Factura`, `Comprobante`, `OC`, `Orden de compra`, `Consecutivo`, `Referencia`, `Folio`…
- **Proveedor:** `Proveedor`, `Suplidor`, `Beneficiario`, `Razón social`…
- **Fecha:** `Fecha`, `Fecha emisión`, `Fecha documento`…
- **Monto:** `Monto`, `Total`, `Importe`, `Valor`, `Monto total`…

Se puede ampliar esta lista en `auditor/config.py` (`SINONIMOS`).

### Montos y tolerancia

Se interpretan formatos `₡1.234.567,89` (LatAm), `$1,234,567.89` (US), negativos
entre paréntesis y símbolos de moneda. Dos montos se consideran iguales si su
diferencia es menor a la **tolerancia** (máx. entre `₡0.01` y `0.5 %` del monto),
configurable en `auditor/config.py`.

---

## Estructura del proyecto

```
app.py              App web (Flask): página de carga + comparativo
templates/
  index.html        Página con las dos zonas de carga (Proveeduría / Recibo)
  error.html        Página de aviso ante archivos faltantes o inválidos
auditor/
  config.py         Sinónimos de columnas, tolerancias, estados
  utils.py          Normalización de texto, montos, fechas y claves
  extractores.py    Lectura de Excel y PDF -> registros canónicos
  conciliador.py    Motor de cruce y clasificación por documento
  dashboard.py      Generación del dashboard HTML autocontenido
  cli.py            Interfaz de línea de comandos
ejemplos/
  generar_ejemplos.py   Crea proveeduria.xlsx y contabilidad.pdf de muestra
tests/
  test_conciliacion.py  Pruebas unitarias (19)
```

---

## Pruebas

```bash
python tests/test_conciliacion.py        # runner integrado, sin pytest
# o, si tienes pytest:
python -m pytest tests/
```

---

## Limitaciones y notas

- La extracción de **PDF** funciona mejor con **tablas** (texto seleccionable).
  Para PDF escaneados (imagen) haría falta OCR, que no está incluido.
- El cruce es por **número de documento**. Si un lado no trae ese número, esos
  registros se reportan aparte como "sin número de documento" y no se cruzan.
- Todos los resultados con variación o faltantes están pensados como **señal de
  revisión manual**, no como conclusión contable definitiva.
