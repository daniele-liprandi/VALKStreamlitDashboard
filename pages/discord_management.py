import streamlit as st
import pandas as pd
from datetime import datetime
import api_client
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

def render():
    st.title("Discord Management")
    
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
        st.info("ℹ️ New factions can be configured with custom webhooks and can be deleted later.")
        
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
            
            # Webhook configuration
            st.markdown("**🔗 Webhook Configuration**")
            webhook_option = st.selectbox(
                "Webhook Type",
                options=["default", "custom"],
                format_func=lambda x: "🛡️ Use Default BGS Webhook" if x == "default" else "🔧 Custom Webhook URL",
                help="Choose whether to use the default webhook or provide a custom one"
            )
            
            new_faction_webhook = None
            if webhook_option == "custom":
                new_faction_webhook = st.text_input(
                    "Custom Webhook URL",
                    placeholder="https://discord.com/api/webhooks/...",
                    help="Discord webhook URL for this faction's notifications"
                )
            
            submit_add = st.form_submit_button("Add Faction", type="primary")
            
            if submit_add:
                if new_faction_name.strip():
                    try:
                        result = api_client.add_faction(
                            new_faction_name.strip(),
                            new_faction_description.strip(),
                            new_faction_webhook.strip() if new_faction_webhook else None
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

        # Convert factions to DataFrame for table display
        faction_data = []
        for faction_name, config in factions.items():
            webhook_url = config.get("webhook_url", "")
            if webhook_url:
                # Show abbreviated webhook URL for custom webhooks
                if "discord.com" in webhook_url:
                    webhook_display = f"🔧 Custom ({webhook_url[-10:]}...)"
                else:
                    webhook_display = f"🔧 Custom"
            else:
                webhook_display = "🛡️ Default BGS"
            
            faction_data.append({
                "Faction Name": faction_name,
                "Description": config.get("description", "No description"),
                "Webhook": webhook_display,
                "Protected": "🔒 Yes" if config.get("protected", False) else "❌ No",
                "Status": "🛡️ Protected" if config.get("protected", False) else "⚙️ Custom"
            })
        
        df_factions = pd.DataFrame(faction_data)
        
        if not df_factions.empty:
            # Configure the AgGrid table
            gb = GridOptionsBuilder.from_dataframe(df_factions)
            gb.configure_default_column(
                filter=True,
                sortable=True,
                resizable=True
            )
            gb.configure_selection("single", use_checkbox=False)
            gb.configure_column("Faction Name", width=200, pinned="left")
            gb.configure_column("Description", width=250)
            gb.configure_column("Webhook", width=150)
            gb.configure_column("Protected", width=100)
            gb.configure_column("Status", width=120)
            
            grid_options = gb.build()
            
            grid_response = AgGrid(
                df_factions,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                allow_unsafe_jscode=True,
                height=min(400, 50 + 35 * len(df_factions))
            )
            
            # Handle faction actions for selected row
            selected_rows = grid_response.get("selected_rows", [])
            if selected_rows is not None and len(selected_rows) > 0:
                # Convert to list if it's a DataFrame
                if hasattr(selected_rows, 'to_dict'):
                    selected_faction = selected_rows.iloc[0].to_dict()
                elif isinstance(selected_rows, list):
                    selected_faction = selected_rows[0]
                else:
                    selected_faction = selected_rows
                
                faction_name = selected_faction["Faction Name"]
                is_protected = "🔒 Yes" in selected_faction["Protected"]
                
                st.subheader(f"🔧 Actions for: {faction_name}")
                
                if is_protected:
                    st.warning("🔒 This is a protected faction and cannot be modified or deleted.")
                else:
                    # Update faction configuration
                    st.markdown("**🔧 Update Faction Configuration**")
                    
                    # Get current faction config for defaults
                    current_config = factions.get(faction_name, {})
                    current_webhook = current_config.get("webhook_url", "")
                    
                    with st.form(f"update_faction_{faction_name}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_desc = st.text_input(
                                "Description",
                                value=selected_faction["Description"],
                                key=f"update_desc_{faction_name}"
                            )
                        
                        with col2:
                            webhook_update_option = st.selectbox(
                                "Webhook Type",
                                options=["keep", "default", "custom"],
                                format_func=lambda x: {
                                    "keep": "� Keep Current",
                                    "default": "🛡️ Use Default BGS", 
                                    "custom": "🔧 Custom Webhook"
                                }[x],
                                key=f"webhook_option_{faction_name}"
                            )
                            
                            new_webhook = None
                            if webhook_update_option == "custom":
                                new_webhook = st.text_input(
                                    "Custom Webhook URL",
                                    value=current_webhook,
                                    placeholder="https://discord.com/api/webhooks/...",
                                    key=f"update_webhook_{faction_name}"
                                )
                            elif webhook_update_option == "default":
                                new_webhook = ""  # Empty string for default
                        
                        col_update, col_delete = st.columns(2)
                        
                        with col_update:
                            if st.form_submit_button("💾 Update Faction", type="primary"):
                                try:
                                    update_args = {"description": new_desc}
                                    if webhook_update_option != "keep":
                                        update_args["webhook_url"] = new_webhook
                                    
                                    api_client.update_faction(faction_name, **update_args)
                                    st.success("✅ Faction updated successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error updating faction: {str(e)}")
                        
                        with col_delete:
                            if st.form_submit_button(f"🗑️ Delete", type="secondary"):
                                try:
                                    api_client.delete_faction(faction_name)
                                    st.success(f"✅ Faction '{faction_name}' deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error deleting faction: {str(e)}")
        else:
            st.info("No factions configured. Add one above to get started!")
        
        # Discord Controls Section
        st.divider()
        st.subheader("📢 Discord Controls")
        
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
                options=["cd", "ld", "lw", "cm", "lm", "2m", "y", "all"],
                format_func=lambda x: {
                    "cd": "Current Day",
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
                options=["cd", "ld", "lw", "cm", "lm", "2m", "y", "all"],
                format_func=lambda x: {
                    "cd": "Current Day",
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
                            "message": custom_message.strip(),
                            "webhook_type": webhook_choice,
                            "username": username
                        })
                        st.success(f"✅ Message sent to {webhook_choice} channel!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
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
        
        # Help section as expandable cards
        st.subheader("ℹ️ Help & Documentation")
        
        # Create tabs for different help sections
        help_tab1, help_tab2, help_tab3, help_tab4 = st.tabs([
            "🏛️ Faction Management", "📢 Discord Controls", "⚡ Quick Actions", "🔧 Troubleshooting"
        ])
        
        with help_tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🛡️ Protected Factions:**")
                st.markdown("""
                - Hardcoded in tenant configuration
                - Cannot be modified or deleted
                - Use configured BGS webhook
                - Example: `Communism Interstellar`, `People's Party of Heverty`
                """)
                
            with col2:
                st.markdown("**⚙️ Custom Factions:**")
                st.markdown("""
                - Added through dashboard
                - Can be modified and deleted
                - Use default BGS webhook
                - Take effect immediately for monitoring
                """)
            
            st.markdown("**📊 Faction Table Features:**")
            st.markdown("""
            - **Filter:** Use column headers to filter by any field
            - **Sort:** Click column headers to sort
            - **Select:** Click on any row to perform actions
            - **Resize:** Drag column borders to adjust width
            """)
        
        with help_tab2:
            # Create a summary table of Discord controls
            discord_data = [
                {"Control", "Description", "Channel", "Period Options"},
                {"📈 Daily Summary", "Yesterday's activity report", "Shoutout", "Fixed (yesterday)"},
                {"🚀 Space CZ", "Space conflict zone stats", "BGS", "Configurable"},
                {"🔫 Ground CZ", "Ground conflict zone stats", "BGS", "Configurable"},
                {"💬 Custom Message", "Send any message", "Selectable", "N/A"}
            ]
            
            discord_df = pd.DataFrame(discord_data[1:], columns=discord_data[0])
            st.dataframe(discord_df, use_container_width=True, hide_index=True)
            
            st.markdown("**Period Options:**")
            period_data = [
                {"Code", "Description"},
                {"ld", "Last Day (yesterday)"},
                {"lw", "Last Week (7 days)"},
                {"cm", "Current Month"},
                {"lm", "Last Month"},
                {"2m", "Last 2 Months"},
                {"y", "Year to Date"},
                {"all", "All Time"}
            ]
            
            period_df = pd.DataFrame(period_data[1:], columns=period_data[0])
            st.dataframe(period_df, use_container_width=True, hide_index=True)
        
        with help_tab3:
            # Quick actions table
            actions_data = [
                {"Action", "Description", "Effect"},
                {"🔄 Faction Conflicts", "Check all factions for conflicts", "Immediate Discord notifications"},
                {"👥 Sync Commanders", "Update commander data from INARA", "Refresh squadron ranks"},
                {"📊 All Top 5", "Send leaderboards for all categories", "Multiple Discord messages"}
            ]
            
            actions_df = pd.DataFrame(actions_data[1:], columns=actions_data[0])
            st.dataframe(actions_df, use_container_width=True, hide_index=True)
        
        with help_tab4:
            st.markdown("**Common Issues & Solutions:**")
            
            issues_data = [
                {"Issue", "Possible Cause", "Solution"},
                {"Faction not recognized", "Incorrect name", "Use exact Elite Dangerous faction name"},
                {"No conflicts detected", "No active conflicts", "Check spelling or wait for conflicts"},
                {"Webhook failed", "Invalid webhook URL", "Check server webhook configuration"},
                {"Discord message failed", "Network issue", "Check connection and retry"},
                {"Empty summaries", "No data for period", "Select different time period"}
            ]
            
            issues_df = pd.DataFrame(issues_data[1:], columns=issues_data[0])
            st.dataframe(issues_df, use_container_width=True, hide_index=True)
            
            st.markdown("**Discord Webhook Channels:**")
            webhook_data = [
                {"Channel", "Purpose", "Message Types"},
                {"📢 Shoutout", "General announcements", "Daily summaries, CZ reports, custom messages"},
                {"🛡️ BGS", "Faction operations", "Conflict notifications, tick alerts, strategic updates"}
            ]
            
            webhook_df = pd.DataFrame(webhook_data[1:], columns=webhook_data[0])
            st.dataframe(webhook_df, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"❌ Error loading faction data: {str(e)}")
        st.info("Please check your connection and try refreshing the page.")

if __name__ == "__main__":
    render()