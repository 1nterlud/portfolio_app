import pandas as pd
import io


def parse_positions(raw: str) -> pd.DataFrame:
    """
    Parse manual text input.
    Format : `TICKER, Quantity[, CostBasis]` per line.
    CostBasis is optional — used for P&L calculations.
    """
    rows = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        parts = [p.strip() for p in line.split(",")]
        sym   = parts[0].upper()
        if not sym:
            continue
        try:
            qty = float(parts[1])
            if qty <= 0:
                continue
        except (ValueError, IndexError):
            continue

        cost = None
        if len(parts) >= 3:
            try:
                cost = float(parts[2])
                if cost <= 0:
                    cost = None
            except ValueError:
                cost = None

        rows.append({"Symbol": sym, "Qty": qty, "CostBasis": cost})

    return pd.DataFrame(rows)


def parse_csv_positions(file) -> pd.DataFrame:
    """
    Parse CSV.
    Recognised columns:
      Symbol/Ticker/Sym/Titre
      Qty/Quantity/Shares/Quantite/Nombre
      CostBasis/Prix/Price/PriceAchat  (optional)
    """
    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip().str.lower()

        sym_a   = {"symbol", "ticker", "sym", "titre"}
        qty_a   = {"qty", "quantity", "shares", "quantite", "quantité", "nombre"}
        cost_a  = {"costbasis", "cost_basis", "cost", "prix",
                   "price", "priceachat", "prixachat", "px"}

        col_map = {}
        for col in df.columns:
            if col in sym_a:   col_map[col] = "Symbol"
            elif col in qty_a: col_map[col] = "Qty"
            elif col in cost_a: col_map[col] = "CostBasis"

        df = df.rename(columns=col_map)
        if "Symbol" not in df.columns or "Qty" not in df.columns:
            return pd.DataFrame()

        df["Symbol"]   = df["Symbol"].astype(str).str.strip().str.upper()
        df["Qty"]      = pd.to_numeric(df["Qty"], errors="coerce")
        if "CostBasis" in df.columns:
            df["CostBasis"] = pd.to_numeric(df["CostBasis"], errors="coerce")
        else:
            df["CostBasis"] = None

        return (
            df[["Symbol", "Qty", "CostBasis"]]
            .dropna(subset=["Symbol", "Qty"])
            .query("Qty > 0")
            .reset_index(drop=True)
        )
    except Exception:
        return pd.DataFrame()
