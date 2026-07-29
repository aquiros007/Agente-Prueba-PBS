"""
Generación del dashboard HTML de conciliación (archivo autocontenido).

El HTML no depende de recursos externos: CSS y JS embebidos, compatible con
tema claro/oscuro. Los colores de estado siguen la paleta validada de estado
(good/warning/serious/critical) y siempre se acompañan de ícono + etiqueta,
de modo que el significado nunca depende solo del color.
"""

import html
import json
from datetime import datetime

from . import config
from .utils import formato_moneda

# Colores de estado (paleta validada) + ícono, para no depender solo del color.
ESTILO_ESTADO = {
    config.ESTADO_CONFIRMADO: {"color": "#0ca30c", "icono": "✓"},
    config.ESTADO_VARIACION:  {"color": "#fab219", "icono": "≠"},
    config.ESTADO_SOLO_A:     {"color": "#ec835a", "icono": "◄"},
    config.ESTADO_SOLO_B:     {"color": "#d03b3b", "icono": "►"},
}


def _esc(v):
    return html.escape("" if v is None else str(v))


def _fmt(v):
    return formato_moneda(v) if v is not None else "—"


def _kpi(valor, etiqueta, sub="", acento=None):
    color = f"color:{acento};" if acento else ""
    return f"""
      <div class="kpi">
        <div class="kpi-val" style="{color}">{valor}</div>
        <div class="kpi-lab">{_esc(etiqueta)}</div>
        <div class="kpi-sub">{_esc(sub)}</div>
      </div>"""


def _barras_estado(resumen):
    """Barras horizontales con la distribución por estado (magnitud = conteo)."""
    datos = [
        (config.ESTADO_CONFIRMADO, resumen["confirmados"]),
        (config.ESTADO_VARIACION, resumen["con_variacion"]),
        (config.ESTADO_SOLO_A, resumen["solo_a"]),
        (config.ESTADO_SOLO_B, resumen["solo_b"]),
    ]
    total = max(sum(n for _, n in datos), 1)
    filas = ""
    for estado, n in datos:
        est = ESTILO_ESTADO[estado]
        pct = n / total * 100
        etiqueta = config.ETIQUETAS_ESTADO[estado]
        filas += f"""
        <div class="bar-row" title="{_esc(etiqueta)}: {n}">
          <div class="bar-lab"><span class="dot" style="background:{est['color']}"></span>{est['icono']} {_esc(etiqueta)}</div>
          <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{est['color']}"></div></div>
          <div class="bar-num">{n}</div>
        </div>"""
    return filas


def _fila_tabla(ln):
    est = ESTILO_ESTADO[ln["estado"]]
    etiqueta = config.ETIQUETAS_ESTADO[ln["estado"]]
    chip = (f'<span class="chip" style="--c:{est["color"]}">'
            f'{est["icono"]} {_esc(etiqueta)}</span>')
    dup = ' <span class="chip dup">⚑ dup</span>' if ln["duplicado"] else ""
    pct = f'{ln["diferencia_pct"]:+.1f}%' if ln["diferencia_pct"] is not None else "—"
    diff = ln["diferencia"]
    diff_cls = "num pos" if (diff or 0) > 0 else ("num neg" if (diff or 0) < 0 else "num")
    return f"""
      <tr data-estado="{ln['estado']}">
        <td>{_esc(ln['documento'])}{dup}</td>
        <td>{_esc(ln['proveedor'])}</td>
        <td>{_esc(ln['fecha'])}</td>
        <td class="num">{_fmt(ln['monto_a'])}</td>
        <td class="num">{_fmt(ln['monto_b'])}</td>
        <td class="{diff_cls}">{_fmt(diff)}</td>
        <td class="num">{pct}</td>
        <td>{chip}</td>
      </tr>"""


