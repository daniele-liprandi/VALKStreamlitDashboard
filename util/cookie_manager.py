import streamlit as st, os, hashlib
from util.encrypted_cookie_manager import EncryptedCookieManager

# Get cookie secret from Streamlit's secrets.toml
cookie_secret = st.secrets["auth"]["cookie_secret"]

# Create a unique prefix per browser session to prevent cross-user contamination
def get_session_id():
    if 'session_id' not in st.session_state:
        session_data = str(id(st.session_state))
        st.session_state.session_id = hashlib.md5(session_data.encode()).hexdigest()[:12]
    return st.session_state.session_id

# Create user-specific cookie prefix
session_id = get_session_id()
unique_prefix = f"streamlit_auth_{session_id}/"

# This should be on top of your script
cookies = EncryptedCookieManager(
    # Each user gets their own cookie namespace
    prefix=unique_prefix,
    # You should really setup a long COOKIES_PASSWORD secret if you're running on Streamlit Cloud.
    password=cookie_secret,
)

if not cookies.ready():
    # Wait for the component to load and send us current cookies.
    st.stop()

def get():
    return cookies