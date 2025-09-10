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

def post_json(path, json_data=None):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.post(url, headers=headers, json=json_data)
    r.raise_for_status()
    return r.status_code

def put_json(path, json_data=None):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.put(url, headers=headers, json=json_data)
    r.raise_for_status()
    return r.json()

def delete_request(path):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.delete(url, headers=headers)
    r.raise_for_status()
    return r.json()

# Faction Management API functions
def get_factions():
    """Get all configured factions"""
    return get_json("factions")

def get_faction_status():
    """Get faction configuration status"""
    return get_json("factions/status")

def add_faction(name, description="Custom faction"):
    """Add a new faction"""
    from datetime import datetime
    data = {
        "name": name,
        "description": description,
        "timestamp": datetime.utcnow().isoformat()
    }
    url = f"{API_BASE}/factions"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.post(url, headers=headers, json=data)
    r.raise_for_status()
    return r.json()

def update_faction(faction_name, description):
    """Update a faction's description"""
    data = {"description": description}
    url = f"{API_BASE}/factions/{faction_name}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.put(url, headers=headers, json=data)
    r.raise_for_status()
    return r.json()

def delete_faction(faction_name):
    """Delete a faction"""
    url = f"{API_BASE}/factions/{faction_name}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.delete(url, headers=headers)
    r.raise_for_status()
    return r.json()