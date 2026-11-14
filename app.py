import os
import json
import unicodedata
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import Dash, dcc, html, Input, Output, State, ctx, ALL
from home import build_home
from theme import (
    NAVY, NAVY_2, BLUE, BLUE_2, CYAN, GREEN, RED, AMBER, NEUTRAL,
    TEXT, MUTED, GRID, STATUS_COLORS, mix, tint
)

# ============================================================
# DASHBOARD GERENCIAL | PROYECTO AVISOS | EQUIPO 2
# Base: registros con marca = normal (2.815 avisos)
# Fecha de corte de los avisos abiertos: 06-may-2023
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:  # versión visible en la barra superior y en la pestaña, para comprobar qué se publicó
    with open(os.path.join(BASE_DIR, "VERSION.txt"), encoding="utf-8") as fh:
        APP_VERSION = fh.read().split(" - ")[0].strip() or "—"
except OSError:
    APP_VERSION = "—"

app = Dash(__name__, title=f"Gestión Gerencial de Avisos | Equipo 2 · v{APP_VERSION}",
           suppress_callback_exceptions=True)
server = app.server

df = pd.read_csv(os.path.join(BASE_DIR, "data", "avisos.csv"), low_memory=False)
df.columns = [str(c).replace("﻿", "").strip() for c in df.columns]

# Tipificación y limpieza
for c in ["Fecha de aviso", "Fecha de cierre"]:
    df[c] = pd.to_datetime(df[c], errors="coerce")
for c in ["Días abierto", "Prioridad días", "Cumple prioridad días",
          "Cumple prioridad periodos", "Año", "nMes", "Año cierre",
          "Latitud", "Longitud"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
for c in ["Tipo de aviso", "Sector", "Prioridad", "Estado aviso",
          "Tiempo aviso", "Departamento", "Municipio", "CTE", "Mes",
          "Linea", "Torre"]:
    df[c] = df[c].fillna("Sin dato").astype(str).str.strip()

# Alcance del plan de trabajo: marca = normal
df = df[df["marca"].astype(str).str.lower().eq("normal")].copy()
df["Mes fecha"] = df["Fecha de aviso"].dt.to_period("M").dt.to_timestamp()
df["Mes cierre fecha"] = df["Fecha de cierre"].dt.to_period("M").dt.to_timestamp()
df["Pendiente situación"] = np.where(
    df["Estado aviso"].eq("Abierto"),
    np.where(df["Tiempo aviso"].eq("Atrasado"), "Pendiente vencido",
             np.where(df["Tiempo aviso"].eq("A tiempo"), "Pendiente dentro del plazo", "Pendiente sin clasificación")),
    "No aplica"
)
# Número de torre para ordenar el trazado de cada línea (T4, T120-V, T88A → 4, 120, 88)
df["Torre n"] = pd.to_numeric(df["Torre"].str.extract(r"(\d+)")[0], errors="coerce")

AGE_BINS = [-1, 90, 365, 730, 1460, 100000]
AGE_LABELS = ["0–90 días", "91–365 días", "1–2 años", "2–4 años", "Más de 4 años"]
df["Antigüedad"] = pd.cut(df["Días abierto"], bins=AGE_BINS, labels=AGE_LABELS).astype(str)

YEARS = sorted(df["Año"].dropna().astype(int).unique().tolist())
PRIORITY_ORDER = ["Mes", "Trimestre", "Semestre", "Año", "Dos años", "Tres años", "Seis años"]
URGENT_PRIOS = ["Mes", "Trimestre"]
LONG_PRIOS = ["Dos años", "Tres años", "Seis años"]

# ------------------------------------------------------------
# Contexto y meta únicos para todo el tablero
# ------------------------------------------------------------
META_SLA = 80.0          # % mínimo de avisos cerrados dentro del plazo
BANDA_ALERTA = 20.0      # entre (meta − 20) y la meta = advertencia
FECHA_CORTE = "06-may-2023"
PERIODO = "ene-2011 – may-2023"
PARTIAL_YEAR = 2023      # año incompleto (avisos hasta mayo)
MIN_CERRADOS_LINEA = 10  # cierres mínimos para evaluar una línea

# Escalas ordinales (sin colores semánticos): más oscuro = más urgente / más antiguo
PRIORITY_COLORS = {p: mix(NAVY, tint(CYAN, 0.55), i / (len(PRIORITY_ORDER) - 1))
                   for i, p in enumerate(PRIORITY_ORDER)}
AGE_COLORS = {lbl: mix(tint(CYAN, 0.55), NAVY, i / (len(AGE_LABELS) - 1))
              for i, lbl in enumerate(AGE_LABELS)}


def sla_color(rate):
    """Color semántico único para cualquier tasa de cumplimiento."""
    if rate is None or pd.isna(rate):
        return NEUTRAL
    if rate >= META_SLA:
        return GREEN
    if rate >= META_SLA - BANDA_ALERTA:
        return AMBER
    return RED


def sla_kind(rate):
    return {GREEN: "ok", AMBER: "warning", RED: "danger"}.get(sla_color(rate), "info")


def fmt_int(v):
    try: return f"{int(round(float(v))):,}".replace(",", ".")
    except Exception: return "0"

def fmt_pct(v):
    try:
        if pd.isna(v): return "—"
        return f"{float(v):.1f}%".replace(".", ",")
    except Exception: return "—"

def fmt_pts(delta):
    try: return f"{float(delta):+.1f} pts".replace(".", ",")
    except Exception: return "—"

def pct(num, den):
    return num / den * 100 if den else np.nan

def _norm(text):
    """Normaliza nombres (sin tildes ni mayúsculas) para cruzar catálogos."""
    t = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in t if not unicodedata.combining(ch)).casefold().strip()

def options(col):
    vals = sorted(df[col].dropna().astype(str).unique().tolist())
    return [{"label": x, "value": x} for x in vals if x and x.lower() not in {"sin dato", "nan", "none", ""}]

def left_margin_for(labels, font_px=12, minimum=60):
    """
    Margen izquierdo (px) suficiente para el nombre de categoría más largo de
    un eje horizontal, de modo que ninguna etiqueta salga del recuadro.
    """
    longest = max((len(str(x)) for x in labels), default=0)
    return int(max(minimum, longest * font_px * 0.62 + 24))

def base_layout(fig, height=310, legend=True):
    fig.update_layout(
        height=height, autosize=True,
        margin=dict(l=14, r=14, t=24, b=48),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="DM Sans, Arial, sans-serif", color=TEXT, size=13),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0, font=dict(size=12, color=TEXT)),
        hoverlabel=dict(font=dict(family="DM Sans, Arial, sans-serif", size=13)),
        clickmode="event+select",
        transition_duration=300
    )
    fig.update_xaxes(showgrid=False, zeroline=False, automargin=True,
                     tickfont=dict(size=12, color=TEXT), title_font=dict(size=13, color=TEXT))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, automargin=True,
                     tickfont=dict(size=12, color=TEXT), title_font=dict(size=13, color=TEXT))
    for trace in fig.data:
        if getattr(trace, "text", None) is not None:
            try:
                trace.textfont = dict(size=12, color=TEXT)
            except Exception:
                pass
    for ann in fig.layout.annotations or []:
        if ann.font is None or ann.font.size is None or ann.font.size < 13:
            ann.font = dict(size=14, color=NAVY)
    return fig

def labels_clear_of_meta(fig, categories, values, labels, meta, axis_max, orientation="v"):
    """
    Evita que la línea punteada de la meta atraviese las etiquetas de las barras.

    Una etiqueta exterior ocupa el tramo inmediatamente posterior al final de la
    barra. Si la barra termina justo antes de la meta, ese tramo cruza la línea.
    En esos casos:
      - la etiqueta se escribe dentro de la barra (blanca, en su extremo), o
      - si la barra es demasiado corta, se escribe justo después de la línea.
    Debe llamarse después de base_layout(), que fija el estilo de las anotaciones.
    """
    window = axis_max * (0.10 if orientation == "v" else 0.16)
    positions = []
    for cat, v, lab in zip(categories, values, labels):
        if pd.isna(v) or not (meta - window < v < meta):
            positions.append("outside")
        elif v >= window * 1.15:
            positions.append("inside")
        else:
            positions.append("none")
            if orientation == "v":
                fig.add_annotation(x=cat, y=meta, text=lab, showarrow=False,
                                   yanchor="bottom", yshift=3,
                                   font=dict(size=13, color=TEXT))
            else:
                fig.add_annotation(x=meta, y=cat, text=lab, showarrow=False,
                                   xanchor="left", xshift=5,
                                   font=dict(size=13, color=TEXT))
    fig.update_traces(
        textposition=positions, insidetextanchor="end", textangle=0,
        insidetextfont=dict(family="DM Sans, Arial, sans-serif", size=12, color="white"),
        selector=dict(type="bar")
    )
    return fig

def meta_line(fig, value, orientation="v"):
    """
    Línea punteada de la meta dibujada POR ENCIMA de las barras.
    Un trazo blanco debajo le da contraste sobre cualquier color de barra.
    """
    add = fig.add_hline if orientation == "v" else fig.add_vline
    key = "y" if orientation == "v" else "x"
    add(**{key: value}, line_color="rgba(255,255,255,0.85)", line_width=4, layer="above")
    add(**{key: value}, line_color=NAVY, line_dash="dash", line_width=2, opacity=.85, layer="above")
    return fig

def meta_label_above_line(fig, categories, values, meta):
    """
    Rótulo de la meta justo encima de la línea, sobre la última barra (o la
    primera, si la última supera la meta y su etiqueta ocuparía ese espacio).
    """
    vals = list(values)
    if vals and pd.notna(vals[-1]) and vals[-1] < meta:
        x, anchor = 1, "right"
    elif vals and pd.notna(vals[0]) and vals[0] < meta:
        x, anchor = 0, "left"
    else:
        return meta_label_outside(fig, meta, "v")
    fig.add_annotation(xref="paper", yref="y", x=x, y=meta, text=f"Meta {meta:.0f} %",
                       showarrow=False, xanchor=anchor, yanchor="bottom", yshift=4,
                       font=dict(family="DM Sans, Arial, sans-serif", size=13, color=NAVY))
    return fig

def meta_label_outside(fig, meta, orientation="v", text=None):
    """Rótulo de la meta fuera del área de datos, para que no tape barras ni puntos."""
    text = text or f"Meta<br>{meta:.0f} %"
    if orientation == "v":
        fig.add_annotation(xref="paper", yref="y", x=1, y=meta, text=text, showarrow=False,
                           xanchor="left", yanchor="middle", xshift=6, align="left",
                           font=dict(family="DM Sans, Arial, sans-serif", size=13, color=NAVY))
    else:
        fig.add_annotation(xref="x", yref="paper", x=meta, y=1, text=text, showarrow=False,
                           xanchor="center", yanchor="bottom", yshift=2,
                           font=dict(family="DM Sans, Arial, sans-serif", size=13, color=NAVY))
    return fig

def empty_fig(msg="No hay datos para los filtros seleccionados"):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=13, color=MUTED))
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return base_layout(fig, 260, False)

def kpi(label, value, detail="", kind="info", text_value=False):
    value_class = "kpi-value kpi-value-text" if text_value else "kpi-value"
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(value, className=value_class),
        html.Div(detail, className="kpi-delta")
    ], className=f"kpi-card {kind}")

def card(title, fig, summary="", chart_key=None):
    graph_kwargs = {"figure": fig, "config": {"displayModeBar": False, "responsive": True}}
    if chart_key:
        graph_kwargs["id"] = {"type": "interactive-chart", "id": chart_key}
    return html.Div([
        html.Div(title, className="chart-title"),
        dcc.Graph(**graph_kwargs),
        html.Div(summary, className="chart-subtitle") if summary else None
    ], className="chart-card")

def active_filters_banner(years, types, depts, prios, extra):
    """Muestra todos los filtros activos tanto de barra lateral como de clics en gráficas."""
    chips = []
    if years: chips.append(f"Años: {', '.join(map(str, years))}")
    if types: chips.append(f"Tipo: {', '.join(types)}")
    if depts: chips.append(f"Depto: {', '.join(depts)}")
    if prios: chips.append(f"Prioridad: {', '.join(prios)}")
    if extra:
        if extra.get("estado"):     chips.append(f"Estado: {extra['estado']}")
        if extra.get("tiempo"):     chips.append(f"Tiempo frente al plazo: {extra['tiempo']}")
        if extra.get("pend_sit"):   chips.append(f"Situación: {extra['pend_sit']}")
        if extra.get("antiguedad"): chips.append(f"Antigüedad: {extra['antiguedad']}")
        if extra.get("linea"):      chips.append(f"Línea: {extra['linea']}")

    if not chips:
        texto = "Interactividad activa en todas las gráficas: Haz clic en cualquier barra, anillo, caja o punto mensual para filtrar el tablero."
        bg = "#F4F7FB"
        border = "#D1DCEC"
    else:
        texto = "Filtros aplicados (vuelve a hacer clic en la gráfica o usa 'Restablecer' para quitar): " + "  |  ".join(chips)
        bg = "#EBF3FF"
        border = BLUE

    return html.Div(
        texto,
        style={
            "backgroundColor": bg, "borderLeft": f"4px solid {border}",
            "padding": "9px 14px", "borderRadius": "6px", "marginBottom": "14px",
            "fontSize": "12.5px", "color": NAVY, "fontWeight": "500"
        }
    )

def header(title, subtitle, years=None, types=None, depts=None, prios=None, extra=None):
    return html.Div([
        html.Div([
            html.Div(title, className="page-title"),
            html.Div(subtitle, className="page-subtitle")
        ], className="page-header"),
        html.Div(
            f"Periodo analizado: {PERIODO} · Corte de avisos abiertos: {FECHA_CORTE} · "
            f"Base: marca = normal (se excluyen registros extremos y escasos) · "
            f"Meta de cumplimiento: ≥ {META_SLA:.0f} % de cierres dentro del plazo",
            className="page-context"
        ),
        active_filters_banner(years, types, depts, prios, extra)
    ])

def filter_data(years=None, types=None, depts=None, prios=None, extra=None):
    d = df.copy()
    if years: d = d[d["Año"].isin(years)]
    if depts: d = d[d["Departamento"].isin(depts)]
    if types: d = d[d["Tipo de aviso"].isin(types)]
    if prios: d = d[d["Prioridad"].isin(prios)]
    if extra:
        if extra.get("estado"):
            d = d[d["Estado aviso"].eq(extra["estado"])]
        if extra.get("tiempo"):
            d = d[d["Tiempo aviso"].eq(extra["tiempo"])]
        if extra.get("pend_sit"):
            d = d[d["Pendiente situación"].eq(extra["pend_sit"])]
        if extra.get("antiguedad"):
            d = d[d["Antigüedad"].eq(extra["antiguedad"])]
        if extra.get("linea"):
            d = d[d["Linea"].eq(extra["linea"])]
    return d

# ============================================================
# INDICADORES (KPI) — un conjunto propio para cada página
# ============================================================

