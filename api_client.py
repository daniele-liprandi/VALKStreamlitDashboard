import requests
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

API_BASE = os.getenv("API_BASE")
API_VERSION = os.getenv("API_VERSION")

def get_api_key():
    # Nur API-Key aus Session zulassen, sonst Fehler anzeigen
    if hasattr(st, "session_state") and "api_key" in st.session_state and st.session_state.api_key:
        return st.session_state.api_key
    st.error("Kein API-Key in der Sitzung gefunden. Bitte loggen Sie sich erneut ein und geben Sie einen API-Key an.")
    raise RuntimeError("API-Key fehlt in der Session.")


def get_json(path, params=None):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": get_api_key(),
        "apiversion": API_VERSION
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def post_json(path):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": get_api_key(),
        "apiversion": API_VERSION
    }
    r = requests.post(url, headers=headers)
    r.raise_for_status()
    return r.status_code