def generar_html(resultado, titulo="Auditoría de Conciliación"):
    r = resultado["resumen"]
    lineas = resultado["lineas"]
    na, nb = resultado["nombre_a"], resultado["nombre_b"]

    # Orden: primero lo que requiere atención (variaciones y faltantes).
    prioridad = {
        config.ESTADO_VARIACION: 0,
        config.ESTADO_SOLO_A: 1,
        config.ESTADO_SOLO_B: 2,
        config.ESTADO_CONFIRMADO: 3,
    }
    lineas_ord = sorted(
        lineas,
        key=lambda x: (prioridad.get(x["estado"], 9), -abs(x["diferencia"] or 0)),
    )
    filas = "".join(_fila_tabla(ln) for ln in lineas_ord)

    dif_neta = r["diferencia_neta"]
    acento_dif = "#0ca30c" if abs(dif_neta) < 0.01 else "#d03b3b"
    pct = r["pct_conciliado"]
    acento_pct = "#0ca30c" if pct >= 95 else ("#fab219" if pct >= 80 else "#d03b3b")

    # Botones de filtro de la tabla.
    botones = '<button class="fbtn activo" data-f="TODOS">Todos</button>'
    for estado in (config.ESTADO_VARIACION, config.ESTADO_SOLO_A,
                   config.ESTADO_SOLO_B, config.ESTADO_CONFIRMADO):
        est = ESTILO_ESTADO[estado]
        botones += (f'<button class="fbtn" data-f="{estado}">'
                    f'<span class="dot" style="background:{est["color"]}"></span>'
                    f'{config.ETIQUETAS_ESTADO[estado]}</button>')

    alertas = ""
    if r["sin_clave_a"] or r["sin_clave_b"]:
        alertas += (f'<div class="alerta">⚠ {r["sin_clave_a"]} registro(s) en '
                    f'{_esc(na)} y {r["sin_clave_b"]} en {_esc(nb)} '
                    f'no tienen número de documento y no se pudieron cruzar.</div>')
    if r["duplicados"]:
        alertas += (f'<div class="alerta">⚑ {r["duplicados"]} documento(s) '
                    f'aparecen duplicados dentro de un mismo lado (montos sumados).</div>')

    generado = datetime.now().strftime("%d/%m/%Y %H:%M")

    return _PLANTILLA.format(
        titulo=_esc(titulo),
        na=_esc(na), nb=_esc(nb),
        generado=generado,
        kpi_docs=_kpi(r["total_documentos"], "Documentos cruzados",
                      f'{r["registros_a"]} en {na} · {r["registros_b"]} en {nb}'),
        kpi_conf=_kpi(f'{pct:.0f}%', "Conciliado",
                      f'{r["confirmados"]} confirmados', acento_pct),
        kpi_var=_kpi(r["con_variacion"], "Con variación",
                     _fmt(r["monto_en_variacion"]) + " en diferencias",
                     "#fab219" if r["con_variacion"] else None),
        kpi_falt=_kpi(r["solo_a"] + r["solo_b"], "Faltantes",
                      f'{r["solo_a"]} solo {na} · {r["solo_b"]} solo {nb}',
                      "#d03b3b" if (r["solo_a"] + r["solo_b"]) else None),
        kpi_ta=_kpi(_fmt(r["monto_total_a"]), f"Monto {na}"),
        kpi_tb=_kpi(_fmt(r["monto_total_b"]), f"Monto {nb}"),
        kpi_dif=_kpi(_fmt(dif_neta), "Diferencia neta",
                     "cuadra" if abs(dif_neta) < 0.01 else "descuadre", acento_dif),
        barras=_barras_estado(r),
        alertas=alertas,
        botones=botones,
        filas=filas,
        col_a=_esc(na), col_b=_esc(nb),
    )


_PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
  :root {{
    color-scheme: light dark;
    --plane:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e;
    --muted:#898781; --grid:#e1e0d9; --line:#c3c2b7; --ring:rgba(11,11,11,.10);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --plane:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7;
      --muted:#898781; --grid:#2c2c2a; --line:#383835; --ring:rgba(255,255,255,.10);
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--plane); color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",sans-serif; line-height:1.45; }}
  .wrap {{ max-width:1200px; margin:0 auto; padding:28px 20px 60px; }}
  header h1 {{ font-size:22px; margin:0 0 4px; }}
  header .sub {{ color:var(--ink2); font-size:13px; }}
  .grid {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); margin:22px 0; }}
  .kpi {{ background:var(--surface); border:1px solid var(--ring); border-radius:12px; padding:16px 18px; }}
  .kpi-val {{ font-size:26px; font-weight:650; letter-spacing:-.01em; }}
  .kpi-lab {{ font-size:13px; font-weight:600; margin-top:2px; }}
  .kpi-sub {{ font-size:12px; color:var(--muted); margin-top:2px; }}
  .card {{ background:var(--surface); border:1px solid var(--ring); border-radius:12px; padding:18px 20px; margin:16px 0; }}
  .card h2 {{ font-size:15px; margin:0 0 14px; }}
  .bar-row {{ display:grid; grid-template-columns:210px 1fr 44px; align-items:center; gap:12px; margin:8px 0; }}
  .bar-lab {{ font-size:13px; display:flex; align-items:center; gap:7px; }}
  .bar-track {{ background:var(--grid); border-radius:6px; height:14px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:6px; min-width:2px; }}
  .bar-num {{ font-size:13px; text-align:right; font-variant-numeric:tabular-nums; color:var(--ink2); }}
  .dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; flex:none; }}
  .alerta {{ background:color-mix(in srgb, #fab219 14%, var(--surface));
    border:1px solid color-mix(in srgb,#fab219 40%,var(--ring)); border-radius:8px;
    padding:9px 12px; font-size:13px; margin:8px 0; }}
  .filtros {{ display:flex; flex-wrap:wrap; gap:8px; margin:6px 0 14px; align-items:center; }}
  .fbtn {{ font:inherit; font-size:13px; padding:6px 12px; border-radius:20px; cursor:pointer;
    background:var(--surface); color:var(--ink); border:1px solid var(--line);
    display:flex; align-items:center; gap:6px; }}
  .fbtn.activo {{ background:var(--ink); color:var(--surface); border-color:var(--ink); }}
  .search {{ font:inherit; font-size:13px; padding:6px 12px; border-radius:20px;
    border:1px solid var(--line); background:var(--surface); color:var(--ink); margin-left:auto; min-width:200px; }}
  .tabla-wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--grid); vertical-align:top; }}
  th {{ color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.03em;
    position:sticky; top:0; background:var(--surface); cursor:pointer; white-space:nowrap; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  td:first-child, td:nth-child(3) {{ white-space:nowrap; }}
  td.pos {{ color:#0ca30c; }} td.neg {{ color:#d03b3b; }}
  .chip {{ display:inline-flex; align-items:center; gap:5px; font-size:12px; font-weight:600;
    padding:2px 9px; border-radius:20px; color:var(--c);
    background:color-mix(in srgb, var(--c) 14%, var(--surface));
    border:1px solid color-mix(in srgb, var(--c) 40%, transparent); }}
  .chip.dup {{ --c:#d03b3b; }}
  tbody tr:hover {{ background:color-mix(in srgb, var(--ink) 4%, var(--surface)); }}
  footer {{ color:var(--muted); font-size:12px; margin-top:26px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{titulo}</h1>
    <div class="sub">Conciliación {na} ↔ {nb} · Cruce por N.º de documento · Generado {generado}</div>
  </header>

  <div class="grid">
    {kpi_docs}{kpi_conf}{kpi_var}{kpi_falt}
  </div>
  <div class="grid">
    {kpi_ta}{kpi_tb}{kpi_dif}
  </div>

  {alertas}

  <div class="card">
    <h2>Distribución por estado</h2>
    {barras}
  </div>

  <div class="card">
    <h2>Detalle de conciliación</h2>
    <div class="filtros">
      {botones}
      <input class="search" id="q" type="search" placeholder="Buscar documento o proveedor…">
    </div>
    <div class="tabla-wrap">
      <table id="tabla">
        <thead><tr>
          <th data-c="0">Documento</th><th data-c="1">Proveedor</th><th data-c="2">Fecha</th>
          <th data-c="3">Monto {col_a}</th><th data-c="4">Monto {col_b}</th>
          <th data-c="5">Diferencia</th><th data-c="6">%</th><th data-c="7">Estado</th>
        </tr></thead>
        <tbody id="tbody">{filas}</tbody>
      </table>
    </div>
  </div>

  <footer>Auditor Conciliador · Los montos con variación o faltantes requieren revisión manual.</footer>
</div>
<script>
  const tbody = document.getElementById('tbody');
  const filas = Array.from(tbody.rows);
  let filtro = 'TODOS';
  function aplicar() {{
    const q = document.getElementById('q').value.toLowerCase();
    filas.forEach(tr => {{
      const okF = filtro === 'TODOS' || tr.dataset.estado === filtro;
      const okQ = !q || tr.textContent.toLowerCase().includes(q);
      tr.style.display = (okF && okQ) ? '' : 'none';
    }});
  }}
  document.querySelectorAll('.fbtn').forEach(b => b.addEventListener('click', () => {{
    document.querySelectorAll('.fbtn').forEach(x => x.classList.remove('activo'));
    b.classList.add('activo'); filtro = b.dataset.f; aplicar();
  }}));
  document.getElementById('q').addEventListener('input', aplicar);
  // Orden por columna al hacer clic en el encabezado.
  document.querySelectorAll('th').forEach(th => th.addEventListener('click', () => {{
    const c = +th.dataset.c; const asc = th.dataset.asc !== 'true'; th.dataset.asc = asc;
    const vivas = filas.filter(f => f.style.display !== 'none');
    vivas.sort((a,b) => {{
      let x = a.cells[c].textContent.trim(), y = b.cells[c].textContent.trim();
      const nx = parseFloat(x.replace(/[^0-9.-]/g,'')), ny = parseFloat(y.replace(/[^0-9.-]/g,''));
      if (!isNaN(nx) && !isNaN(ny)) return asc ? nx-ny : ny-nx;
      return asc ? x.localeCompare(y) : y.localeCompare(x);
    }});
    vivas.forEach(f => tbody.appendChild(f));
  }}));
</script>
</body>
</html>"""