def kpis(d):
    """KPI globales del Resumen gerencial."""
    closed = d[d["Estado aviso"].eq("Cerrado")]
    opened = d[d["Estado aviso"].eq("Abierto")]
    ontime = int(closed["Tiempo aviso"].eq("A tiempo").sum())
    pending_late = int(opened["Tiempo aviso"].eq("Atrasado").sum())
    pending_ontime = int(opened["Tiempo aviso"].eq("A tiempo").sum())
    rate = pct(ontime, len(closed))
    med_days = closed["Días abierto"].median() if not closed.empty else 0
    risk = pct(pending_late, len(opened))

    return [
        kpi("AVISOS REGISTRADOS", fmt_int(len(d)), f"{PERIODO} · marca normal", "info"),
        kpi("TASA DE CIERRE", fmt_pct(pct(len(closed), len(d))), f"{fmt_int(len(closed))} cerrados de {fmt_int(len(d))}", "info"),
        kpi("CUMPLIMIENTO DE CIERRES", fmt_pct(rate),
            f"{fmt_pts(rate - META_SLA)} frente a la meta de {META_SLA:.0f} %", sla_kind(rate)),
        kpi("BACKLOG ACTIVO (ABIERTOS)", fmt_int(len(opened)), f"{fmt_int(pending_late)} vencidos · {fmt_int(pending_ontime)} en plazo", "warning"),
        kpi("RIESGO EN BACKLOG", fmt_pct(risk), f"{fmt_int(pending_late)} pendientes ya vencidos al {FECHA_CORTE}",
            "danger" if (not pd.isna(risk) and risk > 30) else "warning"),
        kpi("TIEMPO MEDIANO DE SOLUCIÓN", f"{fmt_int(med_days)} días", "Mediana en avisos cerrados", "info")
    ]

def compliance_kpis(d):
    """KPI de la página Cumplimiento y plazos."""
    closed = d[d["Estado aviso"].eq("Cerrado")]
    ontime = closed["Tiempo aviso"].eq("A tiempo")
    rate = pct(int(ontime.sum()), len(closed))

    urg = closed[closed["Prioridad"].isin(URGENT_PRIOS)]
    urg_rate = pct(int(urg["Tiempo aviso"].eq("A tiempo").sum()), len(urg))
    lng = closed[closed["Prioridad"].isin(LONG_PRIOS)]
    lng_rate = pct(int(lng["Tiempo aviso"].eq("A tiempo").sum()), len(lng))
    late = int(closed["Tiempo aviso"].eq("Atrasado").sum())
    med = closed["Días abierto"].median() if not closed.empty else 0

    worst_name, worst_detail = "—", "Sin cierres suficientes"
    by_type = closed.groupby("Tipo de aviso")["Tiempo aviso"].agg(
        n="size", late=lambda s: int(s.eq("Atrasado").sum()))
    by_type = by_type[by_type["n"] >= 10]
    if not by_type.empty:
        by_type["pct"] = by_type["late"] / by_type["n"] * 100
        worst_name = by_type["pct"].idxmax()
        worst_detail = f"{fmt_pct(by_type['pct'].max())} de sus cierres atrasados"

    return [
        kpi("CUMPLIMIENTO DE CIERRES", fmt_pct(rate),
            f"{fmt_pts(rate - META_SLA)} frente a la meta de {META_SLA:.0f} %", sla_kind(rate)),
        kpi("PRIORIDADES URGENTES", fmt_pct(urg_rate),
            f"Mes y Trimestre · {fmt_int(len(urg))} cierres", sla_kind(urg_rate)),
        kpi("PRIORIDADES DE LARGO PLAZO", fmt_pct(lng_rate),
            f"Dos a seis años · {fmt_int(len(lng))} cierres", sla_kind(lng_rate)),
        kpi("CIERRES ATRASADOS", fmt_int(late),
            f"{fmt_pct(pct(late, len(closed)))} de los cierres del periodo", "danger" if late else "ok"),
        kpi("MEDIANA DE DÍAS AL CIERRE", f"{fmt_int(med)} días", "La mitad de los cierres tarda más", "info"),
        kpi("TIPO MÁS REZAGADO", worst_name, worst_detail, "danger", text_value=True),
    ]

def territory_kpis(d):
    """KPI de la página Territorio y red."""
    lines = build_line_stats(d)
    evaluated = lines[lines["Cerrados"] >= MIN_CERRADOS_LINEA] if not lines.empty else lines
    n_eval = len(evaluated)
    under = int((evaluated["Cumplimiento"] < META_SLA).sum()) if n_eval else 0

    closed = d[d["Estado aviso"].eq("Cerrado")]
    def cte_rate(name):
        c = closed[closed["CTE"].eq(name)]
        return pct(int(c["Tiempo aviso"].eq("A tiempo").sum()), len(c)), len(c)
    centro, n_c = cte_rate("Centro")
    suroc, n_s = cte_rate("Suroccidente")

    opened = d[d["Estado aviso"].eq("Abierto")]
    venc = opened[opened["Tiempo aviso"].eq("Atrasado") & opened["Torre"].ne("Sin dato")]
    towers_venc = venc[["Linea", "Torre"]].drop_duplicates().shape[0]

    dept_name, dept_detail = "—", "Sin pendientes suficientes"
    od = opened[opened["Departamento"].ne("Sin dato")].groupby("Departamento")["Tiempo aviso"].agg(
        n="size", late=lambda s: int(s.eq("Atrasado").sum()))
    od = od[od["n"] >= 10]
    if not od.empty:
        od["pct"] = od["late"] / od["n"] * 100
        dept_name = od["pct"].idxmax()
        dept_detail = f"{fmt_pct(od['pct'].max())} de sus {fmt_int(od.loc[dept_name, 'n'])} pendientes vencidos"

    return [
        kpi("LÍNEAS BAJO LA META", f"{under} de {n_eval}",
            f"Líneas con ≥ {MIN_CERRADOS_LINEA} cierres evaluables",
            "danger" if n_eval and under / n_eval > .5 else ("warning" if under else "ok")),
        kpi("CUMPLIMIENTO CTE CENTRO", fmt_pct(centro),
            f"{fmt_pts(centro - META_SLA)} vs meta · {fmt_int(n_c)} cierres", sla_kind(centro)),
        kpi("CUMPLIMIENTO CTE SUROCCIDENTE", fmt_pct(suroc),
            f"{fmt_pts(suroc - META_SLA)} vs meta · {fmt_int(n_s)} cierres", sla_kind(suroc)),
        kpi("TORRES CON VENCIDOS", fmt_int(towers_venc),
            f"{fmt_int(len(venc))} avisos vencidos con torre identificada", "danger" if towers_venc else "ok"),
        kpi("DEPARTAMENTO MÁS CRÍTICO", dept_name, dept_detail, "danger", text_value=True),
        kpi("MUNICIPIOS CON PENDIENTES", fmt_int(opened["Municipio"].replace("Sin dato", np.nan).nunique()),
            f"de {fmt_int(d['Municipio'].replace('Sin dato', np.nan).nunique())} municipios con avisos", "info"),
    ]

# ============================================================
# VISUALIZACIONES CON INTERACTIVIDAD COMPLETA
# ============================================================

def status_donut(d):
    c = d["Estado aviso"].value_counts().rename_axis("Estado").reset_index(name="Avisos")
    if c.empty: return empty_fig()
    fig = go.Figure(go.Pie(
        labels=c["Estado"], values=c["Avisos"], hole=.60,
        marker=dict(colors=[STATUS_COLORS.get(x, NEUTRAL) for x in c["Estado"]], line=dict(color="white", width=3)),
        textinfo="label+percent", textposition="outside",
        textfont=dict(size=14, color=TEXT),
        hovertemplate="<b>%{label}</b> (Clic para filtrar)<br>Avisos: %{value:,}<br>Participación: %{percent}<extra></extra>"
    ))
    fig.add_annotation(text=f"<b>{fmt_int(len(d))}</b><br><span style='font-size:13px;color:{MUTED}'>Avisos</span>",
                       x=.5, y=.5, showarrow=False, font=dict(color=NAVY, size=17))
    return base_layout(fig, 315, False)

def closed_compliance_donut(d):
    c = d[d["Estado aviso"].eq("Cerrado")]
    v = c["Tiempo aviso"].value_counts().reindex(["A tiempo", "Atrasado"], fill_value=0)
    if v.sum() == 0: return empty_fig()
    rate = v["A tiempo"] / v.sum() * 100
    fig = go.Figure(go.Pie(
        labels=v.index, values=v.values, hole=.60, sort=False,
        marker=dict(colors=[GREEN, RED], line=dict(color="white", width=3)),
        textinfo="label+percent", textposition="outside",
        textfont=dict(size=14, color=TEXT),
        hovertemplate="<b>%{label}</b> (Clic para filtrar)<br>Avisos: %{value:,}<br>Participación: %{percent}<extra></extra>"
    ))
    fig.add_annotation(text=f"<b>{rate:.1f}%</b><br><span style='font-size:13px;color:{MUTED}'>A tiempo · meta {META_SLA:.0f} %</span>",
                       x=.5, y=.5, showarrow=False, font=dict(color=sla_color(rate), size=17))
    return base_layout(fig, 315, False)

def trend_incoming_closed(d):
    if d.empty: return empty_fig()
    a = d.groupby(d["Fecha de aviso"].dt.to_period("M").dt.to_timestamp()).size().rename("Recibidos")
    closed = d[d["Estado aviso"].eq("Cerrado")]
    c = closed.groupby("Mes cierre fecha").size().rename("Cerrados")
    g = pd.concat([a, c], axis=1, sort=False).fillna(0).sort_index().reset_index()
    xcol = g.columns[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=g[xcol], y=g["Recibidos"], name="Avisos recibidos", mode="lines+markers",
        marker=dict(size=5), line=dict(color=CYAN, width=2.5),
        hovertemplate="<b>%{x|%b %Y}</b> (Clic para filtrar año)<br>Recibidos: %{y:,}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=g[xcol], y=g["Cerrados"], name="Avisos cerrados", mode="lines+markers",
        marker=dict(size=5), line=dict(color=NAVY, width=2.5),
        hovertemplate="<b>%{x|%b %Y}</b> (Clic para filtrar año)<br>Cerrados: %{y:,}<extra></extra>"
    ))
    fig.update_layout(xaxis_title="Mes (Clic en un punto para filtrar su año)", yaxis_title="Cantidad de avisos", hovermode="x unified")
    return base_layout(fig, 330, True)

def _year_label(y):
    return f"{int(y)}*" if int(y) == PARTIAL_YEAR else str(int(y))

def annual_backlog(d):
    if d.empty: return empty_fig()
    g = d.groupby(["Año", "Estado aviso"], observed=False).size().reset_index(name="Avisos")
    years = sorted(pd.to_numeric(d["Año"], errors="coerce").dropna().astype(int).unique().tolist())
    states = ["Cerrado", "Abierto"]
    full_index = pd.MultiIndex.from_product([years, states], names=["Año", "Estado aviso"])
    g = g.set_index(["Año", "Estado aviso"]).reindex(full_index, fill_value=0).reset_index()
    g["Año etiqueta"] = g["Año"].map(_year_label)
    year_order = [_year_label(y) for y in years]
    g["Estado aviso"] = pd.Categorical(g["Estado aviso"], categories=states, ordered=True)
    g = g.sort_values(["Año", "Estado aviso"])

    fig = px.bar(
        g, x="Año etiqueta", y="Avisos", color="Estado aviso", barmode="group", text="Avisos",
        category_orders={"Año etiqueta": year_order, "Estado aviso": states},
        color_discrete_map=STATUS_COLORS,
    )
    for tr in fig.data:
        tr.texttemplate = "%{y:,}"
        tr.textposition = "outside"
        tr.cliponaxis = False
        tr.textfont = dict(family="DM Sans, Arial, sans-serif", size=11, color=TEXT)
        tr.marker.cornerradius = 7
        tr.marker.line.width = 0
        tr.hovertemplate = "<b>Año %{x}</b> (Clic para filtrar)<br>%{fullData.name}: %{y:,}<extra></extra>"

    max_value = int(g["Avisos"].max()) if len(g) else 0
    fig.update_layout(
        barmode="group", bargap=0.16, bargroupgap=0.035,
        uniformtext_minsize=9, uniformtext_mode="hide",
        legend=dict(orientation="h", y=1.06, x=0, xanchor="left"),
        margin=dict(l=46, r=20, t=40, b=58),
    )
    x_title = "Año de aviso (Clic en una barra para filtrar)"
    if PARTIAL_YEAR in years:
        x_title += f" · *{PARTIAL_YEAR} parcial: avisos hasta mayo"
    fig.update_xaxes(title=x_title, tickangle=0, showgrid=False,
                     tickmode="array", tickvals=year_order, ticktext=year_order, tickfont=dict(size=10))
    fig.update_yaxes(title="Número de avisos", gridcolor=GRID, zeroline=False,
                     range=[0, max_value * 1.28 if max_value else 1], showticklabels=False)
    return base_layout(fig, 350, True)

def compliance_by_priority(d):
    c = d[d["Estado aviso"].eq("Cerrado")]
    if c.empty: return empty_fig()
    g = c.groupby("Prioridad").agg(
        Total=("Aviso", "nunique"),
        A_tiempo=("Tiempo aviso", lambda s: int(s.eq("A tiempo").sum()))
    ).reset_index()
    g["Cumplimiento"] = g["A_tiempo"] / g["Total"] * 100
    g["ord"] = g["Prioridad"].apply(lambda x: PRIORITY_ORDER.index(x) if x in PRIORITY_ORDER else 99)
    g = g.sort_values("ord")

    fig = go.Figure(go.Bar(
        x=g["Prioridad"], y=g["Cumplimiento"],
        text=g["Cumplimiento"].map(lambda x: f"{x:.1f}%"), textposition="outside", cliponaxis=False,
        marker=dict(color=[sla_color(v) for v in g["Cumplimiento"]], cornerradius=7, line=dict(width=0)),
        customdata=g[["Total", "A_tiempo"]],
        hovertemplate=("<b>Prioridad: %{x}</b> (Clic para filtrar)<br>Cumplimiento: %{y:.1f}%<br>"
                       "Cerrados: %{customdata[0]:,} · A tiempo: %{customdata[1]:,}<extra></extra>")
    ))
    meta_line(fig, META_SLA, "v")
    fig.update_layout(
        yaxis_title="% de cerrados a tiempo",
        xaxis_title="Prioridad · de la más urgente a la de mayor plazo (Clic para filtrar)",
        uniformtext_minsize=10, uniformtext_mode="hide", margin=dict(l=46, r=24, t=28, b=52)
    )
    fig.update_yaxes(range=[0, 115], tickvals=[0, 20, 40, 60, 80, 100])
    base_layout(fig, 340, False)
    meta_label_above_line(fig, g["Prioridad"], g["Cumplimiento"], META_SLA)
    labels_clear_of_meta(fig, g["Prioridad"], g["Cumplimiento"],
                         g["Cumplimiento"].map(lambda x: f"{x:.1f}%"), META_SLA, 115, "v")
    return fig

def duration_distribution_by_priority(d):
    """Boxplot horizontal por prioridad, con escala visual hasta el percentil 95."""
    c = d[d["Estado aviso"].eq("Cerrado")].dropna(subset=["Días abierto", "Prioridad"]).copy()
    if c.empty: return empty_fig()

    present_prios = [p for p in PRIORITY_ORDER if p in c["Prioridad"].unique()]
    if not present_prios:
        present_prios = sorted(c["Prioridad"].unique().tolist())

    fig = go.Figure()
    for p in present_prios:
        sub = c[c["Prioridad"].eq(p)]["Días abierto"]
        if sub.empty:
            continue
        col = PRIORITY_COLORS.get(p, BLUE)
        fig.add_trace(go.Box(
            x=sub,
            y=[p] * len(sub),
            name=p,
            orientation="h",
            width=0.62,
            boxpoints="outliers",
            marker=dict(color=col, size=5, opacity=0.65),
            line=dict(color=col, width=1.8),
            fillcolor=tint(col, 0.45),
            hovertemplate=(
                f"<b>Prioridad: {p}</b> (Clic para filtrar)<br>"
                "Días abierto: %{x:,} días<extra></extra>"
            )
        ))

    # Escala completa: incluye el caso más largo de cualquier prioridad, para que
    # ninguna caja, bigote ni punto atípico quede cortado (p. ej. Seis años ≈ 3.700 días).
    x_max = max(float(c["Días abierto"].max()) * 1.04, 60)
    step = 250 if x_max <= 2500 else 500

    fig.update_layout(
        xaxis_title="Días transcurridos hasta el cierre (escala completa · Clic en una caja para filtrar)",
        yaxis_title="Prioridad asignada",
        margin=dict(l=110, r=30, t=24, b=52),
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(present_prios))),
        xaxis=dict(range=[0, x_max], dtick=step, showgrid=True, gridcolor=GRID)
    )
    return base_layout(fig, 380, False)

def monthly_closed_compliance(d):
    c = d[d["Estado aviso"].eq("Cerrado")].copy()
    if c.empty: return empty_fig()
    g = c.groupby("Mes cierre fecha").agg(
        Cerrados=("Aviso", "nunique"),
        A_tiempo=("Tiempo aviso", lambda s: int(s.eq("A tiempo").sum()))
    ).reset_index()
    g["Cumplimiento"] = g["A_tiempo"] / g["Cerrados"] * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=g["Mes cierre fecha"], y=g["Cumplimiento"], mode="lines+markers",
        name="Cumplimiento mensual", line=dict(color=tint(BLUE, 0.35), width=2),
        marker=dict(color=[sla_color(v) for v in g["Cumplimiento"]], size=8, line=dict(color="white", width=1)),
        customdata=g[["Cerrados", "A_tiempo"]],
        hovertemplate=(
            "<b>%{x|%B %Y}</b> (Clic para filtrar año)<br>Cumplimiento: %{y:.1f}%<br>"
            "Avisos cerrados: %{customdata[0]:,}<br>Cerrados a tiempo: %{customdata[1]:,}<extra></extra>"
        )
    ))
    meta_line(fig, META_SLA, "v")
    fig.update_yaxes(range=[0, 110], tickvals=[0, 20, 40, 60, 80, 100], title="% de avisos cerrados a tiempo")
    fig.update_xaxes(title="Mes de cierre (Clic en cualquier punto para filtrar por ese año)", tickformat="%Y", dtick="M12")
    fig.update_layout(margin=dict(l=58, r=62, t=32, b=52), hovermode="x unified")
    base_layout(fig, 320, False)
    return meta_label_outside(fig, META_SLA, "v")

def late_by_type(d):
    c = d[d["Estado aviso"].eq("Cerrado")]
    if c.empty: return empty_fig()
    g = c.groupby("Tipo de aviso").agg(
        Total=("Aviso", "nunique"),
        Atrasados=("Tiempo aviso", lambda s: int(s.eq("Atrasado").sum()))
    ).reset_index()
    g["% atrasados"] = g["Atrasados"] / g["Total"] * 100
    g = g.sort_values("% atrasados", ascending=True)
    tolerable = 100 - META_SLA

    fig = go.Figure(go.Bar(
        x=g["% atrasados"], y=g["Tipo de aviso"], orientation="h",
        text=g["% atrasados"].map(lambda x: f"{x:.1f}%"), textposition="outside", cliponaxis=False,
        marker=dict(color=[sla_color(100 - v) for v in g["% atrasados"]], cornerradius=7, line=dict(width=0)),
        customdata=g[["Total", "Atrasados"]],
        hovertemplate=("<b>%{y}</b> (Clic para filtrar)<br>% atrasados: %{x:.1f}%<br>"
                       "Cerrados: %{customdata[0]:,} · Atrasados: %{customdata[1]:,}<extra></extra>")
    ))
    meta_line(fig, tolerable, "h")
    max_value = float(g["% atrasados"].max()) if len(g) else 0
    x_max = max(max_value * 1.22, tolerable * 1.3, 1)
    fig.update_layout(
        xaxis_title="% de avisos cerrados atrasados (Clic en barra para filtrar)",
        yaxis_title="", uniformtext_minsize=10, uniformtext_mode="hide",
        margin=dict(l=left_margin_for(g["Tipo de aviso"]), r=48, t=34, b=48)
    )
    fig.update_xaxes(range=[0, x_max])
    base_layout(fig, 340, False)
    meta_label_outside(fig, tolerable, "h", f"Máximo tolerable: {tolerable:.0f} %")
    labels_clear_of_meta(fig, g["Tipo de aviso"], g["% atrasados"],
                         g["% atrasados"].map(lambda x: f"{x:.1f}%"), tolerable, x_max, "h")
    return fig

def pending_status(d):
    o = d[d["Estado aviso"].eq("Abierto")]
    states = ["Pendiente dentro del plazo", "Pendiente vencido", "Pendiente sin clasificación"]
    vals = o["Pendiente situación"].value_counts().reindex(states, fill_value=0)
    vals = vals[vals > 0]
    if vals.sum() == 0: return empty_fig()

    color_by_state = {
        "Pendiente dentro del plazo": GREEN,
        "Pendiente vencido": RED,
        "Pendiente sin clasificación": AMBER
    }
    fig = go.Figure(go.Pie(
        labels=vals.index, values=vals.values, hole=.58, sort=False,
        marker=dict(colors=[color_by_state[s] for s in vals.index], line=dict(color="white", width=3)),
        textinfo="label+value+percent", textposition="outside",
        textfont=dict(family="DM Sans, Arial, sans-serif", size=12, color=TEXT),
        hovertemplate="<b>%{label}</b> (Clic para filtrar)<br>Avisos: %{value:,}<br>Participación: %{percent}<extra></extra>"
    ))
    fig.add_annotation(
        text=f"<b>{fmt_int(len(o))}</b><br><span style='font-size:12px;color:{MUTED}'>Pendientes</span>",
        x=.5, y=.5, showarrow=False, font=dict(color=NAVY, size=17)
    )
    return base_layout(fig, 320, False)

def pending_age(d):
    o = d[d["Estado aviso"].eq("Abierto")].copy()
    if o.empty: return empty_fig()
    g = o["Antigüedad"].value_counts().reindex(AGE_LABELS, fill_value=0).reset_index()
    g.columns = ["Antigüedad", "Avisos"]

    fig = px.bar(
        g, x="Antigüedad", y="Avisos", text="Avisos", color="Antigüedad",
        color_discrete_map=AGE_COLORS, category_orders={"Antigüedad": AGE_LABELS}
    )
    fig.update_traces(
        texttemplate="%{y:,}", textposition="outside", cliponaxis=False,
        marker=dict(cornerradius=7, line=dict(width=0)),
        hovertemplate="<b>%{x}</b> (Clic para filtrar)<br>Avisos abiertos: %{y:,}<extra></extra>"
    )
    max_value = int(g["Avisos"].max()) if len(g) else 0
    fig.update_layout(showlegend=False, xaxis_title="Antigüedad del pendiente · más oscuro = más antiguo (Clic para filtrar)",
                      yaxis_title="Avisos", margin=dict(l=48, r=22, t=28, b=54))
    fig.update_yaxes(range=[0, max_value * 1.20 if max_value else 1])
    return base_layout(fig, 320, False)

def pending_by_type(d):
    o = d[d["Estado aviso"].eq("Abierto")]
    if o.empty: return empty_fig()
    states = ["Pendiente dentro del plazo", "Pendiente vencido", "Pendiente sin clasificación"]
    types_order = ["Construcciones", "Invasión/Explanacion", "Obras", "Permiso Ingreso", "Vegetación"]
    g = o.groupby(["Tipo de aviso", "Pendiente situación"]).size().reset_index(name="Avisos")
    fig = px.bar(
        g, x="Tipo de aviso", y="Avisos", color="Pendiente situación", barmode="stack",
        category_orders={"Pendiente situación": states, "Tipo de aviso": types_order},
        color_discrete_map={"Pendiente dentro del plazo": GREEN, "Pendiente vencido": RED, "Pendiente sin clasificación": AMBER}
    )
    fig.update_traces(hovertemplate="<b>%{x}</b> (Clic para filtrar)<br>Avisos: %{y:,}<extra></extra>")
    fig.update_layout(xaxis_title="Tipo de aviso (Clic en una barra para filtrar)", yaxis_title="Avisos",
                      legend_title_text="Situación del pendiente")
    return base_layout(fig, 320, True)

def department_performance(d):
    c = d[d["Estado aviso"].eq("Cerrado")]
    o = d[d["Estado aviso"].eq("Abierto")]
    if d.empty: return empty_fig()

    pending = o.groupby("Departamento").size().rename("Pendientes")
    late = c[c["Tiempo aviso"].eq("Atrasado")].groupby("Departamento").size().rename("Cerrados atrasados")
    g = pd.concat([pending, late], axis=1).fillna(0).reset_index()

    department_text = g["Departamento"].fillna("").astype(str).str.strip()
    missing_labels = {"", "sin dato", "s/d", "sd", "no registra", "no disponible", "nan", "none", "null"}
    g = g.loc[~department_text.str.lower().isin(missing_labels)].copy()
    if g.empty:
        return empty_fig("No hay departamentos identificados para los filtros seleccionados.")

    g["Total"] = g["Pendientes"] + g["Cerrados atrasados"]
    g = g.sort_values("Total", ascending=False, kind="stable").head(12)
    department_order = g["Departamento"].astype(str).tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=g["Departamento"], x=g["Pendientes"], name="Pendientes",
        orientation="h", marker=dict(color=RED, cornerradius=7, line=dict(width=0)),
        hovertemplate="<b>%{y}</b> (Clic para filtrar)<br>Pendientes: %{x:,}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        y=g["Departamento"], x=g["Cerrados atrasados"], name="Cerrados atrasados",
        orientation="h", marker=dict(color=AMBER, cornerradius=7, line=dict(width=0)),
        hovertemplate="<b>%{y}</b> (Clic para filtrar)<br>Cerrados atrasados: %{x:,}<extra></extra>"
    ))
    fig.update_layout(
        barmode="stack", xaxis_title="Avisos (Clic en un departamento para filtrar)", yaxis_title="",
        bargap=.22, legend=dict(orientation="h", y=1.04, x=0),
        margin=dict(l=left_margin_for(department_order), r=22, t=42, b=48),
        yaxis=dict(categoryorder="array", categoryarray=department_order, autorange="reversed",
                   ticklabelstandoff=6)
    )
    # Rango fijo desde 0: sin él, el eje podía arrancar en negativo y separar
    # los nombres de los departamentos de sus barras, sacándolos del recuadro.
    max_total = float(g["Total"].max()) if len(g) else 0
    fig.update_xaxes(range=[0, max_total * 1.06 if max_total else 1], rangemode="tozero")
    return base_layout(fig, 320, True)

# ============================================================
# RED DE TRANSMISIÓN: indicadores por línea y por torre
# ============================================================

def _flags(d):
    """Columnas auxiliares 0/1 para agregar por línea, torre o municipio."""
    closed = d["Estado aviso"].eq("Cerrado")
    opened = d["Estado aviso"].eq("Abierto")
    late = d["Tiempo aviso"].eq("Atrasado")
    return d.assign(
        _cerr=closed.astype(int),
        _cerr_ok=(closed & d["Tiempo aviso"].eq("A tiempo")).astype(int),
        _cerr_late=(closed & late).astype(int),
        _abierto=opened.astype(int),
        _venc=(opened & late).astype(int),
        _abierto_ok=(opened & d["Tiempo aviso"].eq("A tiempo")).astype(int),
        _dias_cierre=d["Días abierto"].where(closed),
        _dias_abierto=d["Días abierto"].where(opened),
    )

def _mode(s):
    m = s[s.ne("Sin dato")].mode()
    return m.iat[0] if not m.empty else "Sin dato"

def build_line_stats(d):
    g = d[d["Linea"].ne("Sin dato")]
    cols = ["Linea", "Avisos", "Cerrados", "A_tiempo", "Abiertos", "Vencidos",
            "Mediana_dias", "Torres", "CTE", "Tipo", "Departamentos", "Cumplimiento"]
    if g.empty:
        return pd.DataFrame(columns=cols)
    s = _flags(g).groupby("Linea").agg(
        Avisos=("Aviso", "size"), Cerrados=("_cerr", "sum"), A_tiempo=("_cerr_ok", "sum"),
        Abiertos=("_abierto", "sum"), Vencidos=("_venc", "sum"),
        Mediana_dias=("_dias_cierre", "median"), Torres=("Torre", "nunique"),
        CTE=("CTE", _mode), Tipo=("Tipo de aviso", _mode),
        Departamentos=("Departamento", lambda x: ", ".join(sorted({v for v in x if v != "Sin dato"}))),
    ).reset_index()
    s["Cumplimiento"] = np.where(s["Cerrados"] > 0, s["A_tiempo"] / s["Cerrados"].clip(lower=1) * 100, np.nan)
    return s[cols]

def build_tower_stats(d):
    g = d[d["Linea"].ne("Sin dato") & d["Torre"].ne("Sin dato")].dropna(subset=["Latitud", "Longitud"])
    if g.empty:
        return pd.DataFrame()
    t = _flags(g).groupby(["Linea", "Torre"]).agg(
        Lat=("Latitud", "median"), Lon=("Longitud", "median"), Torre_n=("Torre n", "first"),
        Municipio=("Municipio", _mode), Departamento=("Departamento", _mode),
        Avisos=("Aviso", "nunique"), Cerrados=("_cerr", "sum"),
        Cerrados_a_tiempo=("_cerr_ok", "sum"), Cerrados_atrasados=("_cerr_late", "sum"),
        Abiertos=("_abierto", "sum"), Pendientes_en_plazo=("_abierto_ok", "sum"),
        Vencidos=("_venc", "sum"), Mediana_dias_abierto=("_dias_abierto", "median"),
        Max_dias_abierto=("_dias_abierto", "max"), Mediana_dias_cierre=("_dias_cierre", "median"),
        Tipo=("Tipo de aviso", _mode), Prioridad=("Prioridad", _mode), CTE=("CTE", _mode),
    ).reset_index()
    t["Cumplimiento"] = np.where(
        t["Cerrados"] > 0,
        t["Cerrados_a_tiempo"] / t["Cerrados"] * 100,
        np.nan
    )
    return t.sort_values(["Linea", "Torre_n", "Torre"])

# ============================================================
# MAPAS (Folium / Leaflet)
# ============================================================

COLOMBIA_DEPARTMENTS_GEOJSON_URL = (
    "https://raw.githubusercontent.com/ytolosa/mapas-colombia/main/"
    "output/geojson/col_departamentos_inset_nacional.geojson"
)
_COLOMBIA_GEOJSON_CACHE = None

