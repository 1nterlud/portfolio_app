import pandas as pd
import io


def parse_positions(raw: str) -> pd.DataFrame:
    """
    Parse manual text input into a DataFrame.
    Expected format: one 'TICKER, Quantity' per line.
    Lines that are malformed or have quantity ≤ 0 are silently skipped.
    """
    rows = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        parts = line.split(",", 1)
        sym = parts[0].strip().upper()
        if not sym:
            continue
        try:
            qty = float(parts[1].strip())
            if qty > 0:
                rows.append({"Symbol": sym, "Qty": qty})
        except (ValueError, IndexError):
            pass
    return pd.DataFrame(rows)


def parse_csv_positions(file) -> pd.DataFrame:
    """
    Parse an uploaded CSV file into a standardised (Symbol, Qty) DataFrame.
    Accepted column names:
      - Symbol: symbol | ticker | sym | titre
      - Qty:    qty | quantity | shares | quantite | quantité | nombre
    """
    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip().str.lower()

        symbol_aliases = {"symbol", "ticker", "sym", "titre"}
        qty_aliases    = {"qty", "quantity", "shares", "quantite", "quantité", "nombre"}

        col_map = {}
        for col in df.columns:
            if col in symbol_aliases:
                col_map[col] = "Symbol"
            elif col in qty_aliases:
                col_map[col] = "Qty"

        df = df.rename(columns=col_map)
        if "Symbol" not in df.columns or "Qty" not in df.columns:
            return pd.DataFrame()

        df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
        df["Qty"]    = pd.to_numeric(df["Qty"], errors="coerce")
        return (
            df[["Symbol", "Qty"]]
            .dropna()
            .query("Qty > 0")
            .reset_index(drop=True)
        )
    except Exception:
        return pd.DataFrame()
