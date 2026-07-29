"""
Interfaz de línea de comandos del auditor conciliador.

Uso típico:
    python -m auditor.cli \\
        --proveeduria docs/proveeduria.xlsx \\
        --contabilidad docs/contabilidad.pdf \\
        --salida output/dashboard.html

Cada lado admite Excel (.xlsx) o PDF (.pdf) indistintamente.
"""

import argparse
import json
import os
import sys

from . import config
from .extractores import extraer
from .conciliador import conciliar
from .dashboard import generar_html


def _log(msg):
    print(msg, file=sys.stderr)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="auditor",
        description="Concilia documentos de Proveeduría y Contabilidad "
                    "(Excel/PDF) y genera un dashboard HTML.",
    )
    p.add_argument("--proveeduria", "-p", required=True,
                   help="Archivo del lado A (Proveeduría). .xlsx o .pdf")
    p.add_argument("--contabilidad", "-c", required=True,
                   help="Archivo del lado B (Contabilidad). .xlsx o .pdf")
    p.add_argument("--salida", "-o", default="output/dashboard.html",
                   help="Ruta del dashboard HTML de salida.")
    p.add_argument("--titulo", "-t", default="Auditoría de Conciliación",
                   help="Título del dashboard.")
    p.add_argument("--nombre-a", default=config.LADO_A,
                   help="Etiqueta del lado A (por defecto: Proveeduría).")
    p.add_argument("--nombre-b", default=config.LADO_B,
                   help="Etiqueta del lado B (por defecto: Contabilidad).")
    p.add_argument("--json", dest="json_out", default=None,
                   help="Ruta opcional para exportar el resultado en JSON.")
    args = p.parse_args(argv)

    for etiqueta, ruta in (("Proveeduría", args.proveeduria),
                           ("Contabilidad", args.contabilidad)):
        if not os.path.isfile(ruta):
            _log(f"ERROR: no se encontró el archivo de {etiqueta}: {ruta}")
            return 2

    _log(f"→ Leyendo {args.nombre_a}: {args.proveeduria}")
    reg_a = extraer(args.proveeduria)
    _log(f"  {len(reg_a)} registro(s) extraído(s).")

    _log(f"→ Leyendo {args.nombre_b}: {args.contabilidad}")
    reg_b = extraer(args.contabilidad)
    _log(f"  {len(reg_b)} registro(s) extraído(s).")

    if not reg_a and not reg_b:
        _log("ERROR: no se extrajeron registros de ninguno de los archivos. "
             "Verifique que tengan columnas de documento y monto.")
        return 1

    _log("→ Conciliando por número de documento…")
    resultado = conciliar(reg_a, reg_b, args.nombre_a, args.nombre_b)
    r = resultado["resumen"]

    _log(f"  {r['total_documentos']} documentos cruzados · "
         f"{r['confirmados']} confirmados · "
         f"{r['con_variacion']} con variación · "
         f"{r['solo_a']} solo {args.nombre_a} · "
         f"{r['solo_b']} solo {args.nombre_b}.")

    salida_dir = os.path.dirname(os.path.abspath(args.salida))
    os.makedirs(salida_dir, exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as f:
        f.write(generar_html(resultado, args.titulo))
    _log(f"✓ Dashboard generado: {args.salida}")

    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".",
                    exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(
                {"resumen": resultado["resumen"], "lineas": resultado["lineas"]},
                f, ensure_ascii=False, indent=2, default=str,
            )
        _log(f"✓ Resultado JSON exportado: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
