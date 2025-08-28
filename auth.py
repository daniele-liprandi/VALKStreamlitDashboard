import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE")

def verify_user(username, password):
    try:
        r = requests.post(f"{API_BASE}/login", json={"username": username, "password": password})
        if r.status_code == 200:
            return r.json()
        else:
            print(r.status_code)
            print(r.text)

        return None
    except Exception:
        return None

def user_has_access(user, page):
    if user.get("is_admin"):
        return True
    # Add page-specific permission check here if needed via API
    return True