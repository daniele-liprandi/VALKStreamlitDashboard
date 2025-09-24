import streamlit as st, json, os, asyncio, requests
from dotenv import load_dotenv

from auth import discord_oauth
from util import cookie_manager

# Load environment variables for API
load_dotenv()
API_BASE = os.getenv("API_BASE")
API_KEY = os.getenv("API_KEY")

# Try to import bot functionality with better error handling
BOT_AVAILABLE = False
check_user_roles_with_bot = None

try:
    # Check if bot configuration exists first
    if "discord" in st.secrets and "bot_token" in st.secrets["discord"] and st.secrets["discord"]["bot_token"]:
        from auth.discord_bot_roles import check_user_roles_with_bot
        BOT_AVAILABLE = True
        print("✅ Discord bot functionality loaded successfully")
    else:
        print("ℹ️ Bot token not found in secrets - using basic server check")
except ImportError as e:
    print(f"ℹ️ Discord bot module not available: {e}")
    BOT_AVAILABLE = False
except Exception as e:
    print(f"⚠️ Error loading bot functionality: {e}")
    BOT_AVAILABLE = False

def get_api_key():
    return API_KEY

def get_access_control_info():
    """
    Get information about which access control method is being used.
    This helps with debugging.
    """
    info = {
        "bot_available": BOT_AVAILABLE,
        "access_method": "Discord Bot Role Check" if BOT_AVAILABLE else "Basic Server Membership",
        "server_id": st.secrets.get("discord", {}).get("server_id", "Not configured"),
        "required_roles": st.secrets.get("discord", {}).get("required_roles", []),
        "bot_configured": bool(st.secrets.get("discord", {}).get("bot_token"))
    }
    return info

def is_logged_in():
    """
    Check if a user is logged in, either via Discord OAuth or traditional login.
    Returns True if logged in, False otherwise.
    """
    # First, check for traditional login in session state
    if "user" in st.session_state and st.session_state.user:
        return True
    
    # Check if we're in the OAuth flow FIRST
    query_params = st.query_params
    if 'code' in query_params:
        return process_oauth_callback(query_params['code'])
        
    # Then, check for Discord OAuth login in cookies
    cookies = cookie_manager.get()

    if 'token' in cookies and cookies['token'] != '' and 'discord_access_verified' in cookies:
        try:
            token = discord_oauth.json_str_to_token(cookies['token'])

            if not token.is_expired():
                if "user_id" not in cookies or "user_username" not in cookies:
                    user_id, user_data = asyncio.run(
                        discord_oauth.get_id_data(token['access_token'])
                    )
                    cookies['user_id'] = user_id
                    cookies['user_username'] = user_data['username'] + '#' + user_data['discriminator']
                    cookies.save()
                
                if "user" not in st.session_state:
                    st.session_state.user = {
                        "username": cookies['user_username'],
                        "discord_id": cookies['user_id'],
                        "is_admin": False,
                        "login_type": "discord",
                        "server_access": cookies.get('discord_access_verified') == 'true',
                        "user_roles": json.loads(cookies.get('user_roles', '[]')),
                        "access_method": cookies.get('access_method', 'Unknown')
                    }
                    
                try:
                    backend_result = verify_discord_with_backend(cookies['user_id'], cookies['user_username'])
                    if backend_result:
                        st.session_state.user.update(backend_result)
                except Exception as e:
                    print(f"Backend verification failed: {e}")
                    
                return True
        except Exception as e:
            print(f"Error checking Discord login: {e}")
            clear_discord_cookies()
            return False
    
    return False

