"""
Technical indicators computed locally from price series — no external API.
RSI (Wilder), MACD (12/26/9), Bollinger Bands (20, 2σ).
"""
import pandas as pd
import numpy as np


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI. Returns a Series aligned on close.index (NaN warm-up)."""
    if close is None or len(close) < period + 1:
        return pd.Series(dtype=float)

    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)

    # Wilder smoothing = EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # Flat-loss stretches → RSI = 100 by convention
    rsi = rsi.where(avg_loss > 0, 100.0)
    rsi[avg_gain.isna() | avg_loss.isna()] = np.nan
    return rsi


def calc_macd(close: pd.Series, fast: int = 12, slow: int = 26,
              signal: int = 9) -> pd.DataFrame:
    """MACD line, signal line and histogram. Columns: MACD, MACD_Signal, MACD_Hist."""
    if close is None or len(close) < slow + signal:
        return pd.DataFrame()

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd     = ema_fast - ema_slow
    sig      = macd.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "MACD":        macd,
        "MACD_Signal": sig,
        "MACD_Hist":   macd - sig,
    })


def calc_bollinger(close: pd.Series, period: int = 20,
                   n_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands. Columns: BB_Upper, BB_Middle, BB_Lower."""
    if close is None or len(close) < period:
        return pd.DataFrame()

    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return pd.DataFrame({
        "BB_Upper":  mid + n_std * std,
        "BB_Middle": mid,
        "BB_Lower":  mid - n_std * std,
    })


def technical_signals(close: pd.Series) -> dict:
    """
    Latest-value snapshot used by the UI: RSI level, MACD cross, BB position.
    Returns {} if not enough data.
    """
    rsi  = calc_rsi(close)
    macd = calc_macd(close)
    bb   = calc_bollinger(close)
    if rsi.empty or macd.empty or bb.empty:
        return {}

    last_rsi  = float(rsi.dropna().iloc[-1]) if not rsi.dropna().empty else None
    last_macd = macd.dropna()
    last_bb   = bb.dropna()
    if last_rsi is None or last_macd.empty or last_bb.empty:
        return {}

    m_line = float(last_macd["MACD"].iloc[-1])
    m_sig  = float(last_macd["MACD_Signal"].iloc[-1])
    price  = float(close.iloc[-1])
    upper  = float(last_bb["BB_Upper"].iloc[-1])
    lower  = float(last_bb["BB_Lower"].iloc[-1])

    if last_rsi > 70:   rsi_state = "Suracheté"
    elif last_rsi < 30: rsi_state = "Survendu"
    else:               rsi_state = "Neutre"

    if price > upper:   bb_state = "Au-dessus de la bande haute"
    elif price < lower: bb_state = "Sous la bande basse"
    else:               bb_state = "Dans les bandes"

    return {
        "rsi":        last_rsi,
        "rsi_state":  rsi_state,
        "macd":       m_line,
        "macd_signal": m_sig,
        "macd_state": "Haussier" if m_line > m_sig else "Baissier",
        "bb_state":   bb_state,
    }