def load_colombia_departments_geojson():
    global _COLOMBIA_GEOJSON_CACHE
    if _COLOMBIA_GEOJSON_CACHE is not None:
        return _COLOMBIA_GEOJSON_CACHE
    try:
        import urllib.request
        req = urllib.request.Request(
            COLOMBIA_DEPARTMENTS_GEOJSON_URL,
            headers={"User-Agent": "Dashboard-Avisos-Equipo2/2.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            _COLOMBIA_GEOJSON_CACHE = json.loads(response.read().decode("utf-8"))
    except Exception:
        _COLOMBIA_GEOJSON_CACHE = {}
    return _COLOMBIA_GEOJSON_CACHE

DEPARTMENT_CAPITALS = [
    ("Amazonas","Leticia",-4.2153,-69.9406),("Antioquia","Medellín",6.2442,-75.5812),
    ("Arauca","Arauca",7.0847,-70.7591),("Atlántico","Barranquilla",10.9685,-74.7813),
    ("Bogotá, D.C.","Bogotá",4.7110,-74.0721),("Bolívar","Cartagena",10.3910,-75.4794),
    ("Boyacá","Tunja",5.5353,-73.3678),("Caldas","Manizales",5.0703,-75.5138),
    ("Caquetá","Florencia",1.6144,-75.6062),("Casanare","Yopal",5.3378,-72.3959),
    ("Cauca","Popayán",2.4448,-76.6147),("Cesar","Valledupar",10.4631,-73.2532),
    ("Chocó","Quibdó",5.6947,-76.6611),("Córdoba","Montería",8.7480,-75.8814),
    ("Cundinamarca","Bogotá",4.7110,-74.0721),("Guainía","Inírida",3.8653,-67.9239),
    ("Guaviare","San José del Guaviare",2.5729,-72.6459),("Huila","Neiva",2.9273,-75.2819),
    ("La Guajira","Riohacha",11.5444,-72.9072),("Magdalena","Santa Marta",11.2408,-74.1990),
    ("Meta","Villavicencio",4.1420,-73.6266),("Nariño","Pasto",1.2136,-77.2811),
    ("Norte de Santander","Cúcuta",7.8891,-72.4967),("Putumayo","Mocoa",1.1493,-76.6470),
    ("Quindío","Armenia",4.5339,-75.6811),("Risaralda","Pereira",4.8087,-75.6906),
    ("San Andrés y Providencia","San Andrés",12.5847,-81.7006),("Santander","Bucaramanga",7.1193,-73.1227),
    ("Sucre","Sincelejo",9.3047,-75.3978),("Tolima","Ibagué",4.4389,-75.2322),
    ("Valle del Cauca","Cali",3.4516,-76.5320),("Vaupés","Mitú",1.2530,-70.2340),
    ("Vichada","Puerto Carreño",6.1890,-67.4859),
]

def _map_unavailable(msg):
    return html.Div(msg, className="chart-subtitle", style={"padding": "40px 10px", "textAlign": "center"})

def _base_map(lats, lons, height, default_base="topo", pad=0.25):
    """Mapa base común: encuadre ajustado a los datos (no a todo el país)."""
    import folium
    lat_min, lat_max = float(min(lats)), float(max(lats))
    lon_min, lon_max = float(min(lons)), float(max(lons))
    m = folium.Map(location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2], zoom_start=7,
                   tiles=None, control_scale=True, prefer_canvas=True, zoom_control=True,
                   width="100%", height=f"{height}px")
    bases = {
        "claro": dict(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                      attr="Tiles © Esri", name="Fondo claro"),
        "topo": dict(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
                     attr="Tiles © Esri", name="Relieve y vías"),
        "osm": dict(tiles="OpenStreetMap", name="Calles y caminos"),
    }
    order = [default_base] + [k for k in bases if k != default_base]
    for k in order:
        folium.TileLayer(overlay=False, control=True, show=(k == default_base), **bases[k]).add_to(m)

    geojson = load_colombia_departments_geojson()
    m._limits_layer = None
    if isinstance(geojson, dict) and geojson.get("features"):
        # control=False: se activa/desactiva desde el panel «Filtrar la lectura del mapa».
        m._limits_layer = folium.GeoJson(
            geojson, name="Límites departamentales",
            style_function=lambda feature: {"color": "#8FA6C5", "weight": 1.0, "opacity": .85,
                                            "fillColor": "#EAF0F8", "fillOpacity": .06},
            show=True, control=False
        )
        m._limits_layer.add_to(m)
    m._data_bounds = [[lat_min - pad, lon_min - pad], [lat_max + pad, lon_max + pad]]
    m.fit_bounds(m._data_bounds, padding=(10, 10))

    # Fichas homogéneas: a la derecha del elemento y siempre dentro del mapa.
    from branca.element import Element
    m.get_root().html.add_child(Element("""
    <style>
      .leaflet-tooltip.gestion-tooltip {
        white-space: normal !important;
        max-width: 390px !important;
        min-width: 260px;
        max-height: 62vh;
        overflow-y: auto;
        overflow-wrap: anywhere;
        box-sizing: border-box;
        padding: 9px 11px;
        border: 1px solid #C8D5E8;
        border-radius: 8px;
        box-shadow: 0 3px 14px rgba(15, 39, 78, .22);
        color: #1A2540;
        background: rgba(255,255,255,.98);
        font: 12px/1.5 Arial, sans-serif;
        z-index: 10000;
      }
      .leaflet-tooltip.gestion-tooltip:before {
        display: none;
      }
    </style>
    """))
    map_name = m.get_name()
    # Importante: Folium registra primero este bloque en el HTML y crea el
    # objeto Leaflet después. Diferimos la suscripción para evitar ejecutar
    # map.on() antes de que exista el mapa (lo que dejaba el iframe en blanco).
    m.get_root().script.add_child(Element(f"""
    window.setTimeout(function() {{
      const map = {map_name};
      if (!map || !map.on) return;
      map.on('tooltipopen', function(event) {{
        const tooltip = event.tooltip;
        requestAnimationFrame(function() {{
          const el = tooltip.getElement();
          if (!el) return;
          const mapRect = map.getContainer().getBoundingClientRect();
          const tipRect = el.getBoundingClientRect();
          const pad = 18;
          let dx = 0, dy = 0;
          if (tipRect.left < mapRect.left + pad) dx = mapRect.left + pad - tipRect.left;
          if (tipRect.right > mapRect.right - pad) dx = mapRect.right - pad - tipRect.right;
          if (tipRect.top < mapRect.top + pad) dy = mapRect.top + pad - tipRect.top;
          if (tipRect.bottom > mapRect.bottom - pad) dy = mapRect.bottom - pad - tipRect.bottom;
          if (dx !== 0 || dy !== 0) map.panBy([-dx, -dy], {{animate: false}});
        }});
      }});
    }}, 0);
    """))
    return m

def _add_capitals(m, departments):
    """Punto azul + nombre de la capital, solo para los departamentos presentes en los datos."""
    import folium
    present = {_norm(x) for x in departments if x != "Sin dato"}
    group = folium.FeatureGroup(name="Capitales departamentales", show=True, control=False)
    seen = set()
    for dept, cap, lat, lon in DEPARTMENT_CAPITALS:
        if _norm(dept) not in present or cap in seen:
            continue
        seen.add(cap)
        folium.CircleMarker([lat, lon], radius=3, color=NAVY, weight=1, fill=True,
                            fill_color=NAVY, fill_opacity=1, tooltip=f"{cap} (capital de {dept})").add_to(group)
        folium.Marker([lat, lon], icon=folium.DivIcon(
            icon_size=(140, 16), icon_anchor=(-6, 8),
            html=(f"<div style='font:600 11px Arial,sans-serif;color:{NAVY};white-space:nowrap;"
                  f"text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff'>{cap}</div>"))).add_to(group)
    group.add_to(m)
    return group, len(seen)

MAP_HEIGHT = 560          # alto del mapa integrado (px)
MAP_PANEL_WIDTH = 278     # ancho del panel de filtros dentro del mapa (px)

def _map_filter_panel(m, sections, draw_order, height):
    """
    Leyenda interactiva: cada categoría de la leyenda es una casilla que muestra
    u oculta sus elementos en el mapa. Incluye vistas rápidas («Ver todo»,
    «Solo lo crítico», «Ocultar todo») y una casilla por familia de capas.
    Todo ocurre dentro del mapa (sin recargar el tablero).

    sections: [{"title", "unit", "hint", "items": [(key, label, color, shape,
               folium_layer, count, is_critical)], "reference": bool}]
    """
    from branca.element import Element

    layers_js, cfg_sections = [], []
    for sec in sections:
        items = []
        for key, label, color, shape, layer, count, critical in sec["items"]:
            if layer is None:
                continue
            layers_js.append(f"{json.dumps(key)}: {layer.get_name()}")
            items.append({"key": key, "label": label, "color": color, "shape": shape,
                          "count": None if count is None else int(count), "critical": bool(critical)})
        if items:
            cfg_sections.append({"title": sec["title"], "unit": sec.get("unit", ""),
                                 "hint": sec.get("hint", ""), "reference": bool(sec.get("reference")),
                                 "items": items})
    present = {it["key"] for s in cfg_sections for it in s["items"]}
    cfg = {
        "sections": cfg_sections,
        "order": [k for k in draw_order if k in present],
        "bounds": getattr(m, "_data_bounds", None),
        "panelWidth": MAP_PANEL_WIDTH,
    }

    m.get_root().html.add_child(Element(f"""
    <style>
      .mf-panel {{ width:{MAP_PANEL_WIDTH}px; background:rgba(255,255,255,.97); border:1px solid #C8D5E8;
        border-radius:10px; box-shadow:0 3px 14px rgba(15,39,78,.20); font:12px/1.35 Arial,sans-serif;
        color:#1A2540; overflow:hidden; }}
      .mf-head {{ display:flex; align-items:center; justify-content:space-between; gap:8px;
        background:{NAVY}; color:#fff; padding:8px 10px; cursor:pointer; user-select:none; }}
      .mf-head b {{ font-size:12.5px; letter-spacing:.02em; }}
      .mf-head span {{ font-size:11px; opacity:.85; white-space:nowrap; }}
      .mf-body {{ max-height:{height - 70}px; overflow-y:auto; padding:8px 10px 6px; }}
      .mf-panel.collapsed .mf-body {{ display:none; }}
      .mf-presets {{ display:flex; gap:5px; margin-bottom:8px; }}
      .mf-presets button {{ flex:1; border:1px solid #C8D5E8; background:#F4F7FB; color:{NAVY};
        border-radius:6px; padding:5px 3px; font:600 11px Arial,sans-serif; cursor:pointer; }}
      .mf-presets button:hover {{ background:#E3ECFA; border-color:{BLUE}; }}
      .mf-presets button.active {{ background:{BLUE}; border-color:{BLUE}; color:#fff; }}
      .mf-sec {{ border-top:1px solid #E3E9F2; padding:6px 0 4px; }}
      .mf-sec-title {{ display:flex; align-items:center; gap:6px; font-weight:700; color:{NAVY};
        font-size:12px; cursor:pointer; }}
      .mf-hint {{ color:#53627A; font-size:10.5px; margin:1px 0 3px 21px; }}
      .mf-item {{ display:flex; align-items:center; gap:7px; padding:2px 0 2px 21px; cursor:pointer; }}
      .mf-item:hover {{ background:#F4F7FB; border-radius:5px; }}
      .mf-item.off .mf-lbl, .mf-item.off .mf-sym {{ opacity:.35; }}
      .mf-item.empty {{ cursor:default; }}
      .mf-item.empty .mf-lbl, .mf-item.empty .mf-sym, .mf-item.empty .mf-n {{ opacity:.35; }}
      .mf-item input, .mf-sec-title input {{ margin:0; cursor:pointer; accent-color:{BLUE}; }}
      .mf-lbl {{ flex:1; }}
      .mf-n {{ color:#53627A; font-size:11px; font-variant-numeric:tabular-nums; }}
      .mf-sym {{ display:inline-block; flex:0 0 auto; }}
      .mf-sym.line {{ width:20px; height:5px; border-radius:3px; }}
      .mf-sym.dot {{ width:13px; height:13px; border-radius:50%; border:1px solid #fff; box-shadow:0 0 0 1px rgba(0,0,0,.08); }}
      .mf-sym.tower {{ width:9px; height:9px; border-radius:50%; border:1.5px solid #fff; box-shadow:0 0 0 1px rgba(0,0,0,.25); margin:0 2px; }}
      .mf-sym.cap {{ width:6px; height:6px; border-radius:50%; margin:0 4px; }}
      .mf-sym.outline {{ width:14px; height:10px; border:1.5px solid; border-radius:2px; background:transparent !important; }}
      .mf-foot {{ border-top:1px solid #E3E9F2; color:#53627A; font-size:10.5px; padding:6px 0 2px; }}
    </style>
    """))

    m.get_root().script.add_child(Element(f"""
    (function() {{
      var CFG = {json.dumps(cfg, ensure_ascii=False)};
      function init(tries) {{
        var map, layers;
        try {{
          map = {m.get_name()};
          layers = {{{", ".join(layers_js)}}};
        }} catch (e) {{ map = null; }}
        if (!map || !map.addLayer || typeof L === 'undefined') {{
          if (tries < 40) window.setTimeout(function() {{ init(tries + 1); }}, 50);
          return;
        }}
        var state = {{}};
        CFG.order.forEach(function(k) {{ state[k] = true; }});
        var keysBySection = CFG.sections.map(function(s) {{
          return s.items.map(function(it) {{ return it.key; }});
        }});
        var criticalKeys = {{}};
        CFG.sections.forEach(function(s) {{
          s.items.forEach(function(it) {{ if (it.critical || s.reference) criticalKeys[it.key] = true; }});
        }});
        var referenceKeys = {{}};
        CFG.sections.forEach(function(s) {{
          if (s.reference) s.items.forEach(function(it) {{ referenceKeys[it.key] = true; }});
        }});

        function esc(t) {{
          return String(t).replace(/[&<>"]/g, function(c) {{
            return {{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}}[c];
          }});
        }}
        function symbol(it) {{
          var st = it.shape === 'outline' ? 'border-color:' + it.color : 'background:' + it.color;
          return '<span class="mf-sym ' + it.shape + '" style="' + st + '"></span>';
        }}

        var html = '<div class="mf-head" data-act="toggle"><b>Filtrar la lectura del mapa</b>'
                 + '<span class="mf-caret">ocultar</span></div><div class="mf-body">'
                 + '<div class="mf-presets">'
                 + '<button type="button" data-preset="all">Ver todo</button>'
                 + '<button type="button" data-preset="critical">Solo lo crítico</button>'
                 + '<button type="button" data-preset="none">Ocultar todo</button></div>';
        CFG.sections.forEach(function(s, i) {{
          html += '<div class="mf-sec"><label class="mf-sec-title"><input type="checkbox" data-sec="' + i + '">'
                + esc(s.title) + '</label>';
          if (s.hint) html += '<div class="mf-hint">' + esc(s.hint) + '</div>';
          s.items.forEach(function(it) {{
            var empty = it.count === 0;
            var n = it.count === null ? '' : it.count.toLocaleString('es-CO');
            html += '<label class="mf-item' + (empty ? ' empty' : '') + '" data-key="' + it.key + '"'
                  + (s.unit && !empty ? ' title="' + n + ' ' + esc(s.unit) + '"' : '') + '>'
                  + '<input type="checkbox" data-key="' + it.key + '"' + (empty ? ' disabled' : '') + '>'
                  + symbol(it) + '<span class="mf-lbl">' + esc(it.label) + '</span>'
                  + '<span class="mf-n">' + n + '</span></label>';
          }});
          html += '</div>';
        }});
        html += '<div class="mf-foot">Marca o desmarca una categoría para mostrarla u ocultarla. '
              + 'Pasa el cursor sobre una línea, torre o municipio para ver su ficha.</div></div>';

        var panel;
        var Ctl = L.Control.extend({{
          options: {{ position: 'topleft' }},
          onAdd: function() {{
            panel = L.DomUtil.create('div', 'mf-panel');
            panel.innerHTML = html;
            L.DomEvent.disableClickPropagation(panel);
            L.DomEvent.disableScrollPropagation(panel);
            return panel;
          }}
        }});
        map.addControl(new Ctl());

        function redraw() {{
          CFG.order.forEach(function(k) {{
            var l = layers[k];
            if (l && map.hasLayer(l)) map.removeLayer(l);
          }});
          CFG.order.forEach(function(k) {{
            var l = layers[k];
            if (l && state[k]) map.addLayer(l);
          }});
          sync();
        }}
        function sync() {{
          panel.querySelectorAll('input[data-key]').forEach(function(cb) {{
            var k = cb.getAttribute('data-key');
            cb.checked = !!state[k];
            cb.closest('.mf-item').classList.toggle('off', !state[k]);
          }});
          panel.querySelectorAll('input[data-sec]').forEach(function(cb) {{
            var keys = keysBySection[+cb.getAttribute('data-sec')];
            var on = keys.filter(function(k) {{ return state[k]; }}).length;
            cb.checked = on === keys.length;
            cb.indeterminate = on > 0 && on < keys.length;
          }});
          var all = CFG.order.every(function(k) {{ return state[k]; }});
          var crit = CFG.order.every(function(k) {{ return !!state[k] === !!criticalKeys[k]; }});
          var none = CFG.order.every(function(k) {{ return !!state[k] === !!referenceKeys[k]; }});
          panel.querySelectorAll('button[data-preset]').forEach(function(b) {{
            var p = b.getAttribute('data-preset');
            b.classList.toggle('active', (p === 'all' && all) || (p === 'critical' && crit && !all) || (p === 'none' && none && !all));
          }});
        }}

        panel.addEventListener('change', function(ev) {{
          var t = ev.target;
          if (t.hasAttribute('data-key')) {{
            state[t.getAttribute('data-key')] = t.checked;
          }} else if (t.hasAttribute('data-sec')) {{
            keysBySection[+t.getAttribute('data-sec')].forEach(function(k) {{ state[k] = t.checked; }});
          }}
          redraw();
        }});
        panel.addEventListener('click', function(ev) {{
          var b = ev.target.closest('button[data-preset]');
          if (b) {{
            var p = b.getAttribute('data-preset');
            CFG.order.forEach(function(k) {{
              state[k] = p === 'all' ? true : (p === 'critical' ? !!criticalKeys[k] : !!referenceKeys[k]);
            }});
            redraw();
            return;
          }}
          if (ev.target.closest('[data-act="toggle"]')) {{
            var collapsed = panel.classList.toggle('collapsed');
            panel.querySelector('.mf-caret').textContent = collapsed ? 'mostrar' : 'ocultar';
          }}
        }});

        // En pantallas angostas el panel inicia plegado; en escritorio se deja
        // libre la franja que ocupa el panel al encuadrar los datos.
        var w = map.getContainer().clientWidth;
        if (w < 700) {{
          panel.classList.add('collapsed');
          panel.querySelector('.mf-caret').textContent = 'mostrar';
        }} else if (CFG.bounds) {{
          map.fitBounds(CFG.bounds, {{ paddingTopLeft: [CFG.panelWidth + 24, 12], paddingBottomRight: [12, 12] }});
        }}
        redraw();
      }}
      window.setTimeout(function() {{ init(0); }}, 0);
    }})();
    """))

def _iframe(m, title, height):
    return html.Iframe(
        srcDoc=m.get_root().render(), title=title,
        style={"width": "100%", "height": f"{height}px", "border": "0", "borderRadius": "8px", "display": "block"}
    )

def integrated_map(d):
    """
    Mapa integrado de red y riesgo municipal.
    Reúne en una sola vista las capas que antes estaban separadas:
    líneas de transmisión, torres, torres con vencidos y municipios.
    """
    try:
        import folium
    except ImportError:
        return _map_unavailable("Para visualizar el mapa integrado instala folium (pip install folium).")

    # Capa municipal: volumen total y estado del backlog por municipio.
    municipal = d.dropna(subset=["Latitud", "Longitud"]).copy()
    if not municipal.empty:
        municipal["Ubicación"] = municipal["Municipio"].astype(str) + ", " + municipal["Departamento"].astype(str)
        municipal = _flags(municipal).groupby(
            ["Ubicación", "Municipio", "Departamento"]
        ).agg(
            Latitud=("Latitud", "median"),
            Longitud=("Longitud", "median"),
            Avisos=("Aviso", "nunique"),
            Cerrados=("_cerr", "sum"),
            Cerrados_a_tiempo=("_cerr_ok", "sum"),
            Cerrados_atrasados=("_cerr_late", "sum"),
            Pendientes=("_abierto", "sum"),
            Pendientes_en_plazo=("_abierto_ok", "sum"),
            Vencidos=("_venc", "sum"),
            Mediana_dias_abierto=("_dias_abierto", "median"),
            Max_dias_abierto=("_dias_abierto", "max"),
            Mediana_dias_cierre=("_dias_cierre", "median"),
            Torres=("Torre", "nunique"),
            Lineas=("Linea", "nunique"),
            Tipo_predominante=("Tipo de aviso", _mode),
            Prioridad_predominante=("Prioridad", _mode),
            CTE=("CTE", _mode),
        ).reset_index()
        municipal["% pendientes"] = np.where(
            municipal["Avisos"] > 0,
            municipal["Pendientes"] / municipal["Avisos"] * 100,
            0
        )
        municipal["% cierres a tiempo"] = np.where(
            municipal["Cerrados"] > 0,
            municipal["Cerrados_a_tiempo"] / municipal["Cerrados"] * 100,
            np.nan
        )

    # Capas de red: estadísticas agregadas por línea y torre.
    towers = build_tower_stats(d)
    lines = build_line_stats(d)
    if not towers.empty and not lines.empty:
        lines = lines.set_index("Linea")
    else:
        lines = pd.DataFrame()

    # Un único encuadre que incluye todas las coordenadas de ambas vistas.
    lat_parts, lon_parts, departments = [], [], []
    if not municipal.empty:
        lat_parts.append(municipal["Latitud"].astype(float))
        lon_parts.append(municipal["Longitud"].astype(float))
        departments.extend(municipal["Departamento"].dropna().astype(str).tolist())
    if not towers.empty:
        lat_parts.append(towers["Lat"].astype(float))
        lon_parts.append(towers["Lon"].astype(float))
        departments.extend(towers["Departamento"].dropna().astype(str).tolist())

    if not lat_parts:
        return _map_unavailable("No hay coordenadas de municipios o torres para los filtros seleccionados.")

    all_lats = pd.concat(lat_parts, ignore_index=True)
    all_lons = pd.concat(lon_parts, ignore_index=True)
    height = MAP_HEIGHT
    m = _base_map(all_lats, all_lons, height, default_base="topo", pad=0.18)
    capitals_group, n_capitals = _add_capitals(m, departments)

    def _pending_color(value):
        if value < 33.333:
            return GREEN
        if value < 66.667:
            return AMBER
        return RED

    # Cada categoría de la leyenda es un grupo propio, para poder mostrarla u
    # ocultarla desde el panel «Filtrar la lectura del mapa».
    def _group(name):
        return folium.FeatureGroup(name=name, show=True, control=False)

    muni_groups = {c: _group(f"Municipios {c}") for c in (GREEN, AMBER, RED)}
    line_groups = {c: _group(f"Líneas {c}") for c in (NEUTRAL, GREEN, AMBER, RED)}
    tower_groups = {c: _group(f"Torres {c}") for c in (GREEN, AMBER, RED)}
    n_muni = {c: 0 for c in muni_groups}
    n_line = {c: 0 for c in line_groups}
    n_tower = {c: 0 for c in tower_groups}

    # 1. Municipios: tamaño por volumen total y color por proporción pendiente.
    if not municipal.empty:
        for _, r in municipal.sort_values("Avisos", ascending=False).iterrows():
            radius = float(np.clip(4 + np.sqrt(max(float(r["Avisos"]) - 1, 0)) * 4.1, 4, 18))
            med_open = f"{fmt_int(r['Mediana_dias_abierto'])} días" if not pd.isna(r["Mediana_dias_abierto"]) else "—"
            max_open = f"{fmt_int(r['Max_dias_abierto'])} días" if not pd.isna(r["Max_dias_abierto"]) else "—"
            med_close = f"{fmt_int(r['Mediana_dias_cierre'])} días" if not pd.isna(r["Mediana_dias_cierre"]) else "—"
            close_rate = fmt_pct(r["% cierres a tiempo"]) if not pd.isna(r["% cierres a tiempo"]) else "Sin cierres"
            color = _pending_color(float(r["% pendientes"]))
            popup = (
                f"<div style='font:12px/1.5 Arial,sans-serif;min-width:250px;color:#1A2540'>"
                f"<b style='font-size:14px;color:{NAVY}'>Municipio: {r['Ubicación']}</b><hr style='margin:5px 0;border:0;border-top:1px solid #D8E0EC'>"
                f"<b>Inventario de avisos</b><br>"
                f"Total registrados: <b>{fmt_int(r['Avisos'])}</b><br>"
                f"Cerrados: {fmt_int(r['Cerrados'])} · Pendientes: {fmt_int(r['Pendientes'])}<br>"
                f"Pendientes vencidos: <b style='color:{RED}'>{fmt_int(r['Vencidos'])}</b><br>"
                f"Pendientes dentro del plazo: {fmt_int(r['Pendientes_en_plazo'])}<br>"
                f"Cerrados a tiempo: {fmt_int(r['Cerrados_a_tiempo'])} · Cerrados atrasados: {fmt_int(r['Cerrados_atrasados'])}<br>"
                f"<b>Indicadores de gestión</b><br>"
                f"% de avisos pendientes: <b style='color:{color}'>{fmt_pct(r['% pendientes'])}</b><br>"
                f"% de cierres a tiempo: <b>{close_rate}</b><br>"
                f"Antigüedad mediana de pendientes: {med_open}<br>"
                f"Pendiente más antiguo: {max_open}<br>"
                f"Tiempo mediano de cierre: {med_close}</div>"
            )
            folium.CircleMarker(
                location=[float(r["Latitud"]), float(r["Longitud"])],
                radius=radius, color="#FFFFFF", weight=1,
                fill=True, fill_color=color, fill_opacity=.80,
                tooltip=folium.Tooltip(popup, sticky=True, direction="right", offset=(14, 0), class_name="gestion-tooltip"),
            ).add_to(muni_groups[color])
            n_muni[color] += 1

    # 2. Líneas de transmisión: color por cumplimiento y grosor por pendientes.
    if not lines.empty:
        for line_code in lines.sort_values("Abiertos").index:
            tw = towers[towers["Linea"].eq(line_code)]
            if tw.empty:
                continue
            r = lines.loc[line_code]
            rate = r["Cumplimiento"]
            evaluable = r["Cerrados"] >= MIN_CERRADOS_LINEA
            color = sla_color(rate) if evaluable else NEUTRAL
            group = line_groups[color]
            weight = float(np.clip(2.5 + np.sqrt(float(r["Abiertos"])) * 0.65, 2.5, 10))
            rate_txt = fmt_pct(rate) if not pd.isna(rate) else "sin cierres"
            if not evaluable and not pd.isna(rate):
                rate_txt += f" (menos de {MIN_CERRADOS_LINEA} cierres: no evaluable)"
            med_txt = f"{fmt_int(r['Mediana_dias'])} días" if not pd.isna(r["Mediana_dias"]) else "—"
            tip = (
                f"<b style='font-size:14px;color:{NAVY}'>Línea {line_code}</b><br>"
                f"Cumplimiento de cierres: <b style='color:{color}'>{rate_txt}</b> (meta {META_SLA:.0f} %)<br>"
                f"Avisos: {fmt_int(r['Avisos'])} · Cerrados: {fmt_int(r['Cerrados'])}<br>"
                f"Pendientes: {fmt_int(r['Abiertos'])} · Vencidos: <b>{fmt_int(r['Vencidos'])}</b><br>"
                f"Mediana al cierre: {med_txt}<br>"
                f"Torres con avisos: {fmt_int(r['Torres'])} · Tipo predominante: {r['Tipo']}<br>"
                f"CTE: {r['CTE']} · {r['Departamentos']}"
            )
            coords = tw[["Lat", "Lon"]].astype(float).values.tolist()
            if len(coords) >= 2:
                folium.PolyLine(coords, color="#FFFFFF", weight=weight + 3, opacity=.88).add_to(group)
                folium.PolyLine(
                    coords, color=color, weight=weight, opacity=.9,
                    tooltip=folium.Tooltip(tip, sticky=True, direction="right", offset=(14, 0), class_name="gestion-tooltip")
                ).add_to(group)
            elif len(coords) == 1:
                folium.CircleMarker(
                    coords[0], radius=weight, color="#FFFFFF", weight=1, fill=True,
                    fill_color=color, fill_opacity=.95, tooltip=folium.Tooltip(tip, sticky=True, direction="right", offset=(14, 0), class_name="gestion-tooltip")
                ).add_to(group)
            n_line[color] += 1

    # 3. Torres: un marcador y una ficha de gestión por torre.
    if not towers.empty:
        for _, t in towers.iterrows():
            radius = float(np.clip(3.5 + np.sqrt(max(float(t["Avisos"]), 1)) * 0.8, 3.5, 10))
            med_open = (
                f"{fmt_int(t['Mediana_dias_abierto'])} días"
                if not pd.isna(t["Mediana_dias_abierto"]) else "—"
            )
            max_open = (
                f"{fmt_int(t['Max_dias_abierto'])} días"
                if not pd.isna(t["Max_dias_abierto"]) else "—"
            )
            med_close = (
                f"{fmt_int(t['Mediana_dias_cierre'])} días"
                if not pd.isna(t["Mediana_dias_cierre"]) else "—"
            )
            compliance = (
                fmt_pct(t["Cumplimiento"])
                if not pd.isna(t["Cumplimiento"]) else "Sin cierres"
            )
            overdue_color = RED if int(t["Vencidos"]) > 0 else (
                GREEN if int(t["Abiertos"]) == 0 else AMBER
            )
            tower_tip = (
                f"<div style='font:12px/1.5 Arial,sans-serif;min-width:255px;color:#1A2540'>"
                f"<b style='font-size:14px;color:{NAVY}'>Torre {t['Torre']} · Línea {t['Linea']}</b><br>"
                f"{t['Municipio']}, {t['Departamento']}"
                f"<hr style='margin:5px 0;border:0;border-top:1px solid #D8E0EC'>"
                f"<b>Inventario de avisos</b><br>"
                f"Total registrados: <b>{fmt_int(t['Avisos'])}</b><br>"
                f"Cerrados: {fmt_int(t['Cerrados'])} · Pendientes: {fmt_int(t['Abiertos'])}<br>"
                f"Pendientes dentro del plazo: {fmt_int(t['Pendientes_en_plazo'])}<br>"
                f"Pendientes vencidos: <b style='color:{overdue_color}'>{fmt_int(t['Vencidos'])}</b><br>"
                f"Cerrados a tiempo: {fmt_int(t['Cerrados_a_tiempo'])} · Cerrados atrasados: "
                f"{fmt_int(t['Cerrados_atrasados'])}<br>"
                f"<b>Indicadores de gestión</b><br>"
                f"Cumplimiento de cierres: <b>{compliance}</b> (meta {META_SLA:.0f} %)<br>"
                f"Antigüedad mediana de pendientes: {med_open}<br>"
                f"Pendiente más antiguo: {max_open}<br>"
                f"Tiempo mediano de cierre: {med_close}</div>"
            )
            folium.CircleMarker(
                [float(t["Lat"]), float(t["Lon"])],
                radius=radius, color="#FFFFFF", weight=1.5, fill=True,
                fill_color=overdue_color, fill_opacity=.96,
                tooltip=folium.Tooltip(tower_tip, sticky=True, direction="right", offset=(14, 0), class_name="gestion-tooltip"),
            ).add_to(tower_groups[overdue_color])
            n_tower[overdue_color] += 1

    # Orden de dibujo: municipios (al fondo) → líneas → torres → capitales (encima).
    # Dentro de cada familia, la categoría crítica queda encima.
    for c in (GREEN, AMBER, RED):
        muni_groups[c].add_to(m)
    for c in (NEUTRAL, GREEN, AMBER, RED):
        line_groups[c].add_to(m)
    for c in (GREEN, AMBER, RED):
        tower_groups[c].add_to(m)

    # El control de Leaflet queda solo para elegir el fondo cartográfico.
    folium.LayerControl(collapsed=True, position="topright").add_to(m)

    meta = f"{META_SLA:.0f} %"
    warn = f"{META_SLA - BANDA_ALERTA:.0f}"
    sections = [
        {"title": "Líneas de transmisión", "unit": "líneas",
         "hint": "Color = cumplimiento de cierres a tiempo · grosor = avisos pendientes",
         "items": [
             ("line_crit", f"Crítica (menos de {warn} %)", RED, "line", line_groups[RED], n_line[RED], True),
             ("line_risk", f"En riesgo ({warn} a {META_SLA - 0.1:.1f} %)".replace(".", ","), AMBER, "line", line_groups[AMBER], n_line[AMBER], False),
             ("line_ok", f"Cumple la meta ({meta} o más)", GREEN, "line", line_groups[GREEN], n_line[GREEN], False),
             ("line_ne", f"No evaluable (< {MIN_CERRADOS_LINEA} cierres)", NEUTRAL, "line", line_groups[NEUTRAL], n_line[NEUTRAL], False),
         ]},
        {"title": "Torres", "unit": "torres",
         "hint": "Color = situación de sus avisos abiertos · tamaño = avisos registrados",
         "items": [
             ("tower_red", "Con pendientes vencidos", RED, "tower", tower_groups[RED], n_tower[RED], True),
             ("tower_amber", "Con pendientes no vencidos", AMBER, "tower", tower_groups[AMBER], n_tower[AMBER], False),
             ("tower_green", "Sin pendientes", GREEN, "tower", tower_groups[GREEN], n_tower[GREEN], False),
         ]},
        {"title": "Municipios", "unit": "municipios",
         "hint": "Color = % de sus avisos que sigue abierto · tamaño = avisos registrados",
         "items": [
             ("muni_red", "Alto: 67 % a 100 % pendiente", RED, "dot", muni_groups[RED], n_muni[RED], True),
             ("muni_amber", "Medio: 34 % a 66 % pendiente", AMBER, "dot", muni_groups[AMBER], n_muni[AMBER], False),
             ("muni_green", "Bajo: 0 % a 33 % pendiente", GREEN, "dot", muni_groups[GREEN], n_muni[GREEN], False),
         ]},
    ]
    refs = [("cap", "Capitales departamentales", NAVY, "cap", capitals_group, n_capitals, False)]
    if getattr(m, "_limits_layer", None) is not None:
        refs.append(("limits", "Límites departamentales", "#8FA6C5", "outline", m._limits_layer, None, False))
    sections.append({"title": "Referencias", "unit": "", "hint": "", "items": refs, "reference": True})

    # Orden en que se vuelven a dibujar las capas al filtrar (igual al inicial).
    draw_order = ["limits", "muni_green", "muni_amber", "muni_red",
                  "line_ne", "line_ok", "line_risk", "line_crit",
                  "tower_green", "tower_amber", "tower_red", "cap"]
    _map_filter_panel(m, sections, draw_order, height)
    return _iframe(m, "Mapa integrado de red y riesgo municipal", height)

def line_performance(d):
    s = build_line_stats(d)
    s = s[s["Cerrados"] >= MIN_CERRADOS_LINEA] if not s.empty else s
    if s.empty:
        return empty_fig(f"Ninguna línea tiene al menos {MIN_CERRADOS_LINEA} cierres con estos filtros.")
    s = s.sort_values(["Cumplimiento", "Vencidos"], ascending=[True, False]).head(12)
    order = s["Linea"].tolist()

    fig = go.Figure(go.Bar(
        y=s["Linea"], x=s["Cumplimiento"], orientation="h",
        text=s["Cumplimiento"].map(lambda v: f"{v:.0f}%"), textposition="outside", cliponaxis=False,
        marker=dict(color=[sla_color(v) for v in s["Cumplimiento"]], cornerradius=6, line=dict(width=0)),
        customdata=s[["Cerrados", "Abiertos", "Vencidos", "Departamentos"]],
        hovertemplate=("<b>Línea %{y}</b> (Clic para filtrar)<br>Cumplimiento: %{x:.1f}%<br>"
                       "Cerrados: %{customdata[0]:,} · Pendientes: %{customdata[1]:,} · Vencidos: %{customdata[2]:,}<br>"
                       "%{customdata[3]}<extra></extra>")
    ))
    meta_line(fig, META_SLA, "h")
    fig.update_layout(
        xaxis_title="% de cierres a tiempo (Clic en una línea para filtrar)", yaxis_title="",
        margin=dict(l=left_margin_for(order), r=36, t=34, b=48),
        yaxis=dict(categoryorder="array", categoryarray=order, autorange="reversed"),
    )
    fig.update_xaxes(range=[0, 108], ticksuffix="%", showgrid=True, gridcolor=GRID)
    base_layout(fig, 350, False)
    meta_label_outside(fig, META_SLA, "h", f"Meta {META_SLA:.0f} %")
    labels_clear_of_meta(fig, s["Linea"], s["Cumplimiento"],
                         s["Cumplimiento"].map(lambda v: f"{v:.0f}%"), META_SLA, 108, "h")
    return fig

# ============================================================
# PÁGINAS
# ============================================================

MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def _years_text(ys):
    """2020, 2021 y 2022 → «2020, 2021 y 2022»; años consecutivos → «2020–2022»."""
    ys = sorted(int(y) for y in ys)
    if not ys:
        return ""
    if len(ys) >= 3 and ys == list(range(ys[0], ys[-1] + 1)):
        return f"{ys[0]}–{ys[-1]}"
    ys = [str(y) for y in ys]
    return ys[0] if len(ys) == 1 else ", ".join(ys[:-1]) + " y " + ys[-1]

def summary_findings(d):
    """Hallazgos del Resumen gerencial calculados con los filtros vigentes."""
    f = {}
    n = len(d)
    closed = d[d["Estado aviso"].eq("Cerrado")]
    opened = d[d["Estado aviso"].eq("Abierto")]
    venc = int(opened["Tiempo aviso"].eq("Atrasado").sum())
    late = int(closed["Tiempo aviso"].eq("Atrasado").sum())
    sin_datos = "No hay avisos con los filtros seleccionados."

    # --- 1. Estado de los avisos -----------------------------------------------
    if n == 0:
        f["status"] = sin_datos
    else:
        if opened.empty:
            txt = f"Todos los {fmt_int(n)} avisos están cerrados."
        elif closed.empty:
            txt = f"Los {fmt_int(n)} avisos siguen abiertos"
            txt += f" ({fmt_int(venc)} de ellos ya vencidos)." if venc else "."
        else:
            txt = (f"{fmt_int(len(closed))} de {fmt_int(n)} avisos están cerrados y "
                   f"{fmt_int(len(opened))} siguen abiertos")
            txt += f" ({fmt_int(venc)} de ellos ya vencidos)." if venc else "."
        by_year = d.groupby("Año")["Estado aviso"].agg(
            n="size", rate=lambda s: s.eq("Cerrado").mean() * 100)
        by_year = by_year[by_year["n"] >= 10]
        if len(by_year) >= 2 and by_year["rate"].max() - by_year["rate"].min() >= 1:
            low = by_year[by_year["rate"] < META_SLA]
            high = by_year[by_year["rate"] >= META_SLA]
            if len(low) and len(high) and low.index.min() > high.index.max():
                txt += (f" Hasta {int(high.index.max())} cada año tiene cerrado el {META_SLA:.0f} % o más de sus avisos; "
                        f"desde {int(low.index.min())} la tasa baja hasta {fmt_pct(low['rate'].min())} "
                        f"({int(low['rate'].idxmin())}), porque son avisos más recientes aún en gestión.")
            else:
                txt += (f" Por año de aviso, la tasa de cierre va de {fmt_pct(by_year['rate'].min())} "
                        f"({int(by_year['rate'].idxmin())}) a {fmt_pct(by_year['rate'].max())} "
                        f"({int(by_year['rate'].idxmax())}).")
        f["status"] = txt + " Clic en «Cerrado» o «Abierto» para filtrar."

    # --- 2. Cumplimiento de los cierres -------------------------------------------
    if closed.empty:
        f["comp"] = "No hay avisos cerrados con los filtros seleccionados."
    else:
        txt = f"{fmt_int(late)} de {fmt_int(len(closed))} cierres llegaron después del plazo."
        yc = closed.groupby(closed["Fecha de cierre"].dt.year)["Tiempo aviso"].agg(
            n="size", rate=lambda s: s.eq("A tiempo").mean() * 100)
        yc = yc[yc["n"] >= 30]
        if len(yc) >= 2:
            ok = int((yc["rate"] >= META_SLA).sum())
            txt += (f" Por año de cierre (años con 30 cierres o más), el mejor resultado fue "
                    f"{int(yc['rate'].idxmax())} ({fmt_pct(yc['rate'].max())}) y el más bajo "
                    f"{int(yc['rate'].idxmin())} ({fmt_pct(yc['rate'].min())}); ")
            txt += ("ningún año alcanza la meta." if ok == 0 else
                    f"solo {ok} de {len(yc)} años alcanza{'n' if ok > 1 else ''} la meta.")
        f["comp"] = txt + " Clic en «A tiempo» o «Atrasado» para filtrar."

    # --- 3. Ritmo mensual ----------------------------------------------------
    f["trend_title"] = "Ritmo mensual de ingresos frente a la capacidad real de cierre"
    if n == 0:
        f["trend"] = sin_datos
    else:
        rec = d.groupby(d["Fecha de aviso"].dt.to_period("M")).size()
        cer = closed.groupby(closed["Fecha de cierre"].dt.to_period("M")).size()
        g = pd.concat([rec.rename("r"), cer.rename("c")], axis=1, sort=False).fillna(0).sort_index()
        mean_r, mean_c = g["r"].mean(), g["c"].mean()
        both_states = not opened.empty and not closed.empty
        if not both_states:
            pass   # con filtro de estado, la comparación ingresos/cierres no es representativa
        elif mean_r > mean_c:
            f["trend_title"] = (f"Ingresan más avisos de los que se cierran: {fmt_int(mean_r)} al mes "
                                f"frente a {fmt_int(mean_c)} cierres en promedio")
        else:
            f["trend_title"] = (f"La capacidad de cierre acompaña los ingresos: {fmt_int(mean_c)} cierres "
                                f"al mes frente a {fmt_int(mean_r)} avisos recibidos en promedio")
        peak = g["r"].idxmax()
        txt = (f"En {fmt_int(int((g['r'] > g['c']).sum()))} de {fmt_int(len(g))} meses ingresaron más avisos "
               f"de los que se cerraron. El mayor pico fue {MESES_ES[peak.month - 1]} de {peak.year} "
               f"({fmt_int(g.loc[peak, 'r'])} avisos)")
        txt += (f", y ese mes solo se cerraron {fmt_int(g.loc[peak, 'c'])}."
                if g.loc[peak, "c"] < g.loc[peak, "r"] else ".")
        last = g[g.index > g.index.max() - 12]
        if both_states and len(last) >= 6:
            bal = int(last["r"].sum() - last["c"].sum())
            txt += (f" En los últimos 12 meses ingresaron {fmt_int(last['r'].sum())} avisos y se cerraron "
                    f"{fmt_int(last['c'].sum())}: " +
                    (f"el pendiente creció en {fmt_int(bal)}." if bal > 0 else
                     f"el pendiente se redujo en {fmt_int(-bal)}." if bal < 0 else "el pendiente se mantuvo estable."))
        f["trend"] = (txt + " Los avisos recibidos y cerrados en un mes no son necesariamente los mismos. "
                      "Clic en un punto para filtrar su año.")

    # --- 4. Abiertos por año de aviso -----------------------------------------
    if opened.empty:
        f["annual"] = ("No quedan avisos abiertos con los filtros seleccionados. "
                       "Clic en una barra para filtrar su año.")
    else:
        oy = opened["Año"].dropna().astype(int).value_counts().sort_index()
        if len(oy) <= 3:
            txt = (f"Todos los {fmt_int(len(opened))} avisos abiertos provienen de "
                   f"{_years_text(oy.index)}.")
            recent = oy.index
        else:
            recent = oy.index[-3:]
            share = pct(int(oy.loc[recent].sum()), len(opened))
            txt = (f"Los años {_years_text(recent)} concentran {fmt_int(oy.loc[recent].sum())} de los "
                   f"{fmt_int(len(opened))} avisos abiertos ({fmt_pct(share)}).")
        older = oy[oy.index < recent.min()]
        if len(older):
            txt += (f" De los años anteriores quedan {fmt_int(older.sum())} abiertos; el más antiguo es de "
                    f"{int(older.index.min())}, por lo que el rezago no es solo reciente.")
        if PARTIAL_YEAR in oy.index:
            txt += f" {PARTIAL_YEAR} es parcial (avisos hasta mayo)."
        f["annual"] = txt + " Clic en una barra para filtrar su año."
    return f

def page_resumen(d, years, types, depts, prios, extra):
    closed = d[d["Estado aviso"].eq("Cerrado")]
    opened = d[d["Estado aviso"].eq("Abierto")]
    ontime = int(closed["Tiempo aviso"].eq("A tiempo").sum())
    late = int(closed["Tiempo aviso"].eq("Atrasado").sum())
    pct_closed = pct(len(closed), len(d)) if len(d) else 0
    pct_ontime = pct(ontime, ontime + late) if (ontime + late) else 0
    f = summary_findings(d)

    if not opened.empty:
        top_year_open = int(opened["Año"].value_counts().idxmax())
        top_year_cnt = int(opened["Año"].value_counts().max())
        backlog_title = f"El año {top_year_open} concentra la mayor carga de avisos aún abiertos ({fmt_int(top_year_cnt)})"
    else:
        backlog_title = "Volumen histórico y pendientes actuales por año de aviso"

    synthesis = [
        ("Desempeño de volumen: ",
         f"de {fmt_int(len(d))} avisos analizados se ha cerrado el {fmt_pct(pct_closed)} y permanece abierto "
         f"el {fmt_pct(100 - pct_closed)} ({fmt_int(len(opened))} casos)."),
        ("Calidad de atención: ",
         f"{fmt_int(late)} cierres incumplieron el plazo; el cumplimiento ({fmt_pct(pct_ontime)}) está "
         f"{fmt_pts(pct_ontime - META_SLA)} frente a la meta. Revisar causas en «Cumplimiento y plazos»."),
        ("Alerta gerencial: ",
         f"{fmt_int(opened['Tiempo aviso'].eq('Atrasado').sum())} avisos abiertos ya superaron su fecha límite "
         f"al corte de la base ({FECHA_CORTE}). Ver detalle en «Pendientes por cumplir»."),
    ] if len(d) else []
    if synthesis and f["trend_title"] != "Ritmo mensual de ingresos frente a la capacidad real de cierre":
        synthesis.insert(2, ("Ritmo de atención: ", f["trend_title"][0].lower() + f["trend_title"][1:] + "."))

    return html.Div([
        header("Resumen gerencial del contrato",
               "Monitoreo estratégico 2011–2023: volumen atendido, eficiencia de cierre y pasivo operativo.",
               years, types, depts, prios, extra),
        html.Div(kpis(d), className="kpi-row kpi-row-six"),
        html.Div([
            card(f"El {fmt_pct(pct_closed)} de los avisos registrados ya fueron cerrados ({fmt_int(len(closed))})",
                 status_donut(d), f["status"], chart_key="status-donut"),
            card(f"El {fmt_pct(pct_ontime)} de los cierres se realizó dentro del plazo: "
                 f"{fmt_pts(pct_ontime - META_SLA)} frente a la meta de {META_SLA:.0f} %",
                 closed_compliance_donut(d), f["comp"], chart_key="comp-donut")
        ], className="charts-2col"),
        html.Div([
            card(f["trend_title"], trend_incoming_closed(d), f["trend"], chart_key="trend-inc"),
            card(backlog_title, annual_backlog(d), f["annual"], chart_key="annual-backlog")
        ], className="charts-2col"),
        html.Div([
            html.Div("Síntesis ejecutiva para toma de decisiones", className="chart-title"),
            *[html.P([html.B(lbl), txt], className="analysis-item") for lbl, txt in synthesis],
        ], className="chart-card analysis-card") if synthesis else None,
    ])

def page_cumplimiento(d, years, types, depts, prios, extra):
    closed = d[d["Estado aviso"].eq("Cerrado")]
    if not closed.empty:
        g_type = closed.groupby("Tipo de aviso")["Tiempo aviso"].apply(lambda s: (s == "Atrasado").mean() * 100)
        type_title = f"'{g_type.idxmax()}' presenta la mayor tasa de cierres atrasados ({fmt_pct(g_type.max())})"
        g_prio = closed.groupby("Prioridad")["Tiempo aviso"].apply(lambda s: (s == "A tiempo").mean() * 100)
        worst_p = g_prio.idxmin()
        prio_title = (f"Las prioridades más urgentes son las que menos se cumplen: "
                      f"'{worst_p}' llega solo al {fmt_pct(g_prio.min())}")
    else:
        type_title = "Proporción de avisos cerrados atrasados por tipo"
        prio_title = "Cumplimiento de plazos según el nivel de prioridad asignado"

    return html.Div([
        header("Cumplimiento y tiempos de solución",
               "Evaluación de compromisos contractuales, dispersión de tiempos de respuesta y cuellos de botella por tipología.",
               years, types, depts, prios, extra),
        html.Div(compliance_kpis(d), className="kpi-row kpi-row-six"),
        html.Div([
            card(prio_title,
                 compliance_by_priority(d),
                 "Verde: cumple la meta · ámbar: a menos de 20 pts · rojo: crítico. Clic en una barra para filtrar.",
                 chart_key="comp-prio"),
            card(type_title,
                 late_by_type(d),
                 "Con meta de 80 %, como máximo un 20 % de los cierres puede llegar tarde. Clic en una barra para filtrar.",
                 chart_key="late-type")
        ], className="charts-2col"),
        card("Distribución real de tiempos de atención (Días abierto) según Prioridad",
             duration_distribution_by_priority(d),
             "Compara medianas y rangos de atención por prioridad (más oscuro = más urgente). Haz clic en una caja para filtrar.",
             chart_key="box-prio"),
        card("Evolución histórica del porcentaje de cumplimiento mensual",
             monthly_closed_compliance(d),
             "Cada punto se colorea frente a la meta (verde ≥ 80 %, ámbar 60–79 %, rojo < 60 %). Clic en un punto para filtrar su año.",
             chart_key="month-comp")
    ])

def pending_findings(o):
    """
    Hallazgos del backlog (avisos abiertos) calculados con los filtros vigentes.
    Devuelve títulos, textos de análisis y viñetas de síntesis.
    """
    n = len(o)
    late_mask = o["Tiempo aviso"].eq("Atrasado")
    venc = int(late_mask.sum())
    en_plazo = int(o["Tiempo aviso"].eq("A tiempo").sum())
    pct_venc = pct(venc, n)
    f = {}

    # --- 1. Situación frente al plazo -------------------------------------
    if n == 0:
        f["status"] = "No hay avisos pendientes con los filtros seleccionados."
    else:
        txt = (f"{fmt_int(venc)} de {fmt_int(n)} pendientes ya superaron su plazo" if venc
               else f"Ninguno de los {fmt_int(n)} pendientes ha superado su plazo")
        v = o[late_mask]
        atraso = (v["Días abierto"] - v["Prioridad días"]).dropna()
        if not atraso.empty:
            txt += (f", con un atraso mediano de {fmt_int(atraso.median())} días "
                    f"(el más rezagado supera su plazo en {fmt_int(atraso.max())} días)")
        txt += "."
        if venc and en_plazo:
            txt += f" Los {fmt_int(en_plazo)} restantes siguen dentro del plazo y aún pueden cerrarse a tiempo."
        if venc:
            by_p = v["Prioridad"].value_counts()
            txt += (f" La prioridad «{by_p.idxmax()}» aporta más vencidos "
                    f"({fmt_int(by_p.max())}, {fmt_pct(pct(by_p.max(), venc))} del total vencido).")
        f["status"] = txt + " Clic en un segmento para filtrar."

    # --- 2. Antigüedad -----------------------------------------------------
    if n == 0:
        f["age_title"] = "Estructura de envejecimiento de los avisos abiertos"
        f["age"] = "No hay avisos pendientes con los filtros seleccionados."
    else:
        days = o["Días abierto"]
        over_1y = days > 365
        f["age_title"] = (f"El {fmt_pct(pct(int(over_1y.sum()), n))} de los pendientes "
                          f"lleva más de un año abierto")
        counts = o["Antigüedad"].value_counts().reindex(AGE_LABELS, fill_value=0)
        txt = f"El grupo más numeroso es «{counts.idxmax()}» ({fmt_int(counts.max())} avisos)."
        old = o[days > 1460]
        if len(old):
            txt += f" {fmt_int(len(old))} avisos superan los 4 años"
            prios_old = old["Prioridad"].value_counts()
            if len(prios_old) == 1:
                txt += f", todos de prioridad «{prios_old.index[0]}»"
            old_venc = int(old["Tiempo aviso"].eq("Atrasado").sum())
            txt += f" ({fmt_int(old_venc)} ya vencidos)." if old_venc else "."
        young, aged = o[~over_1y], o[over_1y]
        if len(young) and len(aged):
            r_young = pct(int(young["Tiempo aviso"].eq("Atrasado").sum()), len(young))
            r_aged = pct(int(aged["Tiempo aviso"].eq("Atrasado").sum()), len(aged))
            f["aging_grows"] = r_aged > r_young
            if abs(r_aged - r_young) >= 1:   # solo si la comparación aporta información
                intro = (" El vencimiento crece con la antigüedad:" if r_aged > r_young
                         else " Los pendientes recientes están más vencidos que los antiguos:")
                txt += (f"{intro} está vencido el {fmt_pct(r_young)} de los pendientes de hasta un año, "
                        f"frente al {fmt_pct(r_aged)} de los que superan un año.")
        f["age"] = txt + " Clic en una barra para aislar ese grupo."

    # --- 3. Tipología ------------------------------------------------------
    f["type_title"] = "Concentración del backlog por tipología y estado de vencimiento"
    if n == 0:
        f["type"] = "No hay avisos pendientes con los filtros seleccionados."
    else:
        t = o.groupby("Tipo de aviso").agg(n=("Aviso", "size"),
                                           venc=("Tiempo aviso", lambda s: int(s.eq("Atrasado").sum())))
        t = t.sort_values("n", ascending=False)
        t["pct"] = t["venc"] / t["n"] * 100
        if len(t) >= 2:
            top2 = t.index[:2].tolist()
            f["type_title"] = (f"{top2[0]} y {top2[1]} concentran el "
                               f"{fmt_pct(pct(int(t['n'].iloc[:2].sum()), n))} del backlog")
        txt = ""
        if venc:
            tv = t["venc"].idxmax()
            txt = (f"«{tv}» acumula más pendientes vencidos ({fmt_int(t.loc[tv, 'venc'])}, "
                   f"{fmt_pct(t.loc[tv, 'pct'])} de sus pendientes).")
            small = t.iloc[2:] if len(t) > 2 else t.iloc[0:0]
            small = small[small["pct"] > 50]
            if not small.empty:
                lista = ", ".join(f"{k} ({fmt_pct(r['pct'])} de {fmt_int(r['n'])})" for k, r in small.iterrows())
                txt += (f" Los tipos con pocos casos tienen mayoría vencida: {lista}. "
                        "Son cierres puntuales que reducen el atraso con poco esfuerzo.")
        else:
            txt = "Ningún pendiente de estos tipos está vencido."
        f["type"] = txt + " Clic en una columna para aislar ese tipo."

    # --- Síntesis ------------------------------------------------------------
    bullets = []
    if n:
        bullets.append(("Magnitud del pasivo: ",
                        f"{fmt_int(n)} avisos siguen abiertos al {FECHA_CORTE}; el {fmt_pct(pct_venc)} "
                        f"({fmt_int(venc)}) ya incumplió su plazo."))
        bullets.append(("Envejecimiento: ",
                        f"la mitad de los pendientes supera {fmt_int(o['Días abierto'].median())} días abierto "
                        f"y el caso más antiguo lleva {fmt_int(o['Días abierto'].max())} días."
                        + (" Cuanto más antiguo el aviso, más probable es que esté vencido."
                           if f.get("aging_grows") else "")))
        urg = o[o["Prioridad"].isin(URGENT_PRIOS)]
        accion = ("Atender primero los pendientes vencidos" if venc
                  else "No hay pendientes vencidos con estos filtros")
        if venc:
            tv = o[late_mask]["Tipo de aviso"].value_counts()
            accion += f", empezando por «{tv.idxmax()}» ({fmt_int(tv.max())} vencidos)"
        urg_venc = int(urg["Tiempo aviso"].eq("Atrasado").sum())
        if urg_venc:
            accion += (f". En prioridades urgentes (Mes y Trimestre) ya están vencidos "
                       f"{fmt_int(urg_venc)} de {fmt_int(len(urg))} pendientes")
        if en_plazo:
            accion += (f". Los {fmt_int(en_plazo)} pendientes dentro del plazo deben programarse antes de su "
                       "vencimiento para no ampliar el atraso")
        accion += "."
        bullets.append(("Prioridad de intervención: ", accion))
    f["bullets"] = bullets
    return f

def page_pendientes(d, years, types, depts, prios, extra):
    o = d[d["Estado aviso"].eq("Abierto")]
    vencidos = int(o["Tiempo aviso"].eq("Atrasado").sum())
    pct_venc = pct(vencidos, len(o)) if len(o) else 0
    f = pending_findings(o)
    return html.Div([
        header("Gestión del pasivo pendiente (Backlog)",
               "Caracterización del inventario abierto, envejecimiento de casos y priorización para intervención.",
               years, types, depts, prios, extra),
        html.Div([
            kpi("PENDIENTES TOTALES", fmt_int(len(o)), f"Avisos abiertos al corte {FECHA_CORTE}", "warning"),
            kpi("PENDIENTES VENCIDOS", fmt_int(vencidos), f"{fmt_pct(pct_venc)} del total abierto", "danger"),
            kpi("DENTRO DEL PLAZO", fmt_int(o["Tiempo aviso"].eq("A tiempo").sum()), "Aún con margen de maniobra", "ok"),
            kpi("ANTIGÜEDAD MEDIANA", fmt_int(o["Días abierto"].median()) + " días", "50% supera esta duración", "info"),
            kpi("CASO MÁS ANTIGUO", fmt_int(o["Días abierto"].max()) + " días", "Máximo tiempo sin resolver", "danger")
        ], className="kpi-row"),
        html.Div([
            card(f"El {fmt_pct(pct_venc)} del inventario abierto ya se encuentra vencido",
                 pending_status(d), f["status"], chart_key="pend-status"),
            card(f["age_title"], pending_age(d), f["age"], chart_key="pend-age")
        ], className="charts-2col"),
        card(f["type_title"], pending_by_type(d), f["type"], chart_key="pending-type"),
        html.Div([
            html.Div("Síntesis del backlog para la toma de decisiones", className="chart-title"),
            *[html.P([html.B(lbl), txt], className="analysis-item") for lbl, txt in f["bullets"]],
        ], className="chart-card analysis-card") if f["bullets"] else None,
    ])

def _swatch_dot(color, shape="dot"):
    style = {"display": "inline-block", "verticalAlign": "middle", "marginRight": "6px", "background": color}
    if shape == "line":
        style.update(width="18px", height="5px", borderRadius="3px")
    else:
        size = "9px" if shape == "tower" else "12px"
        style.update(width=size, height=size, borderRadius="50%")
    return html.Span(style=style)

def map_reading_guide():
    """Guía breve, en lenguaje sencillo, para leer el mapa integrado."""
    warn = f"{META_SLA - BANDA_ALERTA:.0f}"
    meta = f"{META_SLA:.0f}"

    def row(color, text, shape="dot"):
        return html.Li([_swatch_dot(color, shape), text])

    blocks = [
        html.Div([
            html.Div("1 · Líneas: ¿cumplen los plazos?", className="map-guide-title"),
            html.Ul([
                row(GREEN, f"Verde: cierra a tiempo el {meta} % o más (cumple la meta).", "line"),
                row(AMBER, f"Ámbar: entre {warn} % y {meta} % (en riesgo).", "line"),
                row(RED, f"Rojo: menos de {warn} % (crítica).", "line"),
                row(NEUTRAL, f"Gris: menos de {MIN_CERRADOS_LINEA} cierres, no se puede evaluar.", "line"),
                html.Li("Más gruesa = más avisos pendientes por atender."),
            ]),
        ], className="map-guide-block"),
        html.Div([
            html.Div("2 · Torres: ¿dónde está el problema puntual?", className="map-guide-title"),
            html.Ul([
                row(RED, "Roja: tiene avisos vencidos. Es el punto a visitar primero.", "tower"),
                row(AMBER, "Ámbar: tiene pendientes, pero aún dentro del plazo.", "tower"),
                row(GREEN, "Verde: sin pendientes.", "tower"),
                html.Li("Más grande = más avisos registrados en esa torre."),
            ]),
        ], className="map-guide-block"),
        html.Div([
            html.Div("3 · Municipios: ¿cuánta carga sigue abierta?", className="map-guide-title"),
            html.Ul([
                row(RED, "Rojo: 67 % o más de sus avisos sigue abierto."),
                row(AMBER, "Ámbar: entre 34 % y 66 % sigue abierto."),
                row(GREEN, "Verde: 33 % o menos sigue abierto."),
                html.Li("Círculo más grande = más avisos en el municipio."),
            ]),
        ], className="map-guide-block"),
        html.Div([
            html.Div("4 · Cómo usarlo", className="map-guide-title"),
            html.Ul([
                html.Li("En el panel del mapa, «Solo lo crítico» deja únicamente lo que está en rojo."),
                html.Li("Marca o desmarca cada categoría para comparar."),
                html.Li("Pasa el cursor sobre una línea, torre o municipio para ver su ficha con cifras."),
                html.Li("El icono de capas (arriba a la derecha) cambia el fondo: relieve, calles o fondo claro."),
                html.Li("Los filtros laterales y los clics en las gráficas también filtran el mapa."),
            ]),
        ], className="map-guide-block"),
    ]
    return html.Details([
        html.Summary("¿Cómo leer este mapa? (guía rápida)"),
        html.Div(blocks, className="map-guide-grid"),
        html.Div([
            html.B("Ejemplo de lectura: "),
            "una línea roja y gruesa con varias torres rojas es la primera prioridad: incumple la meta, "
            "acumula muchos pendientes y ya tiene avisos vencidos. Un municipio grande y rojo indica una zona "
            "con mucha carga que sigue sin resolverse.",
        ], className="map-guide-example"),
    ], open=True, className="map-guide")

def page_territorio(d, years, types, depts, prios, extra):
    lines = build_line_stats(d)
    evaluated = lines[lines["Cerrados"] >= MIN_CERRADOS_LINEA] if not lines.empty else lines
    n_eval = len(evaluated)
    n_ok = int((evaluated["Cumplimiento"] >= META_SLA).sum()) if n_eval else 0
    if n_eval:
        if n_ok == 0:
            line_summary = (
                f"Ninguna de las {n_eval} líneas evaluables alcanza la meta de {META_SLA:.0f} %. "
                "Se requiere revisar el desempeño de cierre y priorizar las líneas con mayor rezago."
            )
        else:
            line_summary = (
                f"{n_ok} de {n_eval} líneas evaluables cumplen la meta de {META_SLA:.0f} %. "
                "Las demás presentan oportunidades de mejora en el cumplimiento de cierres."
            )
    else:
        line_summary = (
            f"No hay líneas con al menos {MIN_CERRADOS_LINEA} cierres para evaluar el cumplimiento "
            "con los filtros seleccionados."
        )

    venc_lines = evaluated.sort_values("Vencidos", ascending=False) if n_eval else evaluated
    if n_eval and venc_lines["Vencidos"].iat[0] > 0:
        top = venc_lines.iloc[0]
        map_summary = (
            f"La línea con mayor número de pendientes vencidos es {top['Linea']} "
            f"({fmt_int(top['Vencidos'])} casos), con un cumplimiento de {fmt_pct(top['Cumplimiento'])}. "
            "Consulta los detalles de cada línea, torre y municipio directamente en el mapa."
        )
    else:
        map_summary = (
            "El mapa permite consultar la distribución de líneas, torres y avisos municipales, "
            "así como los indicadores de gestión de cada municipio."
        )

    return html.Div([
        header("Desempeño territorial y de la red",
               "Visualización integrada de líneas, torres y municipios para identificar zonas críticas y orientar la asignación de cuadrillas.",
               years, types, depts, prios, extra),
        html.Div(territory_kpis(d), className="kpi-row kpi-row-six"),
        html.Div([
            html.Div("Mapa integrado de líneas de transmisión, torres y gestión municipal", className="chart-title"),
            map_reading_guide(),
            integrated_map(d),
            html.Div(map_summary, className="chart-subtitle", style={"marginTop": "10px"}),
            html.Div(
                "El trazado de las líneas es aproximado: conecta las torres según su numeración y no representa "
                "necesariamente el trazado oficial de la infraestructura.",
                className="map-note"
            )
        ], className="chart-card integrated-map-card"),
        html.Div([
            card("Cumplimiento de cierres por línea de transmisión", line_performance(d),
                 line_summary + f" La referencia vertical indica la meta del {META_SLA:.0f} %.",
                 chart_key="line-perf"),
            card("Acumulación de pendientes y cierres tardíos por departamento",
                 department_performance(d),
                 "Se muestran los departamentos con mayor volumen conjunto de pendientes y cierres tardíos. "
                 "Haz clic sobre una barra para filtrar el tablero y el mapa integrado.",
                 chart_key="dept-perf")
        ], className="charts-2col")
    ])

def page_placeholder():
    return build_home()

# ============================================================
# BARRA LATERAL Y LAYOUT PRINCIPAL
# ============================================================
years_opts = [{"label": _year_label(y) + (" (parcial)" if y == PARTIAL_YEAR else ""), "value": int(y)} for y in YEARS]
prio_opts = [{"label": p, "value": p} for p in PRIORITY_ORDER if p in df["Prioridad"].unique()]

sidebar = html.Aside([
    html.Div([
        html.Img(src="/assets/logo_energy.png", className="sidebar-logo"),
        html.Div("GESTIÓN DE AVISOS", className="sidebar-brand-caption"),
        html.Div("GRID INTELLIGENCE · EQ 2", className="brand-tag")
    ], className="sidebar-brand"),
    html.Div("NAVEGACIÓN", className="section-label"),
    dcc.Link([html.Span(className="nav-dot"), "Inicio"], href="/inicio", className="nav-link", id="nav-inicio"),
    dcc.Link([html.Span(className="nav-dot"), "Resumen gerencial"], href="/resumen", className="nav-link", id="nav-resumen"),
    dcc.Link([html.Span(className="nav-dot"), "Cumplimiento y plazos"], href="/cumplimiento", className="nav-link", id="nav-cumplimiento"),
    dcc.Link([html.Span(className="nav-dot"), "Pendientes por cumplir"], href="/pendientes", className="nav-link", id="nav-pendientes"),
    dcc.Link([html.Span(className="nav-dot"), "Territorio y red"], href="/territorio", className="nav-link", id="nav-territorio"),
    html.Div("FILTROS DE GESTIÓN", className="section-label"),
    html.Div([
        html.Button("RESTABLECER FILTROS", id="reset-filters", n_clicks=0, className="reset-filters-btn"),
        html.Div("BASE ACTIVA · MARCA = NORMAL", className="normal-badge"),
        html.Div("Filtra desde aquí o haciendo clic directamente sobre cualquier gráfica.", className="filter-hint"),
        html.Label("AÑO DE AVISO", className="filter-label"),
        dcc.Dropdown(id="f-year", options=years_opts, value=[], multi=True, clearable=True, searchable=True, placeholder="Todos los años"),
        html.Label("TIPO DE AVISO", className="filter-label"),
        dcc.Dropdown(id="f-type", options=options("Tipo de aviso"), value=[], multi=True, clearable=True, searchable=True, placeholder="Todos los tipos"),
        html.Label("DEPARTAMENTO", className="filter-label"),
        dcc.Dropdown(id="f-dept", options=options("Departamento"), value=[], multi=True, clearable=True, searchable=True, placeholder="Todos los departamentos"),
        html.Label("PRIORIDAD", className="filter-label"),
        dcc.Dropdown(id="f-prio", options=prio_opts, value=[], multi=True, clearable=True, searchable=True, placeholder="Todas las prioridades")
    ], className="sidebar-filters"),
    # Cierra el menú para ver el tablero filtrado.
    html.Button("VER TABLERO", id="menu-close-btn", n_clicks=0, className="menu-close-btn"),
    html.Div([
        html.Div("AUTORES · EQUIPO 2", className="authors-title"),
        html.Div([html.Div("MG", className="author-avatar"), html.Div("Mauricio Guerrero", className="author-name")], className="author-row"),
        html.Div([html.Div("DR", className="author-avatar"), html.Div("Daniel Rodriguez", className="author-name")], className="author-row"),
        html.Div([html.Div("JB", className="author-avatar"), html.Div("Juan Bojacá", className="author-name")], className="author-row"),
        html.Div([html.Div("AN", className="author-avatar"), html.Div("Andres Nova", className="author-name")], className="author-row")
    ], className="authors-panel")
], id="sidebar", className="sidebar")

PAGES = [
    ("/inicio", "Inicio"),
    ("/resumen", "Resumen gerencial"),
    ("/cumplimiento", "Cumplimiento y plazos"),
    ("/pendientes", "Pendientes por cumplir"),
    ("/territorio", "Territorio y red"),
]

# ------------------------------------------------------------
# Menú desplegable (escritorio y celular)
# Se usa el elemento nativo <details>: el navegador lo abre y lo cierra al
# tocar el botón de tres líneas (<summary>), sin pasar por el servidor.
# La barra lateral completa (navegación, filtros y autores) va dentro.
# ------------------------------------------------------------
nav_menu = html.Details([
    html.Summary([html.Span(), html.Span(), html.Span()], className="menu-btn",
                 title="Abrir o cerrar el menú", **{"aria-label": "Abrir o cerrar el menú"}),
    sidebar,
], id="nav-menu", className="nav-menu")

topbar = html.Div([
    nav_menu,
    html.Img(src="/assets/logo.svg", alt="ENERGY", className="topbar-logo"),
    html.Div([
        html.Div(f"GESTIÓN DE AVISOS · ENERGY · v{APP_VERSION}", className="topbar-brand"),
        html.Div("Inicio", id="topbar-page-name", className="topbar-page"),
    ], className="topbar-text"),
], className="topbar")

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="extra-filters", data={}),
    dcc.Store(id="menu-closer"),
    topbar,
    html.Main([
        html.Div(id="page-content")
    ], className="main-content")
], className="app-wrapper")