def process_oauth_callback(code):
    """
    Process the OAuth callback with the authorization code.
    Now uses bot for advanced role checking if available.
    """
    try:
        # Show which method we're using
        access_info = get_access_control_info()
        print(f"🔍 Using access control method: {access_info['access_method']}")
        
        # Get access token
        token = asyncio.run(discord_oauth.write_access_token(code))

        if token.is_expired():
            print("Received expired token from Discord")
            st.error("Discord login expired. Please try again.")
            return False

        # Get user data
        user_id, user_data = asyncio.run(discord_oauth.get_id_data(token['access_token']))
        print(f"🔍 Processing login for user: {user_data['username']}#{user_data['discriminator']} (ID: {user_id})")

        # Bot-only access checking - no fallback
        if not BOT_AVAILABLE or not check_user_roles_with_bot:
            st.error("❌ Discord bot is not available. Bot configuration is required for access.")
            st.info("Please contact an administrator to configure the Discord bot.")
            clear_discord_cookies()
            return False
            
        print("🤖 Using Discord bot for role checking...")
        access_check = asyncio.run(check_user_roles_with_bot(user_id))
        access_method = "Discord Bot Role Check"
        
        print(f"🔍 Access check result: {access_check}")
        
        if not access_check.get('has_access', False):
            reason = access_check.get('reason', 'Access denied')
            print(f"❌ Access denied: {reason}")
            
            st.error(f"🚫 Access Denied: {reason}")
            
            # Show specific help based on the reason
            if "not a member" in reason.lower():
                st.info("💡 **Need access?** Ask a server admin for an invite to the Discord server.")
            elif "lacks required roles" in reason.lower() or "required role" in reason.lower():
                required_roles = access_check.get('required_roles', [])
                user_roles = access_check.get('user_roles', [])
                
                st.info(f"💡 **Role Issue:** You need one of these roles: {', '.join(map(str, required_roles))}")
                if user_roles:
                    st.info(f"🏷️ **Your current roles:** {', '.join(user_roles)}")
                st.info("Contact a server admin to get the required role.")
            
            # Show debug info for troubleshooting
            with st.expander("🔧 Debug Information"):
                st.write("**Access Control Method:**", access_method)
                st.write("**Bot Available:**", BOT_AVAILABLE)
                st.json(access_check)
            
            clear_discord_cookies()
            return False

        print(f"✅ Access granted via {access_method}")
        
        # Store successful login data
        cookies = cookie_manager.get()
        cookies['token'] = json.dumps(token)
        cookies['user_id'] = user_id
        cookies['user_username'] = user_data['username'] + '#' + user_data['discriminator']
        cookies['discord_access_verified'] = 'true'
        cookies['server_name'] = access_check.get('server_name', 'Discord Server')
        cookies['access_method'] = access_method
        
        # Store user roles if available from bot check
        user_roles = access_check.get('user_roles', [])
        cookies['user_roles'] = json.dumps(user_roles)
        
        cookies.save()
        
        # Initialize session state
        st.session_state.user = {
            "username": user_data['username'] + '#' + user_data['discriminator'],
            "discord_id": user_id,
            "is_admin": False,
            "login_type": "discord",
            "server_access": True,
            "server_name": access_check.get('server_name', 'Discord Server'),
            "user_roles": user_roles,
            "member_since": access_check.get('member_since'),
            "nickname": access_check.get('nickname'),
            "access_method": access_method
        }
        
        # Backend verification
        try:
            backend_result = verify_discord_with_backend(user_id, user_data['username'] + '#' + user_data['discriminator'])
            if backend_result:
                st.session_state.user.update(backend_result)
        except Exception as e:
            print(f"Backend verification failed: {e}")
        
        # Clear OAuth code and show success
        st.query_params.clear()
        
        # Show success message with method info
        if user_roles:
            st.success(f"✅ Welcome! Access granted via **{access_method}** with roles: {', '.join(user_roles)}")
        else:
            st.success(f"✅ Welcome! Access granted via **{access_method}**")
        
        # Show debug info for admins
        if st.session_state.user.get("is_admin"):
            with st.expander("🔧 Admin Debug Info"):
                st.write("**Access Method:**", access_method)
                st.write("**Bot Available:**", BOT_AVAILABLE)
                st.json(access_check)
            
        st.rerun()
        return True
        
    except Exception as e:
        print(f"OAuth processing error: {e}")
        clear_discord_cookies()
        if "user" in st.session_state:
            del st.session_state.user
        st.error(f"❌ Login failed: {str(e)}")
        
        # Show debug info on error
        with st.expander("🔧 Debug Information"):
            access_info = get_access_control_info()
            st.json(access_info)
            st.text(f"Error: {str(e)}")
        
        return False

