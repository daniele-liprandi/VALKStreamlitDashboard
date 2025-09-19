import requests
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

API_BASE = os.getenv("API_BASE")
API_VERSION = os.getenv("API_VERSION")
API_KEY = os.getenv("API_KEY")

def get_api_key():
    # Nur API-Key aus Session zulassen, sonst Fehler anzeigen
    return API_KEY

def get_json(path, params=None):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": get_api_key(),
        "apiversion": API_VERSION
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def post_json(path, data=None):
    url = f"{API_BASE}/{path}"
    headers = {
        "apikey": get_api_key(),
        "apiversion": API_VERSION
    }
    r = requests.post(url, headers=headers, json=data)
    r.raise_for_status()
    return r.status_code


# Faction Management API functions
def get_factions():
    """Get all configured factions"""
    factions_list = get_json("protected-faction")
    # Convert list to dictionary format for backward compatibility
    factions_dict = {}
    for faction in factions_list:
        factions_dict[faction["name"]] = {
            "id": faction["id"],
            "description": faction.get("description", ""),
            "webhook_url": faction.get("webhook_url", ""),
            "protected": faction.get("protected", False)
        }
    return factions_dict

def get_faction_status():
    """Get faction configuration status"""
    factions_list = get_json("protected-faction")
    total_factions = len(factions_list)
    protected_factions = sum(1 for f in factions_list if f.get("protected", False))
    custom_factions = total_factions - protected_factions
    
    # Check if there's a default webhook (assuming non-empty webhook_url indicates configured webhook)
    default_webhook = any(f.get("webhook_url") for f in factions_list)
    
    return {
        "total_factions": total_factions,
        "protected_factions": protected_factions,
        "custom_factions": custom_factions,
        "default_webhook": default_webhook
    }

def add_faction(name, description="Custom faction", webhook_url=None):
    """Add a new faction"""
    data = {
        "name": name,
        "description": description,
        "protected": False  # New factions are not protected by default
    }
    if webhook_url:
        data["webhook_url"] = webhook_url
    url = f"{API_BASE}/protected-faction"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.post(url, headers=headers, json=data)
    r.raise_for_status()
    return r.json()

def update_faction(faction_name, description=None, webhook_url=None):
    """Update a faction's description and/or webhook_url"""
    # First get the faction to find its ID
    factions = get_json("protected-faction")
    faction_id = None
    for faction in factions:
        if faction["name"] == faction_name:
            faction_id = faction["id"]
            break
    
    if faction_id is None:
        raise ValueError(f"Faction '{faction_name}' not found")
    
    data = {}
    if description is not None:
        data["description"] = description
    if webhook_url is not None:
        data["webhook_url"] = webhook_url
    url = f"{API_BASE}/protected-faction/{faction_id}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.put(url, headers=headers, json=data)
    r.raise_for_status()
    return r.json()

def delete_faction(faction_name):
    """Delete a faction"""
    # First get the faction to find its ID
    factions = get_json("protected-faction")
    faction_id = None
    for faction in factions:
        if faction["name"] == faction_name:
            faction_id = faction["id"]
            break
    
    if faction_id is None:
        raise ValueError(f"Faction '{faction_name}' not found")
    
    url = f"{API_BASE}/protected-faction/{faction_id}"
    headers = {
        "apikey": API_KEY,
        "apiversion": API_VERSION
    }
    r = requests.delete(url, headers=headers)
    r.raise_for_status()
    return {"status": "deleted"}