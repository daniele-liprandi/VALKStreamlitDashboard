import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from api_client import get_json
from auth import user_has_access
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import json

def format_conflict_status(conflict_status, conflict_details):
    """Format conflict status for display with appropriate emoji"""
    if not conflict_status:
        return "❓ No Data"
    
    if conflict_status == "peaceful":
        return "✅ Peaceful"
    elif conflict_status == "unknown":
        return "❓ Unknown"
    elif conflict_status in ["war", "civil_war", "election", "multiple"]:
        return f"⚔️ {conflict_details}" if conflict_details else f"⚔️ {conflict_status.replace('_', ' ').title()}"
    else:
        return "❓ Unknown"

def render():
    if not user_has_access(st.session_state.user, '3_Systems'):
        st.error('Unauthorized')
        st.stop()

    st.title("🌌 Systems Status")
    st.markdown("Monitor system states and current commander activities")

    # Load systems list
    try:
        systems_data = get_json("systems/list")
        systems_list = systems_data.get("systems", [])
        
        if not systems_list:
            st.warning("No systems found with recent activity or EDSM data")
            return
            
        # Create overview table
        st.subheader("📊 Systems Overview")
        
        systems_df = pd.DataFrame(systems_list)
        systems_df["System"] = systems_df["system_name"]
        systems_df["Controlling Faction"] = systems_df["controlling_faction"].fillna("Unknown")
        systems_df["Active CMDRs"] = systems_df["active_cmdrs"]
        systems_df["Has EDSM Data"] = systems_df["has_edsm_data"].map({True: "✅", False: "❌"})
        
        # Add conflict status from API response (now pre-calculated)
        systems_df["Conflict Status"] = systems_df.apply(
            lambda row: format_conflict_status(row.get("conflict_status"), row.get("conflict_details")), 
            axis=1
        )
        
        # Select columns for display
        display_df = systems_df[["System", "Controlling Faction", "Active CMDRs", "Has EDSM Data", "Conflict Status"]].copy()
        display_df.insert(0, "No.", range(1, len(display_df) + 1))
        
        # Configure grid for system selection
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_selection("single", use_checkbox=True)
        gb.configure_grid_options(suppressAutoSize=True)
        
        # Configure columns
        gb.configure_column("No.", width=60, pinned="left")
        gb.configure_column("System", width=150, pinned="left")
        gb.configure_column("Controlling Faction", width=200)
        gb.configure_column("Active CMDRs", width=120, type=["numericColumn"])
        gb.configure_column("Has EDSM Data", width=120)
        gb.configure_column("Conflict Status", width=150)
        
        grid_options = gb.build()
        
        systems_grid = AgGrid(
            display_df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            height=300,
            allow_unsafe_jscode=True
        )
        
        # Get selected system
        selected_rows = systems_grid.get("selected_rows", pd.DataFrame())
        
        if not selected_rows.empty:
            selected_system = selected_rows.iloc[0]["System"]
            
            st.markdown("---")
            st.subheader(f"🎯 System Details: **{selected_system}**")
            
            # Period selector
            col1, col2 = st.columns([1, 3])
            with col1:
                period_labels = {
                    "cd": "Current Day",
                    "ld": "Last Day (Yesterday)",
                }
                selected_label = st.selectbox("Activity Period:", list(period_labels.values()))
                selected_period = [k for k, v in period_labels.items() if v == selected_label][0]
            
            # Load system details
            try:
                system_status = get_json(f"systems/{selected_system}/status?period={selected_period}")
                
                if system_status:
                    render_system_details(system_status, selected_period)
                else:
                    st.error("Failed to load system details")
                    
            except Exception as e:
                st.error(f"Error loading system details: {e}")
        else:
            st.info("👆 Select a system from the table above to view detailed information")
            
    except Exception as e:
        st.error(f"Error loading systems: {e}")

