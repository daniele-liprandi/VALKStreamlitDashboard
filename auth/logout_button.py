import streamlit as st
from util import cookie_manager
from auth import auth

def render():
    if st.button("Logout"):
        # Use the centralized logout function from auth module
        auth.logout()
        
        # Force a page refresh to redirect to login
        st.rerun()