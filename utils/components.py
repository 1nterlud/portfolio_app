"""
Reusable visual components — badges, gauges, alert banners, hero headers,
section titles, freshness footer, empty states, key-value tables.

All return HTML strings (rendered via st.markdown with unsafe_allow_html=True)
or call streamlit directly. Keeps inline HTML out of UI files.
"""
from __future__ import annotations
import re
import streamlit as st
from config import BADGE_TONES, LEGACY_BADGE_MAP, COLORS


# ── Lightweight markdown / emoji utilities ────────────────────────────────────

_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# Heuristic: any leading run of non-ASCII (emoji) up to the first space
_EMOJI_RE = re.compile(r"^(\W+)\s+", re.UNICODE)


def _md_to_html(text: str) -> str:
    """Convert lightweight **bold** markdown to inline HTML."""
    return _MD_BOLD_RE.sub(r"<strong>\1</strong>", text)


def _split_emoji(text: str) -> tuple[str, str]:
    """Return (leading-emoji, rest). If no emoji prefix, return ('', text)."""
    text = text.lstrip()
    m = _EMOJI_RE.match(text)
    if m and not m.group(1).isascii():
        return m.group(1).strip(), text[m.end():].lstrip()
    return "", text


# Fallback icons per tone if no emoji prefix
_TONE_FALLBACK_ICON = {
    "success": "✓",
    "info":    "ⓘ",
    "warning": "⚠",
    "danger":  "⛔",
    "neutral": "•",
    "violet":  "★",
}


# ── Token helpers ─────────────────────────────────────────────────────────────

def _resolve_tone(tone: str) -> dict:
    """Accept new tone name OR legacy color name; fall back to neutral."""
    if tone in BADGE_TONES:
        return BADGE_TONES[tone]
    if tone in LEGACY_BADGE_MAP:
        return BADGE_TONES[LEGACY_BADGE_MAP[tone]]
    return BADGE_TONES["neutral"]


# ── Badges & chips ────────────────────────────────────────────────────────────

def badge_html(label: str, tone: str = "neutral") -> str:
    """Return a styled pill badge as HTML string."""
    t = _resolve_tone(tone)
    return (
        f"<span class='pp-chip' style='background:{t['bg']};color:{t['fg']};"
        f"border-color:{t['border']}'>{label}</span>"
    )


def render_badges(badges: list[tuple], max_per_row: int = 8) -> None:
    """Render a list of (label, tone) tuples as a wrapping row."""
    if not badges:
        return
    html = "<div style='display:flex;flex-wrap:wrap;gap:4px;margin:6px 0 10px 0'>"
    for label, tone in badges[:max_per_row]:
        html += badge_html(label, tone)
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── Hero header ───────────────────────────────────────────────────────────────

