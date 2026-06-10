"""
All Plotly chart builders — one function per chart, returns go.Figure.
Rendering happens in tab / page files, never here.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from config import COLORS, CHART_PALETTE

# ── Base theme — shared across all charts ────────────────────────────────────
_LAYOUT = dict(
    plot_bgcolor=COLORS["bg"],
    paper_bgcolor=COLORS["bg"],
    margin=dict(t=44, b=22, l=14, r=18),
    font=dict(family="-apple-system, BlinkMacSystemFont, Inter, Segoe UI, sans-serif",
              size=12, color=COLORS["text"]),
    hoverlabel=dict(
        bgcolor="white",
        bordercolor=COLORS["primary"],
        font=dict(size=12, color=COLORS["text"],
                  family="-apple-system, Inter, sans-serif"),
    ),
    colorway=CHART_PALETTE,
)

_AXIS = dict(
    gridcolor="rgba(226, 232, 240, 0.65)",
    linecolor="rgba(226, 232, 240, 0)",
    zerolinecolor="rgba(148, 163, 184, 0.35)",
    tickfont=dict(color=COLORS["muted"], size=11),
    title_font=dict(color=COLORS["muted"], size=11),
    showspikes=False,
)


def _style(fig: go.Figure) -> go.Figure:
    """Apply axis polish, title formatting, and default legend style."""
    fig.update_xaxes(**_AXIS)
    fig.update_yaxes(**_AXIS)
    fig.update_layout(
        title_font=dict(size=13, color=COLORS["text"]),
        title_x=0.02,
        title_xanchor="left",
        legend_bgcolor="rgba(255,255,255,0)",
        legend_borderwidth=0,
        legend_font=dict(size=11, color=COLORS["muted"]),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  Portfolio charts
# ─────────────────────────────────────────────────────────────────────────────

def chart_sector_comparison(comp_df: pd.DataFrame) -> go.Figure:
    long = comp_df.melt(
        id_vars="Secteur", value_vars=["Portefeuille", "S&P 500"],
        var_name="Source", value_name="Poids",
    )
    fig = px.bar(
        long, x="Secteur", y="Poids", color="Source", barmode="group",
        color_discrete_map={
            "Portefeuille": COLORS["primary"],
            "S&P 500":      COLORS["muted"],
        },
    )
    fig.update_traces(marker_line_width=0,
                      hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.1%}<extra></extra>")
    fig.update_layout(
        **_LAYOUT,
        yaxis_tickformat=".0%",
        xaxis_tickangle=-30,
        legend_title_text="",
        bargap=0.28,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return _style(fig)


def chart_ticker_donut(df_port: pd.DataFrame) -> go.Figure:
    fig = px.pie(
        df_port, values="W", names="Symbol", hole=0.62,
        color_discrete_sequence=CHART_PALETTE,
    )
    fig.update_traces(
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11, color=COLORS["text"]),
        marker=dict(line=dict(color="#ffffff", width=2)),
        hovertemplate="<b>%{label}</b><br>Poids: %{percent}<extra></extra>",
    )
    fig.update_layout(**_LAYOUT, showlegend=False)
    return _style(fig)


def chart_drawdowns(drawdowns: pd.Series) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdowns.index,
        y=drawdowns.values * 100,
        mode="lines",
        line=dict(color=COLORS["danger"], width=1.6),
        fill="tozeroy",
        fillcolor="rgba(244, 63, 94, 0.16)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Drawdown: %{y:.1f}%<extra></extra>",
        name="Drawdown",
    ))
    fig.update_layout(**_LAYOUT, yaxis_ticksuffix="%", showlegend=False,
                      yaxis_title="Drawdown", xaxis_title=None)
    return _style(fig)


def chart_performance(cum_port: pd.Series, cum_bench: pd.Series, benchmark: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cum_port.index, y=cum_port.values,
        mode="lines", name="Portefeuille",
        line=dict(color=COLORS["primary"], width=2.4),
        fill="tozeroy", fillcolor="rgba(37, 99, 235, 0.08)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Portefeuille: %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=cum_bench.index, y=cum_bench.values,
        mode="lines", name=benchmark,
        line=dict(color=COLORS["muted"], width=1.8, dash="dot"),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>" + benchmark + ": %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT, hovermode="x unified",
        yaxis_title="Valeur (base 1)", xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return _style(fig)


def chart_monte_carlo(mc_df: pd.DataFrame, total_val: float) -> go.Figure:
    bands = [
        ("P95",     COLORS["light"],     None,        "rgba(16, 185, 129, 0.08)"),
        ("P75",     COLORS["success"],   "P95",       "rgba(16, 185, 129, 0.16)"),
        ("Médiane", COLORS["primary"],   "P75",       "rgba(37, 99, 235, 0.18)"),
        ("P25",     COLORS["warning"],   "Médiane",   "rgba(245, 158, 11, 0.16)"),
        ("P5",      COLORS["danger"],    "P25",       "rgba(244, 63, 94, 0.10)"),
    ]
    fig = go.Figure()
    for name, color, fill_target, fill_color in bands:
        fig.add_trace(go.Scatter(
            x=mc_df.index, y=mc_df[name], name=name,
            line=dict(width=1.6, color=color),
            fill="tonexty" if fill_target else None,
            fillcolor=fill_color if fill_target else None,
            hovertemplate=f"<b>{name}</b><br>Jour %{{x}}<br>$%{{y:,.0f}}<extra></extra>",
        ))
    fig.add_hline(
        y=total_val, line_dash="dash", line_color=COLORS["muted"],
        line_width=1.2,
        annotation_text="<b>Valeur actuelle</b>",
        annotation_position="bottom right",
        annotation_font=dict(color=COLORS["muted"], size=10),
    )
    fig.update_layout(
        **_LAYOUT, yaxis_title="Valeur projetée", xaxis_title="Jours de trading",
        yaxis_tickprefix="$", yaxis_tickformat=",.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    title_text="Percentile"),
    )
    return _style(fig)


def chart_contributors(contrib_df: pd.DataFrame) -> go.Figure:
    colors = [COLORS["success"] if v >= 0 else COLORS["danger"]
              for v in contrib_df["Contribution"]]
    fig = go.Figure(go.Bar(
        x=contrib_df["Symbol"],
        y=contrib_df["Contribution"] * 100,
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:+.2f}%" for v in contrib_df["Contribution"] * 100],
        textposition="outside",
        textfont=dict(color=COLORS["text"], size=11),
        hovertemplate="<b>%{x}</b><br>Contribution: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT, yaxis_ticksuffix="%",
                      yaxis_title="Contribution", xaxis_title=None, showlegend=False,
                      bargap=0.4)
    return _style(fig)


def chart_correlation_matrix(rets: pd.DataFrame) -> go.Figure:
    corr = rets.corr().round(2)
    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        zmin=-1, zmax=1,
        colorscale=[
            [0.0, "#f43f5e"],
            [0.25, "#fda4af"],
            [0.5, "#ffffff"],
            [0.75, "#93c5fd"],
            [1.0, "#2563eb"],
        ],
        text=corr.values.round(2),
        texttemplate="%{text}",
        textfont=dict(size=11, color=COLORS["text"]),
        hoverongaps=False,
        hovertemplate="<b>%{x} × %{y}</b><br>ρ = %{z:.2f}<extra></extra>",
        colorbar=dict(thickness=10, title=dict(text="ρ", font=dict(size=11)),
                      tickfont=dict(color=COLORS["muted"], size=10)),
    ))
    fig.update_layout(**_LAYOUT, xaxis_tickangle=-30, yaxis_autorange="reversed")
    return _style(fig)


def chart_efficient_frontier(
    cloud_df: pd.DataFrame,
    frontier_df: pd.DataFrame | None,
    current: dict,
    max_sharpe: dict,
    min_vol: dict,
) -> go.Figure:
    """Cloud + frontier line + 3 anchored markers."""
    fig = go.Figure()

    # Random cloud (low-opacity scatter)
    fig.add_trace(go.Scatter(
        x=cloud_df["Volatility"] * 100,
        y=cloud_df["Return"] * 100,
        mode="markers",
        marker=dict(
            size=5, color=cloud_df["Sharpe"], colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Sharpe", thickness=10,
                          tickfont=dict(color=COLORS["muted"], size=10),
                          title_font=dict(color=COLORS["muted"], size=11)),
            opacity=0.45,
            line=dict(width=0),
        ),
        name="Portefeuilles simulés",
        hovertemplate="Vol: %{x:.1f}%<br>Ret: %{y:.1f}%<extra></extra>",
    ))

    # True efficient frontier line
    if frontier_df is not None and not frontier_df.empty:
        fig.add_trace(go.Scatter(
            x=frontier_df["Volatility"] * 100,
            y=frontier_df["Return"] * 100,
            mode="lines",
            line=dict(color=COLORS["text"], width=2.5),
            name="Frontière efficiente",
        ))

    def _add_marker(ret, vol, name, color, symbol="star"):
        if ret is None or vol is None:
            return
        fig.add_trace(go.Scatter(
            x=[vol * 100], y=[ret * 100],
            mode="markers+text",
            marker=dict(size=18, color=color, symbol=symbol,
                        line=dict(width=2.5, color="white")),
            text=[f"<b>{name}</b>"], textposition="top center",
            textfont=dict(color=COLORS["text"], size=11),
            name=name,
            hovertemplate=f"<b>{name}</b><br>Vol: %{{x:.1f}}%<br>Ret: %{{y:.1f}}%<extra></extra>",
        ))

    _add_marker(current.get("return"), current.get("volatility"),
                "Actuel", COLORS["warning"], "circle")
    if max_sharpe:
        _add_marker(max_sharpe.get("return"), max_sharpe.get("volatility"),
                    "Max Sharpe", COLORS["success"], "star")
    if min_vol:
        _add_marker(min_vol.get("return"), min_vol.get("volatility"),
                    "Min Vol", COLORS["primary"], "diamond")

    fig.update_layout(
        **_LAYOUT,
        xaxis_title="Volatilité annualisée (%)",
        yaxis_title="Rendement annualisé (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        hovermode="closest",
    )
    return _style(fig)


# ── Rolling metrics ──────────────────────────────────────────────────────────

def chart_rolling_sharpe(rs: pd.Series) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rs.index, y=rs.values, mode="lines",
        line=dict(color=COLORS["primary"], width=2.2),
        name="Sharpe roulant",
        fill="tozeroy", fillcolor="rgba(37, 99, 235, 0.10)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Sharpe: %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color=COLORS["success"],
                  line_width=1.2,
                  annotation_text="Bon ≥ 1.0",
                  annotation_position="top right",
                  annotation_font=dict(color=COLORS["success"], size=10))
    fig.add_hline(y=0.0, line_dash="dot", line_color=COLORS["muted"], line_width=1)
    fig.update_layout(**_LAYOUT, yaxis_title="Sharpe (90j)",
                      xaxis_title=None, showlegend=False)
    return _style(fig)


def chart_rolling_drawdown(rd: pd.Series) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rd.index, y=rd.values * 100, mode="lines",
        line=dict(color=COLORS["danger"], width=1.8),
        fill="tozeroy", fillcolor="rgba(244, 63, 94, 0.16)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>DD: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT, yaxis_title="Drawdown roulant",
                      xaxis_title=None, showlegend=False, yaxis_ticksuffix="%")
    return _style(fig)


# ── Backtest ─────────────────────────────────────────────────────────────────

def chart_backtest_comparison(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    palette = {
        "Actuel": COLORS["primary"],
        "Cible":  COLORS["success"],
    }
    dashes = {"Actuel": "solid", "Cible": "solid"}
    for col in df.columns:
        color = palette.get(col, COLORS["muted"])
        dash  = dashes.get(col, "dot")
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], mode="lines",
            line=dict(color=color, width=2.2, dash=dash),
            name=col,
            hovertemplate=f"<b>{col}</b><br>%{{x|%d %b %Y}}<br>%{{y:.2f}}<extra></extra>",
        ))
    fig.update_layout(
        **_LAYOUT, yaxis_title="Valeur (base 1)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return _style(fig)


# ── Health Score breakdown ───────────────────────────────────────────────────

def chart_health_breakdown(breakdown: dict) -> go.Figure:
    labels = list(breakdown.keys())
    vals   = list(breakdown.values())
    bar_colors = [COLORS["primary"], COLORS["success"],
                  COLORS["accent"], COLORS["warning"]]
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker=dict(color=bar_colors[:len(labels)], line=dict(width=0)),
        text=[f"<b>{v}</b>" for v in vals], textposition="outside",
        textfont=dict(color=COLORS["text"], size=12),
        hovertemplate="<b>%{x}</b><br>%{y}/100<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT, yaxis_title="Score / 100",
                      yaxis_range=[0, 110], showlegend=False,
                      xaxis_title=None, bargap=0.45)
    return _style(fig)


# ── Stress tests ─────────────────────────────────────────────────────────────

def chart_stress_results(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    bar_colors = [COLORS["danger"] if v < 0 else COLORS["success"]
                  for v in df["Rendement"]]
    fig.add_trace(go.Bar(
        x=df["Scénario"], y=df["Rendement"] * 100,
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"<b>{v:+.1%}</b>" for v in df["Rendement"]],
        textposition="outside",
        textfont=dict(color=COLORS["text"], size=12),
        hovertemplate="<b>%{x}</b><br>Rendement: %{y:.1f}%<extra></extra>",
        name="Rendement",
    ))
    fig.update_layout(**_LAYOUT, yaxis_ticksuffix="%",
                      yaxis_title="Rendement portefeuille",
                      showlegend=False, bargap=0.4)
    return _style(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  Single-stock charts
# ─────────────────────────────────────────────────────────────────────────────

def chart_price_history(hist: pd.DataFrame, ticker: str) -> go.Figure:
    if hist.empty:
        return go.Figure()
    perf  = (hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1
    color = COLORS["success"] if perf >= 0 else COLORS["danger"]
    fill  = "rgba(16, 185, 129, 0.10)" if perf >= 0 else "rgba(244, 63, 94, 0.10)"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        mode="lines",
        line=dict(color=color, width=2.2),
        fill="tozeroy", fillcolor=fill,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>$%{y:,.2f}<extra></extra>",
        name=ticker,
    ))
    fig.update_layout(
        **_LAYOUT,
        title=f"<b>{ticker}</b>  ·  {perf:+.1%}",
        xaxis_title=None, yaxis_title="Prix ($)",
        showlegend=False,
    )
    return _style(fig)


def chart_revenue_net_income(fin: pd.DataFrame) -> tuple[go.Figure, go.Figure]:
    empty = go.Figure()
    if fin.empty:
        return empty, empty
    df = fin.T.sort_index()

    fig_rev = go.Figure()
    if "Total Revenue" in df.columns:
        fig_rev.add_trace(go.Bar(
            x=df.index.astype(str), y=df["Total Revenue"] / 1e9,
            marker=dict(color=COLORS["primary"], line=dict(width=0)),
            text=(df["Total Revenue"] / 1e9).round(1).astype(str) + "B",
            textposition="outside",
            textfont=dict(color=COLORS["text"], size=11),
            hovertemplate="%{x}<br>Revenue: $%{y:.1f}B<extra></extra>",
        ))
    fig_rev.update_layout(**_LAYOUT, yaxis_title="Revenue ($B)", xaxis_title=None,
                          showlegend=False, bargap=0.4)

    fig_ni = go.Figure()
    if "Net Income" in df.columns:
        bar_colors = [COLORS["success"] if v >= 0 else COLORS["danger"]
                      for v in df["Net Income"]]
        fig_ni.add_trace(go.Bar(
            x=df.index.astype(str), y=df["Net Income"] / 1e9,
            marker=dict(color=bar_colors, line=dict(width=0)),
            text=(df["Net Income"] / 1e9).round(1).astype(str) + "B",
            textposition="outside",
            textfont=dict(color=COLORS["text"], size=11),
            hovertemplate="%{x}<br>Net Income: $%{y:.1f}B<extra></extra>",
        ))
    fig_ni.update_layout(**_LAYOUT, yaxis_title="Net Income ($B)", xaxis_title=None,
                         showlegend=False, bargap=0.4)
    return _style(fig_rev), _style(fig_ni)


def chart_eps(earnings: pd.DataFrame) -> go.Figure:
    if earnings.empty:
        return go.Figure()
    try:
        eps = earnings.dropna(subset=["Reported EPS"]).sort_index().tail(10)
        if eps.empty:
            return go.Figure()
        bar_colors = [COLORS["success"] if v >= 0 else COLORS["danger"]
                      for v in eps["Reported EPS"]]
        fig = go.Figure(go.Bar(
            x=eps.index.astype(str), y=eps["Reported EPS"],
            marker=dict(color=bar_colors, line=dict(width=0)),
            text=eps["Reported EPS"].round(2), textposition="outside",
            textfont=dict(color=COLORS["text"], size=11),
            hovertemplate="%{x}<br>EPS: $%{y:.2f}<extra></extra>",
        ))
        fig.update_layout(**_LAYOUT, yaxis_title="EPS ($)", xaxis_title=None,
                          xaxis_tickangle=-30, showlegend=False, bargap=0.4)
        return _style(fig)
    except Exception:
        return go.Figure()


# ── Multi-ticker compare ─────────────────────────────────────────────────────

def chart_compare_metric(rows: list[dict], metric: str, format_pct: bool = False) -> go.Figure:
    df = pd.DataFrame(rows).dropna(subset=[metric])
    if df.empty:
        return go.Figure()
    colors = [COLORS["primary"] if v >= 0 else COLORS["danger"] for v in df[metric]]
    fmt = "{:+.1%}" if format_pct else "{:.2f}"
    text = [fmt.format(v) for v in df[metric]]
    fig = go.Figure(go.Bar(
        x=df["Symbol"], y=df[metric] * (100 if format_pct else 1),
        marker=dict(color=colors, line=dict(width=0)),
        text=text, textposition="outside",
        textfont=dict(color=COLORS["text"], size=11),
        hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT, yaxis_title=metric, xaxis_title=None,
                      showlegend=False, bargap=0.4,
                      yaxis_ticksuffix="%" if format_pct else "")
    return _style(fig)


# ── Macro charts (FRED) ───────────────────────────────────────────────────────

def chart_macro_series(series: dict[str, "pd.Series"]) -> "go.Figure":
    """Multi-panel line chart for macro series (each on its own y-axis subplot)."""
    from plotly.subplots import make_subplots
    names = [n for n, s in series.items() if not s.empty]
    if not names:
        return go.Figure()
    fig = make_subplots(rows=len(names), cols=1, shared_xaxes=True,
                        subplot_titles=names, vertical_spacing=0.06)
    palette = list(CHART_PALETTE)
    for i, name in enumerate(names):
        s = series[name].dropna()
        fig.add_trace(
            go.Scatter(x=s.index, y=s.values, mode="lines", name=name,
                       line=dict(color=palette[i % len(palette)], width=1.8),
                       hovertemplate=f"<b>{name}</b><br>%{{x|%b %Y}}: %{{y:.2f}}<extra></extra>"),
            row=i + 1, col=1,
        )
    fig.update_layout(**_LAYOUT, showlegend=False,
                      height=220 * len(names), margin=dict(t=30, b=22, l=14, r=18))
    fig.update_xaxes(**_AXIS)
    fig.update_yaxes(**_AXIS)
    return fig


# ── Technical indicator charts (Alpha Vantage) ───────────────────────────────

def chart_rsi(rsi: "pd.Series", ticker: str) -> "go.Figure":
    s = rsi.dropna().tail(252)
    fig = go.Figure()
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(244,63,94,0.08)", line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(16,185,129,0.08)", line_width=0)
    fig.add_hline(y=70, line=dict(color=COLORS["danger"],  width=1, dash="dot"))
    fig.add_hline(y=30, line=dict(color=COLORS["success"], width=1, dash="dot"))
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, mode="lines", name="RSI",
        line=dict(color=COLORS["primary"], width=2),
        hovertemplate="<b>RSI</b><br>%{x|%d %b %Y}: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT, title=f"RSI(14) — {ticker}",
                      yaxis=dict(range=[0, 100], **_AXIS))
    return _style(fig)


def chart_macd(macd_df: "pd.DataFrame", ticker: str) -> "go.Figure":
    df = macd_df.dropna().tail(252)
    if df.empty:
        return go.Figure()
    hist_colors = [COLORS["success"] if v >= 0 else COLORS["danger"]
                   for v in df.get("MACD_Hist", df.iloc[:, 2])]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index, y=df.get("MACD_Hist", df.iloc[:, 2]),
        name="Histogramme", marker_color=hist_colors,
        hovertemplate="%{x|%d %b}: %{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df.get("MACD", df.iloc[:, 0]),
                             name="MACD", line=dict(color=COLORS["primary"], width=1.5)))
    fig.add_trace(go.Scatter(x=df.index, y=df.get("MACD_Signal", df.iloc[:, 1]),
                             name="Signal", line=dict(color=COLORS["warning"], width=1.5,
                                                      dash="dot")))
    fig.update_layout(**_LAYOUT, title=f"MACD — {ticker}", barmode="relative")
    return _style(fig)


def chart_bbands(price: "pd.Series", bbands: "pd.DataFrame", ticker: str) -> "go.Figure":
    df = bbands.dropna().tail(252)
    px_s = price.reindex(df.index).dropna()
    fig = go.Figure()
    upper_col = [c for c in df.columns if "Upper" in c or "upper" in c]
    lower_col = [c for c in df.columns if "Lower" in c or "lower" in c]
    mid_col   = [c for c in df.columns if "Middle" in c or "middle" in c or "Mid" in c]
    if upper_col and lower_col:
        fig.add_trace(go.Scatter(
            x=df.index.tolist() + df.index[::-1].tolist(),
            y=df[upper_col[0]].tolist() + df[lower_col[0]][::-1].tolist(),
            fill="toself", fillcolor="rgba(37,99,235,0.07)",
            line=dict(width=0), name="Bandes BB", showlegend=True,
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df[upper_col[0]],
                                 line=dict(color=COLORS["secondary"], width=1, dash="dot"),
                                 name="Upper", showlegend=False))
        fig.add_trace(go.Scatter(x=df.index, y=df[lower_col[0]],
                                 line=dict(color=COLORS["secondary"], width=1, dash="dot"),
                                 name="Lower", showlegend=False))
    if mid_col:
        fig.add_trace(go.Scatter(x=df.index, y=df[mid_col[0]],
                                 line=dict(color=COLORS["muted"], width=1),
                                 name="MA20"))
    fig.add_trace(go.Scatter(x=px_s.index, y=px_s.values,
                             line=dict(color=COLORS["primary"], width=2),
                             name=ticker))
    fig.update_layout(**_LAYOUT, title=f"Bollinger Bands(20) — {ticker}")
    return _style(fig)
