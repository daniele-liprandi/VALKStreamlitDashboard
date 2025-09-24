# discord_bot_roles.py
# Optional: Advanced role checking using Discord Bot
# This provides more granular control over role-based access

import asyncio
import aiohttp
import streamlit as st
from typing import Dict, Any, List, Optional

# Bot configuration from secrets
try:
    DISCORD_BOT_TOKEN = st.secrets["discord"]["bot_token"]
    DISCORD_SERVER_ID = st.secrets["discord"]["server_id"]
    REQUIRED_ROLES = st.secrets["discord"]["required_roles"]
except KeyError as e:
    print(f"Discord bot configuration missing: {e}")
    DISCORD_BOT_TOKEN = None

class DiscordBotRoleChecker:
    """
    Discord Bot-based role checker for more precise role verification.
    
    Setup Requirements:
    1. Create a Discord Application at https://discord.com/developers/applications
    2. Create a bot user and get the bot token
    3. Invite the bot to your server with these permissions:
       - Read Messages/View Channels
       - Read Message History (optional)
    4. Add the bot token to your secrets.toml
    """
    
    def __init__(self, bot_token: str, server_id: str):
        self.bot_token = bot_token
        self.server_id = server_id
        self.base_url = "https://discord.com/api/v10"
    
    async def get_user_roles(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's roles in the Discord server using the bot token.
        
        Returns:
            Dict with user role information and access status
        """
        if not self.bot_token:
            return {"error": "Bot token not configured"}
        
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Get guild member information
                url = f"{self.base_url}/guilds/{self.server_id}/members/{user_id}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        member_data = await response.json()
                        return await self._check_role_access(member_data, session, headers)
                    elif response.status == 404:
                        return {
                            "has_access": False,
                            "reason": "User is not a member of the Discord server",
                            "status_code": 404
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "has_access": False,
                            "reason": f"Discord API error: {response.status}",
                            "error": error_text
                        }
            except Exception as e:
                return {
                    "has_access": False,
                    "reason": f"Network error: {str(e)}",
                    "error": str(e)
                }
    
    async def _check_role_access(self, member_data: Dict, session: aiohttp.ClientSession, headers: Dict) -> Dict[str, Any]:
        """
        Check if the user has the required roles for access.
        """
        user_role_ids = member_data.get("roles", [])
        
        # Get detailed role information
        url = f"{self.base_url}/guilds/{self.server_id}/roles"
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    all_roles = await response.json()
                    role_lookup = {role["id"]: role for role in all_roles}
                    
                    # Get user's role names
                    user_roles = [role_lookup.get(role_id, {}).get("name", "Unknown") for role_id in user_role_ids]
                    
                    # Check if user has any required roles
                    has_required_role = self._user_has_required_role(user_role_ids, user_roles)
                    
                    return {
                        "has_access": has_required_role,
                        "user_roles": user_roles,
                        "user_role_ids": user_role_ids,
                        "required_roles": REQUIRED_ROLES,
                        "reason": "Access granted - user has required role" if has_required_role else "Access denied - user lacks required roles",
                        "member_since": member_data.get("joined_at"),
                        "nickname": member_data.get("nick")
                    }
                else:
                    # Fallback: just check if user is in server
                    return {
                        "has_access": True,  # User is in server, grant basic access
                        "reason": "User is in server (role check failed)",
                        "user_role_ids": user_role_ids,
                        "required_roles": REQUIRED_ROLES
                    }
        except Exception as e:
            # Fallback: just check if user is in server
            return {
                "has_access": True,  # User is in server, grant basic access
                "reason": f"User is in server (role check error: {str(e)})",
                "user_role_ids": user_role_ids,
                "error": str(e)
            }
    
    def _user_has_required_role(self, user_role_ids: List[str], user_role_names: List[str]) -> bool:
        """
        Check if the user has any of the required roles.
        Supports both role IDs and role names.
        """
        for required_role in REQUIRED_ROLES:
            # Check by role ID
            if required_role in user_role_ids:
                return True
            # Check by role name (case insensitive)
            if required_role.lower() in [name.lower() for name in user_role_names]:
                return True
        
        return False

    async def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about the Discord server.
        Useful for debugging and admin purposes.
        """
        if not self.bot_token:
            return {"error": "Bot token not configured"}
        
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Get guild information
                url = f"{self.base_url}/guilds/{self.server_id}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        guild_data = await response.json()
                        
                        # Get roles information
                        roles_url = f"{self.base_url}/guilds/{self.server_id}/roles"
                        async with session.get(roles_url, headers=headers) as roles_response:
                            if roles_response.status == 200:
                                roles_data = await roles_response.json()
                                guild_data["roles"] = roles_data
                        
                        return guild_data
                    else:
                        error_text = await response.text()
                        return {"error": f"Discord API error: {response.status}", "details": error_text}
            except Exception as e:
                return {"error": f"Network error: {str(e)}"}


# Initialize the bot role checker if configured
bot_role_checker = None
if DISCORD_BOT_TOKEN and DISCORD_SERVER_ID:
    bot_role_checker = DiscordBotRoleChecker(DISCORD_BOT_TOKEN, DISCORD_SERVER_ID)


async def check_user_roles_with_bot(user_id: str) -> Dict[str, Any]:
    """
    Check user roles using the Discord bot.
    
    Args:
        user_id: Discord user ID
        
    Returns:
        Dict with access information
    """
    if not bot_role_checker:
        return {
            "has_access": False,
            "reason": "Discord bot not configured",
            "error": "Missing bot configuration"
        }
    
    return await bot_role_checker.get_user_roles(user_id)


# Usage example in your auth.py:
"""
# In your process_oauth_callback function, replace the server access check with:

if DISCORD_BOT_TOKEN:
    # Use bot for more precise role checking
    access_check = asyncio.run(
        check_user_roles_with_bot(user_id)
    )
else:
    # Fallback to basic server membership check
    access_check = asyncio.run(
        discord_oauth.check_server_access(token['access_token'], user_id)
    )
"""

# Admin utility functions
async def get_server_stats() -> Dict[str, Any]:
    """
    Get server statistics for admin dashboard.
    Only works if bot is configured.
    """
    if not bot_role_checker:
        return {"error": "Bot not configured"}
    
    return await bot_role_checker.get_server_info()


async def list_users_with_roles() -> List[Dict[str, Any]]:
    """
    List all users in the server with their roles.
    Useful for admin purposes.
    """
    if not bot_role_checker:
        return [{"error": "Bot not configured"}]
    
    # This would require additional API calls to list all members
    # Implementation depends on your specific needs
    pass