# ============================================================
# CALLBACKS
# ============================================================

@app.callback(
    Output("f-year", "value"),
    Output("f-type", "value"),
    Output("f-dept", "value"),
    Output("f-prio", "value"),
    Output("extra-filters", "data"),
    Input("reset-filters", "n_clicks"),
    prevent_initial_call=True
)
def reset_filters(_):
    return [], [], [], [], {}

def _toggle(values, val):
    return [v for v in values if v != val] if val in values else values + [val]

@app.callback(
    Output("f-year", "value", allow_duplicate=True),
    Output("f-type", "value", allow_duplicate=True),
    Output("f-dept", "value", allow_duplicate=True),
    Output("f-prio", "value", allow_duplicate=True),
    Output("extra-filters", "data", allow_duplicate=True),
    Input({"type": "interactive-chart", "id": ALL}, "clickData"),
    State("f-year", "value"),
    State("f-type", "value"),
    State("f-dept", "value"),
    State("f-prio", "value"),
    State("extra-filters", "data"),
    prevent_initial_call=True
)
def handle_all_chart_clicks(click_list, years, types, depts, prios, extra):
    # Ignorar disparos vacíos cuando se renderiza una nueva pestaña
    if not ctx.triggered or not ctx.triggered[0].get("value"):
        return (dash.no_update,) * 5

    trig_id = ctx.triggered_id
    if not isinstance(trig_id, dict):
        return (dash.no_update,) * 5

    chart_key = trig_id.get("id")
    point = ctx.triggered[0]["value"]["points"][0]

    years = list(years or [])
    types = list(types or [])
    depts = list(depts or [])
    prios = list(prios or [])
    extra = dict(extra or {})

    if chart_key == "status-donut":
        val = point.get("label")
        extra["estado"] = None if extra.get("estado") == val else val

    elif chart_key == "comp-donut":
        val = point.get("label")
        extra["tiempo"] = None if extra.get("tiempo") == val else val

    elif chart_key in ("trend-inc", "month-comp"):
        years = _toggle(years, int(pd.to_datetime(point.get("x")).year))

    elif chart_key == "annual-backlog":
        years = _toggle(years, int(str(point.get("x")).rstrip("*")))

    elif chart_key == "comp-prio":
        prios = _toggle(prios, point.get("x"))

    elif chart_key == "box-prio":
        prios = _toggle(prios, point.get("y"))

    elif chart_key == "late-type":
        types = _toggle(types, point.get("y"))

    elif chart_key == "pending-type":
        types = _toggle(types, point.get("x"))

    elif chart_key == "pend-status":
        val = point.get("label")
        extra["pend_sit"] = None if extra.get("pend_sit") == val else val

    elif chart_key == "pend-age":
        val = point.get("x")
        extra["antiguedad"] = None if extra.get("antiguedad") == val else val

    elif chart_key == "dept-perf":
        depts = _toggle(depts, point.get("y"))

    elif chart_key == "line-perf":
        val = point.get("y")
        extra["linea"] = None if extra.get("linea") == val else val

    return years, types, depts, prios, extra

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("f-year", "value"),
    Input("f-type", "value"),
    Input("f-dept", "value"),
    Input("f-prio", "value"),
    Input("extra-filters", "data")
)
def render_page(pathname, years, types, depts, prios, extra):
    d = filter_data(years, types, depts, prios, extra)
    path = pathname or "/inicio"
    if path == "/cumplimiento": return page_cumplimiento(d, years, types, depts, prios, extra)
    if path == "/pendientes":   return page_pendientes(d, years, types, depts, prios, extra)
    if path == "/territorio":   return page_territorio(d, years, types, depts, prios, extra)
    if path == "/resumen":      return page_resumen(d, years, types, depts, prios, extra)
    return page_placeholder()

