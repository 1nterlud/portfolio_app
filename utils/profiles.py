"""
Portfolio profiles — save / load multiple portfolios as JSON within session_state.
Optionally export to JSON file for cross-session persistence.
"""
import json
import streamlit as st
from datetime import datetime


_PROFILES_KEY = "portfolio_profiles"


def init_profiles() -> dict:
    """Make sure the profile store exists."""
    if _PROFILES_KEY not in st.session_state:
        st.session_state[_PROFILES_KEY] = {}
    return st.session_state[_PROFILES_KEY]


def list_profiles() -> list[str]:
    return list(init_profiles().keys())


def save_profile(name: str, payload: dict) -> None:
    """Save a portfolio profile under `name`."""
    if not name:
        return
    profiles = init_profiles()
    profiles[name] = {
        **payload,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }


def load_profile(name: str) -> dict | None:
    return init_profiles().get(name)


def delete_profile(name: str) -> None:
    profiles = init_profiles()
    profiles.pop(name, None)


def export_profiles_json() -> str:
    """Serialize all profiles to a JSON string for download."""
    return json.dumps(init_profiles(), indent=2, ensure_ascii=False)


def import_profiles_json(text: str) -> int:
    """Merge an uploaded JSON into the in-session profile store. Returns count added."""
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return 0
        profiles = init_profiles()
        n_before = len(profiles)
        profiles.update(data)
        return len(profiles) - n_before
    except Exception:
        return 0
