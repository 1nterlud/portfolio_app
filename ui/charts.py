"""
All Plotly chart builders — one function per chart, returns go.Figure.
Rendering is done in the tab / page files, never here.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from config import COLORS

# Base layout applied to every chart via **_LAYOUT
_LAYOUT = dict(
    plot_bgcolor=COLORS["bg"],
    paper_bgcolor=COLORS["bg"],
    margin=dict(t=28, b=8, l=8, r=8),
    font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
)

# Axis style applied via update_xaxes / update_yaxes (never as layout kwarg)
_AXIS = dict(
    gridcolor=COLORS["grid"],
    linecolor=COLORS["grid"],
    tickfont=dict(color=COLORS["text"]),
    title_font=dict(color=COLORS["text"]),
)


def _style(fig: go.Figure) -> go.Figure:
    """Apply consistent axis colors — uses update_xaxes/update_yaxes to avoid
    keyword conflicts with chart-specific update_layout calls."""
    fig.update_xaxes(**_AXIS)
    fig.update_yaxes(**_AXIS)
    return fig


# ── Portfolio charts ──────────────────────────────────────────────────────────

def chart_sector_comparison(comp_df: pd.DataFrame) -> go.Figure:
    long = comp_df.melt(
        id_vars="Secteur", value_vars=["Portefeuille", "S&P 500"],
        var_name="Source", value_name="Poids",
    )
    fig = px.bar(
        long, x="Secteur", y="Poids", color="Source", barmode="group",
        color_discrete_map={"Portefeuille": COLORS["primary"], "S&P 500": COLORS["secondary"]},
    )
    fig.update_layout(**_LAYOUT, yaxis_tickformat=".0%", xaxis_tickangle=-35,
                      legend_title_text="", bargap=0.2)
    return _style(fig)


def chart_ticker_donut(df_port: pd.DataFrame) -> go.Figure:
    fig = px.pie(df_port, values="W", names="Symbol", hole=0.50,
                 color_discrete_sequence=px.colors.qualitative.Plotly)
    fig.update_traces(textinfo="label+percent", textposition="outside")
    fig.update_layout(**_LAYOUT, showlegend=True)
    return _style(fig)


def chart_drawdowns(drawdowns: pd.Series) -> go.Figure:
    fig = px.area((drawdowns * 100).rename("Drawdown (%)"),
                  color_discrete_sequence=[COLORS["danger"]],
                  labels={"value": "Baisse (%)", "index": "Date"})
    fig.update_layout(**_LAYOUT, showlegend=False, yaxis_ticksuffix="%")
    return _style(fig)


def chart_performance(cum_port: pd.Series, cum_bench: pd.Series, benchmark: str) -> go.Figure:
    df = pd.DataFrame({"Portefeuille": cum_port, benchmark: cum_bench})
    fig = px.line(df, labels={"value": "Valeur (base 1)", "index": "Date", "variable": ""},
                  color_discrete_map={"Portefeuille": COLORS["primary"], benchmark: COLORS["secondary"]})
    fig.update_layout(**_LAYOUT, legend_title_text="", hovermode="x unified")
    return _style(fig)


def chart_monte_carlo(mc_df: pd.DataFrame, total_val: float) -> go.Figure:
    bands = [
        ("P95",     COLORS["light"],     None,        "rgba(0,200,0,0.08)"),
        ("P75",     COLORS["success"],   "P95",       "rgba(0,200,0,0.12)"),
        ("Médiane", COLORS["primary"],   "P75",       "rgba(0,104,201,0.15)"),
        ("P25",     COLORS["warning"],   "Médiane",   "rgba(230,126,0,0.12)"),
        ("P5",      COLORS["danger"],    "P25",       "rgba(220,53,69,0.08)"),
    ]
    fig = go.Figure()
    for name, color, fill_target, fill_color in bands:
        fig.add_trace(go.Scatter(
            x=mc_df.index, y=mc_df[name], name=name,
            line=dict(width=1.5, color=color),
            fill="tonexty" if fill_target else None,
            fillcolor=fill_color if fill_target else None,
        ))
    fig.add_hline(y=total_val, line_dash="dash", line_color="gray",
                  annotation_text="Valeur actuelle", annotation_position="bottom right")
    fig.update_layout(**_LAYOUT, yaxis_title="Valeur ($)", xaxis_title="Jours de trading",
                      legend_title="Percentile", yaxis_tickprefix="$")
    return _style(fig)


def chart_contributors(contrib_df: pd.DataFrame) -> go.Figure:
    colors = [COLORS["success"] if v >= 0 else COLORS["danger"] for v in contrib_df["Contribution"]]
    fig = go.Figure(go.Bar(
        x=contrib_df["Symbol"],
        y=contrib_df["Contribution"] * 100,
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in contrib_df["Contribution"] * 100],
        textposition="outside",
    ))
    fig.update_layout(**_LAYOUT, yaxis_ticksuffix="%", yaxis_title="Contribution (%)",
                      xaxis_title="", showlegend=False)
    return _style(fig)


def chart_correlation_matrix(rets: pd.DataFrame) -> go.Figure:
    corr = rets.corr().round(2)
    fig  = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        zmin=-1, zmax=1,
        colorscale="RdBu_r",
        text=corr.values.round(2),
        texttemplate="%{text}",
        textfont=dict(size=11, color=COLORS["text"]),
        hoverongaps=False,
    ))
    fig.update_layout(**_LAYOUT, xaxis_tickangle=-35, yaxis_autorange="reversed")
    return _style(fig)


def chart_efficient_frontier(
    frontier_df: pd.DataFrame,
    current: dict,
    max_sharpe: dict,
    min_vol: dict,
) -> go.Figure:
    """Scatter cloud coloured by Sharpe with three special markers."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=frontier_df["Volatility"] * 100,
        y=frontier_df["Return"] * 100,
        mode="markers",
        marker=dict(
            size=4,
            color=frontier_df["Sharpe"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Sharpe", thickness=12,
                          tickfont=dict(color=COLORS["text"]),
                          title_font=dict(color=COLORS["text"])),
            opacity=0.6,
        ),
        name="Portfolios simulés",
        hovertemplate="Vol: %{x:.1f}%<br>Ret: %{y:.1f}%<extra></extra>",
    ))

    def _add_marker(ret, vol, name, color, symbol="star"):
        if ret is None or vol is None:
            return
        fig.add_trace(go.Scatter(
            x=[vol * 100], y=[ret * 100],
            mode="markers+text",
            marker=dict(size=16, color=color, symbol=symbol,
                        line=dict(width=2, color="white")),
            text=[name], textposition="top center",
            name=name,
        ))

    _add_marker(current.get("return"), current.get("volatility"),
                "Actuel", COLORS["warning"], "circle")
    if max_sharpe:
        _add_marker(max_sharpe.get("return"), max_sharpe.get("volatility"),
                    "Max Sharpe", COLORS["success"], "star")
    if min_vol:
        _add_marker(min_vol.get("return"), min_vol.get("volatility"),
                    "Min Volatilité", COLORS["primary"], "diamond")

    fig.update_layout(
        **_LAYOUT,
        xaxis_title="Volatilité annualisée (%)",
        yaxis_title="Rendement annualisé (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(color=COLORS["text"])),
        hovermode="closest",
    )
    return _style(fig)


