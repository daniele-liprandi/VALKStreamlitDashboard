import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Production API base URL
API_BASE = os.getenv("API_BASE")

# Debugging locally
#API_BASE = "http://localhost:5000/api"

# API key for authentication
API_KEY = os.getenv("API_KEY")
API_VERSION = os.getenv("API_VERSION")

def get_json(path, params=None):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()

def post_json(path):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.post(url, headers=headers)
    r.raise_for_status()
    return r.status_code