def render_system_details(system_status, period):
    """Render detailed system information"""
    
    system_name = system_status.get("system_name")
    edsm_data = system_status.get("edsm_data", {})
    activity_data = system_status.get("activity_data", {})
    cmdr_summary = system_status.get("cmdr_summary", {})
    summary = system_status.get("summary", {})
    
    # System State from EDSM (Yesterday's tick)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📅 System State (Previous Tick)")
        
        if edsm_data and edsm_data.get("factions"):
            st.markdown(f"**Controlling Faction:** {edsm_data.get('controlling_faction', {}).get('name', 'Unknown')}")
            st.markdown(f"**Last EDSM Update:** {edsm_data.get('last_updated', 'Never')}")
            
            # Show faction states
            factions = edsm_data.get("factions", [])
            
            # Helper function to safely extract state names
            def get_state_names(faction):
                states = []
                
                # Process active_states (list of dicts)
                for state_obj in faction.get("active_states", []):
                    if isinstance(state_obj, dict):
                        state_name = state_obj.get("state", "")
                    else:
                        state_name = str(state_obj)
                    if state_name:
                        states.append(state_name)
                
                # Process main state
                main_state = faction.get("state", "")
                if isinstance(main_state, dict):
                    main_state = main_state.get("state", "") or main_state.get("name", "")
                elif main_state:
                    main_state = str(main_state)
                
                if main_state and main_state not in states:
                    states.append(main_state)
                
                return states
            
            # Find conflict factions
            conflict_factions = []
            for faction in factions:
                state_names = get_state_names(faction)
                if any(state.lower() in ["war", "civil war", "election"] for state in state_names):
                    conflict_factions.append(faction)
            
            if conflict_factions:
                st.markdown("#### ⚔️ **Factions in Conflict:**")
                for faction in conflict_factions:
                    influence = faction.get("influence", 0)
                    if influence:
                        influence_pct = f"{influence:.1%}"
                    else:
                        influence_pct = "Unknown"
                    
                    state_names = get_state_names(faction)
                    states_str = ', '.join(state_names) if state_names else "Unknown"
                    
                    st.markdown(f"- **{faction.get('name')}**: {influence_pct} - *{states_str}*")
            else:
                st.markdown("✅ **No active conflicts detected**")
            
            # Show top factions by influence
            st.markdown("#### 📊 **Top Factions by Influence:**")
            top_factions = sorted(factions, key=lambda x: x.get("influence", 0), reverse=True)[:5]
            
            for i, faction in enumerate(top_factions, 1):
                influence = faction.get("influence", 0)
                influence_pct = f"{influence:.1%}" if influence else "Unknown"
                
                # Safely get main state
                main_state = faction.get("state", "")
                if isinstance(main_state, dict):
                    state_display = main_state.get("state", "") or main_state.get("name", "Unknown")
                else:
                    state_display = str(main_state) if main_state else "None"
                
                st.markdown(f"{i}. **{faction.get('name')}**: {influence_pct} - *{state_display}*")
        else:
            st.warning("⚠️ No EDSM data available for this system")
    
    with col2:
        st.markdown(f"### 🚀 Current Activity ({period_labels.get(period, period)})")
        
        if summary.get("total_cmdrs", 0) > 0:
            # Activity summary
            st.markdown(f"**Active Commanders:** {summary.get('total_cmdrs', 0)}")
            st.markdown(f"**Total Credits Earned:** {summary.get('total_credits', 0):,} Cr")
            st.markdown(f"**Missions Completed:** {summary.get('total_missions', 0)}")
            st.markdown(f"**Combat Bonds:** {summary.get('total_combat_bonds', 0):,} Cr")
            st.markdown(f"**Bounty Vouchers:** {summary.get('total_bounty_vouchers', 0):,} Cr")
            st.markdown(f"**Exploration Sales:** {summary.get('total_exploration', 0):,} Cr")
            
            # Recent conflicts detected
            conflicts = activity_data.get("conflicts_detected", [])
            if conflicts:
                st.markdown("#### ⚔️ **Recent Conflict Updates:**")
                latest_conflict = conflicts[0]
                st.markdown(f"Last detected by **{latest_conflict.get('cmdr')}** at {latest_conflict.get('timestamp')}")
                
                for conflict in latest_conflict.get("conflicts", []):
                    faction1 = conflict.get("Faction1", {})
                    faction2 = conflict.get("Faction2", {})
                    war_type = conflict.get("WarType", "Unknown")
                    
                    st.markdown(f"- **{war_type}**: {faction1.get('Name')} vs {faction2.get('Name')}")
                    st.markdown(f"  Won Days: {faction1.get('WonDays', 0)} - {faction2.get('WonDays', 0)}")
            
        else:
            st.info("ℹ️ No recent activity detected in this system")
    
    # Commander Activity Details
    if cmdr_summary:
        st.markdown("---")
        st.markdown("### 👥 Commander Activity Details")
        
        # Create commander activity dataframe
        cmdr_rows = []
        for cmdr, data in cmdr_summary.items():
            cmdr_rows.append({
                "Commander": cmdr,
                "Missions": data.get("missions_completed", 0),
                "Combat Bonds": f"{data.get('combat_bonds', 0):,} Cr",
                "Bounty Vouchers": f"{data.get('bounty_vouchers', 0):,} Cr", 
                "Exploration": f"{data.get('exploration_earnings', 0):,} Cr",
                "Market Trans.": data.get("market_transactions", 0),
                "Total Credits": f"{data.get('total_credits', 0):,} Cr"
            })
        
        if cmdr_rows:
            cmdr_df = pd.DataFrame(cmdr_rows)
            cmdr_df.insert(0, "No.", range(1, len(cmdr_df) + 1))
            
            # Sort by total credits
            cmdr_df["Credits_Numeric"] = [int(row["Total Credits"].replace(" Cr", "").replace(",", "")) for _, row in cmdr_df.iterrows()]
            cmdr_df = cmdr_df.sort_values("Credits_Numeric", ascending=False).drop("Credits_Numeric", axis=1).reset_index(drop=True)
            cmdr_df["No."] = range(1, len(cmdr_df) + 1)
            
            # Configure grid
            gb = GridOptionsBuilder.from_dataframe(cmdr_df)
            gb.configure_grid_options(suppressAutoSize=True)
            
            # Configure columns
            gb.configure_column("No.", width=60, pinned="left")
            gb.configure_column("Commander", width=150, pinned="left")
            gb.configure_column("Missions", width=80, type=["numericColumn"])
            gb.configure_column("Market Trans.", width=100, type=["numericColumn"])
            
            for col in ["Combat Bonds", "Bounty Vouchers", "Exploration", "Total Credits"]:
                gb.configure_column(col, width=120, type=["rightAligned"])
            
            grid_options = gb.build()
            
            AgGrid(
                cmdr_df,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.NO_UPDATE,
                height=min(400, 70 + 35 * len(cmdr_df)),
                allow_unsafe_jscode=True
            )
    
    # Detailed Activity Logs
    if any(activity_data.values()):
        st.markdown("---")
        st.markdown("### 📝 Detailed Activity Logs")
        
        tab1, tab2, tab3, tab4 = st.tabs(["🎯 Missions", "⚔️ Combat", "💰 Bounties", "🔍 Exploration"])
        
        with tab1:
            missions = activity_data.get("missions_completed", [])
            if missions:
                missions_df = pd.DataFrame(missions)
                missions_df = missions_df.rename(columns={
                    "cmdr": "Commander",
                    "awarding_faction": "Faction", 
                    "mission_name": "Mission",
                    "reward": "Reward",
                    "timestamp": "Time"
                })
                missions_df["Reward"] = missions_df["Reward"].apply(lambda x: f"{x:,} Cr" if pd.notnull(x) else "0 Cr")
                st.dataframe(missions_df, use_container_width=True)
            else:
                st.info("No missions completed in this period")
        
        with tab2:
            bonds = activity_data.get("combat_bonds", [])
            if bonds:
                bonds_df = pd.DataFrame(bonds)
                bonds_df = bonds_df.rename(columns={
                    "cmdr": "Commander",
                    "awarding_faction": "For Faction",
                    "victim_faction": "Against Faction", 
                    "reward": "Bond Value",
                    "timestamp": "Time"
                })
                bonds_df["Bond Value"] = bonds_df["Bond Value"].apply(lambda x: f"{x:,} Cr" if pd.notnull(x) else "0 Cr")
                st.dataframe(bonds_df, use_container_width=True)
            else:
                st.info("No combat bonds redeemed in this period")
        
        with tab3:
            vouchers = activity_data.get("bounty_vouchers", [])
            if vouchers:
                vouchers_df = pd.DataFrame(vouchers)
                vouchers_df = vouchers_df.rename(columns={
                    "cmdr": "Commander",
                    "faction": "Faction",
                    "amount": "Amount",
                    "timestamp": "Time"
                })
                vouchers_df["Amount"] = vouchers_df["Amount"].apply(lambda x: f"{x:,} Cr" if pd.notnull(x) else "0 Cr")
                st.dataframe(vouchers_df, use_container_width=True)
            else:
                st.info("No bounty vouchers redeemed in this period")
        
        with tab4:
            exploration = activity_data.get("exploration_sales", [])
            if exploration:
                exploration_df = pd.DataFrame(exploration)
                exploration_df = exploration_df.rename(columns={
                    "cmdr": "Commander",
                    "earnings": "Earnings",
                    "timestamp": "Time"
                })
                exploration_df["Earnings"] = exploration_df["Earnings"].apply(lambda x: f"{x:,} Cr" if pd.notnull(x) else "0 Cr")
                st.dataframe(exploration_df, use_container_width=True)
            else:
                st.info("No exploration data sold in this period")

# Helper for period labels
period_labels = {
    "cd": "Current Day",
    "ld": "Last Day (Yesterday)",
}