# ── Single-stock charts ───────────────────────────────────────────────────────

def chart_price_history(hist: pd.DataFrame, ticker: str) -> go.Figure:
    if hist.empty:
        return go.Figure()
    perf  = (hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1
    color = COLORS["success"] if perf >= 0 else COLORS["danger"]
    fig   = px.area(
        hist, y="Close",
        title=f"{ticker}  {perf:+.1%}",
        labels={"Close": "Prix ($)", "Date": ""},
        color_discrete_sequence=[color],
    )
    fig.update_traces(fillcolor="rgba(0,104,201,0.08)")
    fig.update_layout(**_LAYOUT, xaxis_title=None, yaxis_title="Prix ($)")
    return _style(fig)


def chart_revenue_net_income(fin: pd.DataFrame) -> tuple[go.Figure, go.Figure]:
    """Returns (revenue_fig, net_income_fig) from annual financials."""
    empty = go.Figure()
    if fin.empty:
        return empty, empty

    df = fin.T.sort_index()

    fig_rev = go.Figure()
    if "Total Revenue" in df.columns:
        fig_rev.add_trace(go.Bar(
            x=df.index.astype(str), y=df["Total Revenue"] / 1e9,
            marker_color=COLORS["primary"],
            text=(df["Total Revenue"] / 1e9).round(1).astype(str) + "B",
            textposition="outside",
            textfont=dict(color=COLORS["text"]),
        ))
    fig_rev.update_layout(**_LAYOUT, yaxis_title="Revenue ($B)", xaxis_title=None,
                           showlegend=False)

    fig_ni = go.Figure()
    if "Net Income" in df.columns:
        bar_colors = [COLORS["success"] if v >= 0 else COLORS["danger"] for v in df["Net Income"]]
        fig_ni.add_trace(go.Bar(
            x=df.index.astype(str), y=df["Net Income"] / 1e9,
            marker_color=bar_colors,
            text=(df["Net Income"] / 1e9).round(1).astype(str) + "B",
            textposition="outside",
            textfont=dict(color=COLORS["text"]),
        ))
    fig_ni.update_layout(**_LAYOUT, yaxis_title="Net Income ($B)", xaxis_title=None,
                          showlegend=False)
    return _style(fig_rev), _style(fig_ni)


def chart_eps(earnings: pd.DataFrame) -> go.Figure:
    if earnings.empty:
        return go.Figure()
    try:
        eps = (
            earnings
            .dropna(subset=["Reported EPS"])
            .sort_index()
            .tail(10)
        )
        if eps.empty:
            return go.Figure()
        bar_colors = [COLORS["success"] if v >= 0 else COLORS["danger"] for v in eps["Reported EPS"]]
        fig = go.Figure(go.Bar(
            x=eps.index.astype(str),
            y=eps["Reported EPS"],
            marker_color=bar_colors,
            text=eps["Reported EPS"].round(2),
            textposition="outside",
            textfont=dict(color=COLORS["text"]),
        ))
        fig.update_layout(**_LAYOUT, yaxis_title="EPS ($)", xaxis_title=None,
                           xaxis_tickangle=-35, showlegend=False)
        return _style(fig)
    except Exception:
        return go.Figure()