@app.callback(
    Output("nav-inicio", "className"), Output("nav-resumen", "className"),
    Output("nav-cumplimiento", "className"), Output("nav-pendientes", "className"),
    Output("nav-territorio", "className"),
    Output("topbar-page-name", "children"),
    Input("url", "pathname")
)
def active_nav(path):
    p = path if path in dict(PAGES) else "/inicio"
    classes = tuple("nav-link active" if p == x else "nav-link" for x, _ in PAGES)
    return (*classes, dict(PAGES)[p])

# Cierra el menú al cambiar de página o al pulsar «Ver tablero».
# Se ejecuta en el navegador (clientside): no espera respuesta del servidor.
app.clientside_callback(
    """
    function(path, n) {
        var menu = document.getElementById('nav-menu');
        if (menu) { menu.open = false; }
        return window.dash_clientside.no_update;
    }
    """,
    Output("menu-closer", "data"),
    Input("url", "pathname"),
    Input("menu-close-btn", "n_clicks"),
)

if __name__ == "__main__":
    # Ejecución local: python app.py → http://127.0.0.1:8050/
    # En Render el tablero se sirve con gunicorn (ver render.yaml / Procfile),
    # que usa directamente el objeto `server` y no pasa por este bloque.
    app.run(debug=os.environ.get("DASH_DEBUG", "1") == "1",
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", 8050)))
