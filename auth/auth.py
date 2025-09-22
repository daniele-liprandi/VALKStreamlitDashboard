import streamlit as st, json, os, asyncio, requests
from dotenv import load_dotenv

from auth import discord_oauth
from util import cookie_manager

# Load environment variables for API
load_dotenv()
API_BASE = os.getenv("API_BASE")
API_KEY = os.getenv("API_KEY")

def get_api_key():
    # Return API key from environment
    return API_KEY

def is_logged_in():
    """
    Check if a user is logged in, either via Discord OAuth or traditional login.
    Returns True if logged in, False otherwise.
    """
    # First, check for traditional login in session state
    if "user" in st.session_state and st.session_state.user:
        # User is logged in through traditional username/password
        return True
        
    # Then, check for Discord OAuth login
    cookies = cookie_manager.get()

    if 'token' in cookies and cookies['token'] != '':
        # User has a Discord token stored in cookies
        token = discord_oauth.json_str_to_token(cookies['token'])

        if not token.is_expired():
            # Valid Discord token, check if user info is in session state
            if "user_id" not in cookies or "user_username" not in cookies:
                # Missing user data, retrieve it
                try:
                    user_id, user_data = asyncio.run(
                        discord_oauth.get_id_data(token['access_token'])
                    )
                    cookies['user_id'] = user_id
                    cookies['user_username'] = user_data['username'] + '#' + user_data['discriminator']
                    cookies.save()
                except:
                    return False
            
            # Store Discord user info in session state if not already there
            if "user" not in st.session_state:
                st.session_state.user = {
                    "username": cookies['user_username'],
                    "discord_id": cookies['user_id'],
                    "is_admin": False,  # Default to non-admin
                    "login_type": "discord"
                }
                
            # Try to verify with backend if this is an admin
            try:
                verify_discord_with_backend(cookies['user_id'], cookies['user_username'])
            except Exception as e:
                print(f"Backend verification failed: {e}")
                # If backend check fails, still allow login but as non-admin
                pass
                
            return True
    
    # Check if we're in the OAuth flow
    try:
        code = st.query_params()['code']
    except:
        # No code parameter, not in OAuth flow
        return False

    # Process OAuth flow
    try:
        token = asyncio.run(
            discord_oauth.write_access_token(code)
        )

        if token.is_expired():
            return False

        cookies['token'] = json.dumps(token)

        user_id, user_data = asyncio.run(
            discord_oauth.get_id_data(token['access_token'])
        )

        cookies['user_id'] = user_id
        cookies['user_username'] = user_data['username'] + '#' + user_data['discriminator']

        cookies.save()
        st.experimental_set_query_params()
        
        # Initialize session state for Discord login
        st.session_state.user = {
            "username": user_data['username'] + '#' + user_data['discriminator'],
            "discord_id": user_id,
            "is_admin": False,  # Default to non-admin
            "login_type": "discord"
        }
        
        # Check with backend if this user is an admin
        try:
            verify_discord_with_backend(user_id, user_data['username'] + '#' + user_data['discriminator'])
        except Exception as e:
            print(f"Backend verification failed: {e}")
            # If backend check fails, still allow login but as non-admin
            pass
            
        return True
    except Exception as e:
        print(f"OAuth processing error: {e}")
        return False

def verify_user(username, password):
    """
    Verify a user with username and password against the backend API.
    Returns user data if successful, None otherwise.
    """
    headers = {}
    key = get_api_key()
    if key:
        headers["apikey"] = key
    try:
        r = requests.post(f"{API_BASE}/login", json={"username": username, "password": password}, headers=headers)
        if r.status_code == 200:
            # Store login type
            user_data = r.json()
            user_data["login_type"] = "traditional"
            return user_data
        else:
            print(r.status_code)
            print(r.text)
        return None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return None

def verify_discord_with_backend(discord_id, discord_username):
    """
    Verify a Discord user with the backend API to check if they're an admin.
    Updates session state with admin status.
    """
    headers = {}
    key = get_api_key()
    if key:
        headers["apikey"] = key
    try:
        # Modify this endpoint based on your actual API
        r = requests.post(
            f"{API_BASE}/verify_discord", 
            json={"discord_id": discord_id, "discord_username": discord_username}, 
            headers=headers
        )
        if r.status_code == 200:
            result = r.json()
            # Update session state with additional info from backend
            if "user" in st.session_state:
                st.session_state.user["is_admin"] = result.get("is_admin", False)
                st.session_state.user["tenant_name"] = result.get("tenant_name", "")
                # Add any other fields from the backend response
            return result
        return None
    except Exception as e:
        print(f"Error verifying Discord user with backend: {e}")
        return None

def user_has_access(user, page):
    """
    Check if a user has access to a specific page.
    Admin users have access to everything.
    """
    if user.get("is_admin"):
        return True
    # Add page-specific permission check here if needed
    return True

def logout():
    """
    Log out the user by clearing session state and cookies.
    """
    # Clear session state
    if "user" in st.session_state:
        st.session_state.pop("user")
    
    # Clear cookies for Discord login
    cookies = cookie_manager.get()
    if 'token' in cookies:
        cookies['token'] = ''
    if 'user_id' in cookies:
        cookies['user_id'] = ''
    if 'user_username' in cookies:
        cookies['user_username'] = ''
    cookies.save()