import streamlit as st
import api_client
from datetime import datetime

def render():
    st.title("🏛️ Faction Management")
    
    # Check if user is admin
    user = st.session_state.get("user", {})
    if not user.get("is_admin"):
        st.error("⛔ Access denied. This page requires administrator privileges.")
        return
    
    try:
        # Get faction status and current factions
        status = api_client.get_faction_status()
        factions = api_client.get_factions()
        
        # Display status overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Factions", status.get("total_factions", 0))
        with col2:
            st.metric("Protected Factions", status.get("protected_factions", 0))
        with col3:
            st.metric("Custom Factions", status.get("custom_factions", 0))
        with col4:
            webhook_status = "✅ OK" if status.get("default_webhook") else "❌ Missing"
            st.metric("Default Webhook", webhook_status)
        
        st.divider()
        
        # Add new faction section
        st.subheader("➕ Add New Faction")
        st.info("ℹ️ New factions will use the default BGS webhook and can be deleted later.")
        
        with st.form("add_faction_form"):
            col1, col2 = st.columns([2, 3])
            
            with col1:
                new_faction_name = st.text_input(
                    "Faction Name",
                    placeholder="Enter faction name...",
                    help="The exact faction name as it appears in Elite Dangerous"
                )
            
            with col2:
                new_faction_description = st.text_input(
                    "Description (Optional)",
                    placeholder="Brief description of this faction...",
                    value="Custom faction"
                )
            
            submit_add = st.form_submit_button("Add Faction", type="primary")
            
            if submit_add:
                if new_faction_name.strip():
                    try:
                        result = api_client.add_faction(
                            new_faction_name.strip(),
                            new_faction_description.strip()
                        )
                        st.success(f"✅ Successfully added faction: {new_faction_name}")
                        st.rerun()
                    except Exception as e:
                        if "already exists" in str(e):
                            st.error(f"❌ Faction '{new_faction_name}' already exists!")
                        else:
                            st.error(f"❌ Error adding faction: {str(e)}")
                else:
                    st.error("❌ Faction name cannot be empty!")
        
        st.divider()
        
        # Current factions table
        st.subheader("📋 Current Factions")
        
        if not factions:
            st.warning("No factions configured.")
            return
        
        # Group factions by protection status
        protected_factions = {k: v for k, v in factions.items() if v.get("protected", False)}
        custom_factions = {k: v for k, v in factions.items() if not v.get("protected", False)}
        
        # Protected factions section
        if protected_factions:
            st.markdown("**🛡️ Protected Factions** *(Cannot be modified or deleted)*")
            
            for faction_name, config in protected_factions.items():
                with st.container():
                    col1, col2, col3 = st.columns([3, 4, 1])
                    
                    with col1:
                        st.markdown(f"**{faction_name}**")
                    
                    with col2:
                        st.markdown(f"*{config.get('description', 'No description')}*")
                    
                    with col3:
                        st.markdown("🔒 Protected")
            
            st.divider()
        
        # Custom factions section
        if custom_factions:
            st.markdown("**⚙️ Custom Factions** *(Can be modified or deleted)*")
            
            for faction_name, config in custom_factions.items():
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{faction_name}**")
                    
                    with col2:
                        # Editable description
                        description_key = f"desc_{faction_name}"
                        if description_key not in st.session_state:
                            st.session_state[description_key] = config.get('description', '')
                        
                        new_description = st.text_input(
                            "Description",
                            value=st.session_state[description_key],
                            key=f"input_{description_key}",
                            label_visibility="collapsed"
                        )
                        
                        if new_description != st.session_state[description_key]:
                            st.session_state[description_key] = new_description
                    
                    with col3:
                        # Update button
                        if st.button("💾", key=f"update_{faction_name}", help="Update description"):
                            try:
                                api_client.update_faction(faction_name, st.session_state[description_key])
                                st.success("Updated!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    
                    with col4:
                        # Delete button
                        if st.button("🗑️", key=f"delete_{faction_name}", help="Delete faction"):
                            if st.session_state.get(f"confirm_delete_{faction_name}"):
                                try:
                                    api_client.delete_faction(faction_name)
                                    st.success(f"Deleted {faction_name}")
                                    # Clean up session state
                                    if description_key in st.session_state:
                                        del st.session_state[description_key]
                                    if f"confirm_delete_{faction_name}" in st.session_state:
                                        del st.session_state[f"confirm_delete_{faction_name}"]
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                            else:
                                st.session_state[f"confirm_delete_{faction_name}"] = True
                                st.warning("Click delete again to confirm!")
                                st.rerun()
        else:
            st.info("No custom factions configured. Add one above to get started!")
        
        # Discord Controls Section
        st.divider()
        st.subheader("📢 Discord Controls")
        st.info("🔧 Admin-only: Trigger Discord notifications manually")
        
        # Discord trigger buttons in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📊 Daily Summary**")
            if st.button("📈 Send Daily Summary", help="Send yesterday's activity summary to Discord"):
                try:
                    api_client.post_json("summary/discord/tick")
                    st.success("✅ Daily summary sent to Discord!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("**⚔️ Space CZ Summary**")
            period_space = st.selectbox(
                "Period",
                options=["ld", "lw", "cm", "lm", "2m", "y", "all"],
                format_func=lambda x: {
                    "ld": "Last Day", "lw": "Last Week", "cm": "Current Month",
                    "lm": "Last Month", "2m": "Last 2 Months", "y": "Year", "all": "All Time"
                }[x],
                key="space_period"
            )
            if st.button("🚀 Send Space CZ", help="Send space conflict zone summary"):
                try:
                    api_client.post_json("summary/discord/syntheticcz", {"period": period_space})
                    st.success(f"✅ Space CZ summary sent ({period_space})!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with col3:
            st.markdown("**🏃 Ground CZ Summary**")
            period_ground = st.selectbox(
                "Period",
                options=["ld", "lw", "cm", "lm", "2m", "y", "all"],
                format_func=lambda x: {
                    "ld": "Last Day", "lw": "Last Week", "cm": "Current Month",
                    "lm": "Last Month", "2m": "Last 2 Months", "y": "Year", "all": "All Time"
                }[x],
                key="ground_period"
            )
            if st.button("🔫 Send Ground CZ", help="Send ground conflict zone summary"):
                try:
                    api_client.post_json("summary/discord/syntheticgroundcz", {"period": period_ground})
                    st.success(f"✅ Ground CZ summary sent ({period_ground})!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Custom message section
        st.markdown("**💬 Custom Message**")
        with st.form("custom_discord_message"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                custom_message = st.text_area(
                    "Message Content",
                    placeholder="Enter your custom message for Discord...",
                    height=100,
                    help="This message will be sent to the selected Discord channel"
                )
            
            with col2:
                webhook_choice = st.selectbox(
                    "Channel",
                    options=["shoutout", "bgs"],
                    format_func=lambda x: "📢 Shoutout" if x == "shoutout" else "🛡️ BGS",
                    help="Choose which Discord channel to send to"
                )
                
                username = st.text_input(
                    "Your Name",
                    value=user.get("username", "Admin"),
                    help="Name to show as sender"
                )
            
            submit_message = st.form_submit_button("📤 Send Message", type="primary")
            
            if submit_message:
                if custom_message.strip():
                    try:
                        api_client.post_json("discord/trigger/custom-message", {
                            "content": custom_message.strip(),
                            "webhook": webhook_choice,
                            "username": username
                        })
                        st.success(f"✅ Message sent to {webhook_choice} channel!")
                    except Exception as e:
                        st.error(f"❌ Error sending message: {str(e)}")
                else:
                    st.error("❌ Message content cannot be empty!")
        
        # Quick actions
        st.markdown("**⚡ Quick Actions**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Trigger Faction Conflicts", help="Check all factions for conflicts"):
                try:
                    api_client.post_json("debug/multi-faction-conflicts")
                    st.success("✅ Faction conflict check triggered!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with col2:
            if st.button("👥 Sync Commanders", help="Sync commander data with INARA"):
                try:
                    api_client.post_json("sync/cmdrs")
                    st.success("✅ Commander sync completed!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with col3:
            if st.button("📊 All Top 5 to Discord", help="Send all top 5 leaderboards"):
                try:
                    api_client.post_json("summary/discord/top5all")
                    st.success("✅ All top 5 summaries sent!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        st.divider()
        
        # Help section
        st.subheader("ℹ️ Help")
        
        with st.expander("How does faction management work?"):
            st.markdown("""
            **Protected Factions:**
            - `Communism Interstellar` and `People's Party of Heverty` are hardcoded
            - These cannot be modified or deleted
            - They use the configured BGS webhook
            
            **Custom Factions:**
            - You can add any faction name here
            - All custom factions use the default BGS webhook
            - You can update descriptions and delete custom factions
            - Changes take effect immediately for the conflict monitoring scheduler
            
            **Conflict Monitoring:**
            - The system checks for conflicts every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
            - When conflicts are found, notifications are sent to the appropriate Discord webhook
            - All custom factions use the same default BGS webhook
            """)
        
        with st.expander("Discord Controls Guide"):
            st.markdown("""
            **Daily Summary:**
            - Sends a comprehensive report of yesterday's activities
            - Includes market events, missions, influence, bounties, exploration, etc.
            - Goes to the Shoutout Discord channel
            
            **Space/Ground CZ Summaries:**
            - Sends conflict zone statistics for the selected time period
            - Shows system-by-system breakdown and commander participation
            - Useful for tracking combat activities
            
            **Custom Messages:**
            - Send any message to Discord channels
            - Choose between Shoutout (general) or BGS (faction-specific) channels
            - Your username will be included as the sender
            
            **Quick Actions:**
            - **Faction Conflicts:** Manually check all configured factions for conflicts
            - **Sync Commanders:** Update commander data from INARA
            - **All Top 5:** Send leaderboards for all categories at once
            
            **Time Periods:**
            - `ld` = Last Day (yesterday)
            - `lw` = Last Week (previous 7 days)
            - `cm` = Current Month
            - `lm` = Last Month
            - `2m` = Last 2 Months
            - `y` = Year to Date
            - `all` = All Time
            """)
        
        with st.expander("Troubleshooting"):
            st.markdown("""
            **Common Issues:**
            - **Faction name not recognized:** Make sure you use the exact faction name as it appears in Elite Dangerous
            - **No conflicts detected:** The faction might not be in any conflicts, or the name might be misspelled
            - **Webhook not working:** Check that the Discord webhook URL is properly configured in the server environment
            - **Discord message failed:** Check your internet connection and try again
            - **Empty summaries:** No data available for the selected time period
            """)
            
        with st.expander("Discord Channel Information"):
            st.markdown("""
            **Available Webhooks:**
            - **📢 Shoutout Channel:** General announcements, daily summaries, CZ reports
            - **🛡️ BGS Channel:** Faction conflicts, tick notifications, strategic updates
            
            **Message Types:**
            - Daily summaries are automatically formatted with leaderboards
            - CZ summaries include detailed statistics by system and commander
            - Custom messages appear with your username and timestamp
            - All messages respect Discord's formatting (Markdown support)
            """)
            
    except Exception as e:
        st.error(f"❌ Error loading faction data: {str(e)}")
        st.info("Please check your connection and try refreshing the page.")

if __name__ == "__main__":
    render()