def clear_discord_cookies():
    """Clear Discord-related cookies."""
    cookies = cookie_manager.get()
    keys_to_clear = ['token', 'user_id', 'user_username', 'discord_access_verified', 'server_name', 'user_roles', 'access_method']
    for key in keys_to_clear:
        cookies[key] = ''
    cookies.save()

def verify_user(username, password):
    """Verify traditional username/password login."""
    headers = {}
    key = get_api_key()
    if key:
        headers["apikey"] = key
    try:
        r = requests.post(f"{API_BASE}/login", json={"username": username, "password": password}, headers=headers)
        if r.status_code == 200:
            user_data = r.json()
            user_data["login_type"] = "traditional"
            return user_data
        else:
            print(f"Login failed: {r.status_code} - {r.text}")
        return None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return None

def verify_discord_with_backend(discord_id, discord_username):
    """Verify Discord user with backend for admin status."""
    headers = {}
    key = get_api_key()
    if key:
        headers["apikey"] = key
    try:
        r = requests.post(
            f"{API_BASE}/verify_discord", 
            json={"discord_id": discord_id, "discord_username": discord_username}, 
            headers=headers
        )
        if r.status_code == 200:
            result = r.json()
            return {
                "is_admin": result.get("is_admin", False),
                "tenant_name": result.get("tenant_name", "")
            }
        return None
    except Exception as e:
        print(f"Error verifying Discord user with backend: {e}")
        return None

def user_has_access(user, page):
    """Check if user has access to a specific page."""
    if user.get("is_admin"):
        return True
    
    if user.get("login_type") == "discord":
        return user.get("server_access", False)
    
    return True

def logout():
    """Log out the user by clearing session state and cookies."""
    for key in ["user", "tenant_name"]:
        if key in st.session_state:
            del st.session_state[key]
    
    clear_discord_cookies()

def show_access_control_status():
    """
    Display current access control configuration.
    Useful for debugging and admin purposes.
    """
    info = get_access_control_info()
    
    st.subheader("🔧 Access Control Status")
    
    # Show current method
    if info["bot_available"]:
        st.success(f"✅ Using: **{info['access_method']}**")
    else:
        st.info(f"ℹ️ Using: **{info['access_method']}**")
    
    # Configuration details
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Bot Configured", "Yes" if info["bot_configured"] else "No")
        st.metric("Bot Available", "Yes" if info["bot_available"] else "No")
    
    with col2:
        st.metric("Server ID", info["server_id"])
        if info["required_roles"]:
            st.write("**Required Roles:**")
            for role in info["required_roles"]:
                st.write(f"- {role}")
        else:
            st.write("**Required Roles:** None configured")
    
    # Current user info
    if "user" in st.session_state and st.session_state.user.get("login_type") == "discord":
        st.subheader("👤 Current User")
        user = st.session_state.user
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Username:** {user.get('username')}")
            st.write(f"**Access Method:** {user.get('access_method', 'Unknown')}")
            st.write(f"**Server:** {user.get('server_name', 'Unknown')}")
        
        with col2:
            user_roles = user.get('user_roles', [])
            if user_roles:
                st.write("**Your Roles:**")
                for role in user_roles:
                    st.write(f"- {role}")
            else:
                st.write("**Your Roles:** None detected")
            
            if user.get('member_since'):
                st.write(f"**Member Since:** {user.get('member_since')[:10]}")

def reverify_discord_access():
    """Re-verify Discord server access for the current user."""
    if "user" not in st.session_state or st.session_state.user.get("login_type") != "discord":
        return True
    
    cookies = cookie_manager.get()
    if 'token' not in cookies or cookies['token'] == '':
        return False
    
    try:
        token = discord_oauth.json_str_to_token(cookies['token'])
        if token.is_expired():
            return False
        
        user_id = cookies.get('user_id')
        
        if BOT_AVAILABLE and check_user_roles_with_bot:
            access_check = asyncio.run(check_user_roles_with_bot(user_id))
        else:
            access_check = asyncio.run(discord_oauth.check_server_access(token['access_token'], user_id))
        
        if not access_check.get('has_access', False):
            logout()
            st.error("🚫 Your Discord server access has been revoked.")
            st.rerun()
            return False
        
        return True
        
    except Exception as e:
        print(f"Error re-verifying Discord access: {e}")
        return True  # Don't log out on temporary errors