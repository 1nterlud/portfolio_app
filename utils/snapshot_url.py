"""
Snapshot URL — serialize portfolio state into st.query_params so a link restores it.
"""
import base64
import json
import streamlit as st


def encode_state(payload: dict) -> str:
    """JSON → base64 (URL-safe) compact string."""
    raw = json.dumps(payload, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_state(token: str) -> dict | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return None


def set_share_link(payload: dict) -> str:
    """Encode + write to query_params; return the new URL fragment."""
    token = encode_state(payload)
    st.query_params["snap"] = token
    return f"?snap={token}"


def read_share_link() -> dict | None:
    token = st.query_params.get("snap")
    if not token:
        return None
    return decode_state(token)