def render_page_hero(
    eyebrow: str,
    title: str,
    subtitle: str | None = None,
    pills: list[tuple] | None = None,
) -> None:
    """
    Premium page header — dark gradient banner with eyebrow / title / pills.
    pills = [(icon, label), ...] — small glass chips with metadata.
    """
    pills_html = ""
    if pills:
        pills_html = "<div class='pp-hero-meta'>"
        for icon, label in pills:
            pills_html += (
                f"<span class='pp-hero-pill'>"
                f"<span style='opacity:0.85'>{icon}</span>{label}</span>"
            )
        pills_html += "</div>"

    sub_html = (
        f"<div class='pp-hero-sub'>{subtitle}</div>" if subtitle else ""
    )

    st.markdown(
        f"""
        <div class='pp-hero'>
          <div class='pp-hero-eyebrow'>{eyebrow}</div>
          <div class='pp-hero-title'>{title}</div>
          {sub_html}
          {pills_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Hero value card ───────────────────────────────────────────────────────────

def render_hero_value(
    title: str, value: str, delta: str | None = None, delta_tone: str = "neutral"
) -> None:
    """Big gradient value card — used at the top of the dashboard."""
    arrow = ""
    if delta and delta_tone == "success":
        arrow = "▲ "
    elif delta and delta_tone == "danger":
        arrow = "▼ "
    delta_html = (
        f"<div class='pp-hero-value-delta'>{arrow}{delta}</div>" if delta else ""
    )
    st.markdown(
        f"""
        <div class='pp-hero-value'>
          <div class='pp-hero-value-label'>{title}</div>
          <div class='pp-hero-value-amount'>{value}</div>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Health gauge ──────────────────────────────────────────────────────────────

def render_health_gauge(score: int, label: str, color: str) -> None:
    """Premium circular score ring with label below."""
    bg_grad = (
        f"conic-gradient({color} 0deg, {color} {score * 3.6}deg, "
        f"#e2e8f0 {score * 3.6}deg, #e2e8f0 360deg)"
    )
    st.markdown(
        f"""
        <div class='pp-gauge-wrapper'>
          <div class='pp-gauge-ring' style='background:{bg_grad}'>
            <div class='pp-gauge-inner'>
              <span class='pp-gauge-score' style='color:{color}'>{score}</span>
              <span class='pp-gauge-suffix'>/ 100</span>
            </div>
          </div>
          <div class='pp-gauge-label' style='color:{color}'>{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Section title (icon + text) ───────────────────────────────────────────────

def render_section_title(icon: str, title: str, sub: str | None = None) -> None:
    """Small icon-tile + bold title — replaces st.subheader for premium feel."""
    sub_html = f"<span class='pp-section-title-sub'>· {sub}</span>" if sub else ""
    st.markdown(
        f"""
        <div class='pp-section-title'>
          <div class='pp-section-title-icon'>{icon}</div>
          <div>
            <span class='pp-section-title-text'>{title}</span>
            {sub_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Premium stat tile ─────────────────────────────────────────────────────────

def render_stat_tile(label: str, value: str, sub: str | None = None,
                     accent: str = "primary") -> None:
    """Compact custom stat tile — alternative to st.metric for hero rows."""
    accent_color = {
        "primary": COLORS["primary"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "danger":  COLORS["danger"],
        "violet":  COLORS["accent"],
    }.get(accent, COLORS["primary"])

    sub_html = f"<div class='pp-stat-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"""
        <div class='pp-stat' style='border-top:3px solid {accent_color}'>
          <div class='pp-stat-label'>{label}</div>
          <div class='pp-stat-value'>{value}</div>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Alert banner ──────────────────────────────────────────────────────────────

def render_alert_banner(alerts: list[tuple], title: str | None = None) -> None:
    """Top-of-page alert stack. alerts = [(level, message), ...].

    Premium card design: icon tile + bold-rendered text + tone-tinted gradient.
    """
    if not alerts:
        return

    # Resolve normalized tone keys so we can map to CSS classes
    norm_alerts = []
    for level, msg in alerts[:6]:
        tone = level if level in BADGE_TONES else LEGACY_BADGE_MAP.get(level, "neutral")
        norm_alerts.append((tone, msg))

    # Header row — count badge by severity
    counts = {}
    for tone, _ in norm_alerts:
        counts[tone] = counts.get(tone, 0) + 1

    severity_order = ["danger", "warning", "info", "success", "neutral", "violet"]
    chips = ""
    for sev in severity_order:
        if sev in counts:
            t = BADGE_TONES[sev]
            chips += (
                f"<span class='pp-alert-count' style='background:{t['bg']};"
                f"color:{t['fg']};border-color:{t['border']}'>"
                f"{counts[sev]}</span>"
            )

    head_title = title or "Alertes actives"
    header_html = (
        f"<div class='pp-alert-header'>"
        f"<div class='pp-alert-header-title'>"
        f"<span class='pp-alert-header-dot'></span>{head_title}"
        f"</div>"
        f"<div class='pp-alert-header-counts'>{chips}</div>"
        f"</div>"
    )

    # Alert cards
    items = ""
    for tone, raw_msg in norm_alerts:
        icon, body = _split_emoji(raw_msg)
        if not icon:
            icon = _TONE_FALLBACK_ICON.get(tone, "•")
        body_html = _md_to_html(body)
        items += (
            f"<div class='pp-alert pp-alert-{tone}'>"
            f"  <div class='pp-alert-icon'>{icon}</div>"
            f"  <div class='pp-alert-body'>{body_html}</div>"
            f"</div>"
        )

    st.markdown(
        f"<div class='pp-alert-stack'>{header_html}{items}</div>",
        unsafe_allow_html=True,
    )


# ── Audit / freshness caption ─────────────────────────────────────────────────

def render_audit_caption(source: str, fetched_at, n_days: int | None = None,
                         date_range: tuple | None = None) -> None:
    """Subtle caption explaining where the data comes from."""
    parts = [f"📡 Source : <b>{source}</b>"]
    if hasattr(fetched_at, "strftime"):
        parts.append(f"🕐 Récupéré à <b>{fetched_at.strftime('%H:%M:%S')}</b>")
    if n_days:
        parts.append(f"📊 <b>{n_days}</b> séances")
    if date_range:
        parts.append(f"📅 {date_range[0]} → {date_range[1]}")
    st.markdown(
        f"<div style='color:#94a3b8;font-size:0.76rem;margin-top:4px;"
        f"display:flex;flex-wrap:wrap;gap:14px'>"
        f"{''.join(f'<span>{p}</span>' for p in parts)}</div>",
        unsafe_allow_html=True,
    )


# ── Empty state ───────────────────────────────────────────────────────────────

def render_empty_state(title: str, hint: str, icon: str = "📭") -> None:
    """Designed empty state — replaces bare 'N/A' or 'No data'."""
    st.markdown(
        f"""
        <div class='pp-empty'>
          <div class='pp-empty-icon'>{icon}</div>
          <div class='pp-empty-title'>{title}</div>
          <div class='pp-empty-hint'>{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Key-value table ───────────────────────────────────────────────────────────

def render_kv_table(rows: list[tuple]) -> None:
    """Compact key-value table. Each row: (label, value, optional tone)."""
    lines = []
    for row in rows:
        key, val = row[0], row[1]
        tone = row[2] if len(row) > 2 else None
        color = _resolve_tone(tone)["fg"] if tone else "inherit"
        if val == "N/A":
            color = "#9e9e9e"
        lines.append(
            f"<tr><td style='color:#64748b;font-size:0.85rem'>{key}</td>"
            f"<td style='font-weight:600;color:{color};text-align:right'>"
            f"{val}</td></tr>"
        )
    st.markdown(
        f"<table>{''.join(lines)}</table>",
        unsafe_allow_html=True,
    )
    st.write("")


# ── Footer ────────────────────────────────────────────────────────────────────

def render_freshness_footer(version: str, last_fetch=None) -> None:
    """App version + last data refresh — pinned at the bottom of pages."""
    stamp = last_fetch.strftime("%Y-%m-%d %H:%M") if last_fetch else "—"
    st.markdown(
        f"""
        <div class='pp-footer'>
          <span class='pp-footer-dot'></span>
          Portfolio Pro <b>v{version}</b> · Données actualisées · {stamp}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Sidebar brand block ───────────────────────────────────────────────────────

def render_sidebar_brand(name: str, version: str, logo_letter: str = "P") -> None:
    """Premium sidebar header — logo tile + gradient name + version."""
    st.markdown(
        f"""
        <div class='pp-brand'>
          <div class='pp-brand-logo'>{logo_letter}</div>
          <div class='pp-brand-text'>
            <span class='pp-brand-name'>{name}</span>
            <span class='pp-brand-ver'>Premium · v{version}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
