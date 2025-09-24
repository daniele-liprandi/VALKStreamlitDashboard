import os, json
from typing import cast, Dict, Any
from httpx_oauth.clients.discord import DiscordOAuth2, PROFILE_ENDPOINT
from httpx_oauth.oauth2 import OAuth2Token
from httpx_oauth.exceptions import GetIdEmailError
import streamlit as st

# Get credentials from Streamlit's secrets.toml
client_id = st.secrets["auth"]["client_id"]
client_secret = st.secrets["auth"]["client_secret"]
redirect_uri = st.secrets["auth"]["redirect_uri"]

class MyDiscordOAuth2(DiscordOAuth2):
    async def get_id_data(self, token: str):
        """Get Discord user ID and profile data."""
        async with self.get_httpx_client() as client:
            response = await client.get(
                PROFILE_ENDPOINT,
                headers={**self.request_headers, "Authorization": f"Bearer {token}"},
            )

            if response.status_code >= 400:
                raise GetIdEmailError(response.json())

            data = cast(Dict[str, Any], response.json())
            user_id = data["id"]
            return user_id, data

client = MyDiscordOAuth2(client_id, client_secret)

def get_client():
    return client

async def write_authorization_url():
    client = get_client()
    authorization_url = await client.get_authorization_url(
        redirect_uri,
        scope=["identify"],  # Only need identify since bot handles server checking
        extras_params={"access_type": "offline"},
    )
    return authorization_url

async def write_access_token(code):
    token = await client.get_access_token(code, redirect_uri)
    return token

async def get_id_data(token):
    user_id, user_data = await client.get_id_data(token)
    return user_id, user_data

def json_str_to_token(token):
    return OAuth2Token(cast(Dict[str, Any], json.loads(token)))