import requests
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

API_BASE = os.getenv("API_BASE")

def get_api_key(api_key=None):
    # Verwende explizit übergebenen API-Key oder den aus der Session
    if api_key:
        return api_key
    if hasattr(st, "session_state") and "api_key" in st.session_state and st.session_state.api_key:
        return st.session_state.api_key
    return None

def verify_user(username, password, api_key=None):
    headers = {}
    key = get_api_key(api_key)
    if key:
        headers["apikey"] = key
    try:
        r = requests.post(f"{API_BASE}/login", json={"username": username, "password": password}, headers=headers)
        if r.status_code == 200:
            # Die Response enthält tenant_name, username, etc.
            return r.json()
        else:
            print(r.status_code)
            print(r.text)
        return None
    except Exception:
        return None

def user_has_access(user, page, api_key=None):
    # Optional: API-Key für weitere API-Requests verwenden
    if user.get("is_admin"):
        return True
    # Add page-specific permission check here if needed via API
    return True