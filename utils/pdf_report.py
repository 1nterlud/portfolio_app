"""
PDF report builder using reportlab. Self-contained: no external chart export.
For charts, we render compact textual KPI cards + numbers — keeps deps minimal.
"""
from datetime import datetime
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        "H1Brand", parent=base["Heading1"], textColor=colors.HexColor("#0068C9"),
        fontSize=22, spaceAfter=8, fontName="Helvetica-Bold",
    ))
    base.add(ParagraphStyle(
        "H2Brand", parent=base["Heading2"], textColor=colors.HexColor("#1e293b"),
        fontSize=13, spaceBefore=14, spaceAfter=4, fontName="Helvetica-Bold",
    ))
    base.add(ParagraphStyle(
        "Body2", parent=base["BodyText"], fontSize=9.5,
        textColor=colors.HexColor("#1e293b"),
    ))
    base.add(ParagraphStyle(
        "Muted", parent=base["BodyText"], fontSize=8,
        textColor=colors.HexColor("#64748b"),
    ))
    return base


def _kpi_table(rows: list[tuple]) -> Table:
    t = Table(rows, colWidths=[5*cm, 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR",   (0, 0), (0, -1), colors.HexColor("#475569")),
        ("TEXTCOLOR",   (1, 0), (1, -1), colors.HexColor("#0f172a")),
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
            [colors.white, colors.HexColor("#fafbfc")]),
        ("BOX",   (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#e2e8f0")),
    ]))
    return t


def _positions_table(positions: list[list]) -> Table:
    """positions = [[Symbol, Qty, Val, W%, Sector], ...] with header as row 0."""
    t = Table(positions, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#0068C9")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("ALIGN",       (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#f8fafc")]),
        ("BOX",   (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.15, colors.HexColor("#e2e8f0")),
    ]))
    return t


def build_pdf_report(
    portfolio_name: str,
    total_val:   float,
    m:           dict,
    mpt:         dict,
    health:      dict,
    div_score:   dict,
    benchmark:   str,
    positions:   list[dict],
    strengths:   list[str],
    risks:       list[str],
    suggestions: list[str],
    version:     str = "2.0.0",
) -> bytes:
    """Render and return raw PDF bytes."""
    if not _REPORTLAB_OK:
        raise ImportError("reportlab n'est pas installé : pip install reportlab")
    buf  = BytesIO()
    doc  = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.4*cm, bottomMargin=1.4*cm,
        title=f"Rapport {portfolio_name}",
    )
    S = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(f"Portfolio Pro — Rapport", S["H1Brand"]))
    story.append(Paragraph(
        f"{portfolio_name} · Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
        f"Benchmark : {benchmark} · v{version}",
        S["Muted"],
    ))
    story.append(Spacer(1, 0.4*cm))

    # ── Hero value + Health Score ────────────────────────────────────────────
    hero = [
        [Paragraph(f"<b>Valeur Totale</b><br/>"
                   f"<font size=18 color='#0068C9'>${total_val:,.0f}</font>", S["Body2"]),
         Paragraph(f"<b>Health Score</b><br/>"
                   f"<font size=18 color='{health['color']}'>{health['score']}/100</font>"
                   f"<br/><font size=9>{health['label']}</font>", S["Body2"])],
    ]
    hero_t = Table(hero, colWidths=[8*cm, 8*cm])
    hero_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX",        (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
    ]))
    story.append(hero_t)
    story.append(Spacer(1, 0.4*cm))

    # ── Performance & risk KPIs ──────────────────────────────────────────────
    story.append(Paragraph("Performance & Risque", S["H2Brand"]))
    kpi_rows = [
        ["Rendement Total",  f"{m['total_ret']:+.1%}"],
        ["CAGR",             f"{m['cagr']:+.1%}"],
        ["Volatilité Ann.",  f"{m['vol']:.1%}"],
        ["Sharpe",           f"{m['sharpe']:.2f}"],
        ["Sortino",          f"{m['sortino']:.2f}"],
        ["Calmar",           f"{m['calmar']:.2f}"],
        ["Max Drawdown",     f"{m['max_dd']:.1%}"],
        ["VaR 95% (1j)",     f"{m['var_95']:.2%}"],
        ["CVaR 95% (1j)",    f"{m['cvar_95']:.2%}"],
    ]
    if mpt:
        kpi_rows += [
            [f"Beta vs {benchmark}",  f"{mpt['beta']:.2f}"],
            [f"Alpha annuel",         f"{mpt['alpha_ann']:+.1%}"],
            [f"Information Ratio",    f"{mpt.get('info_ratio', 0):.2f}"],
            [f"Tracking Error",       f"{mpt.get('tracking_error', 0):.1%}"],
        ]
    story.append(_kpi_table(kpi_rows))

    # ── Diversification ──────────────────────────────────────────────────────
    story.append(Paragraph("Diversification", S["H2Brand"]))
    story.append(Paragraph(
        f"<b>Score : {div_score['score']}/100</b> — {div_score['label']}",
        S["Body2"],
    ))

    # ── Diagnosis ────────────────────────────────────────────────────────────
    def _section(title, items, color):
        story.append(Paragraph(f"<font color='{color}'>{title}</font>", S["H2Brand"]))
        if not items:
            story.append(Paragraph("—", S["Muted"]))
            return
        for it in items:
            story.append(Paragraph(f"• {it}", S["Body2"]))

    _section("Points forts",   strengths,   "#29a352")
    _section("Risques",        risks,       "#dc3545")
    _section("Suggestions",    suggestions, "#0068C9")

    # ── Positions ────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Positions", S["H1Brand"]))

    header = ["Symbol", "Qty", "Prix", "Valeur", "Poids", "Secteur"]
    rows   = [header]
    for p in positions:
        rows.append([
            p.get("Symbol", ""),
            f"{p.get('Qty', 0):.2f}",
            f"${p.get('Prix', 0):,.2f}" if p.get("Prix") else "—",
            f"${p.get('Val', 0):,.0f}",
            f"{p.get('W', 0):.1%}",
            p.get("Secteur", "—"),
        ])
    story.append(_positions_table(rows))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        "Document généré automatiquement par Portfolio Pro. "
        "Ne constitue pas un conseil en investissement.",
        S["Muted"],
    ))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf
