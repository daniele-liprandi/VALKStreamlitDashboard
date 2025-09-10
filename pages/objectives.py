import streamlit as st
from datetime import datetime
import json
import requests
from api_client import get_json, API_BASE, API_KEY, API_VERSION
from auth import user_has_access

def render():
    if not user_has_access(st.session_state.user, '5_Objectives'):
        st.error('Unauthorized')
        st.stop()

    st.set_page_config(page_title="🎯 Objectives Management")
    st.title("🎯 BGS Objectives Management")

    # Tabs für verschiedene Funktionen
    tab1, tab2, tab3 = st.tabs(["📋 Active Objectives", "➕ Create New", "🗑️ Delete Objective"])

    with tab1:
        st.header("📋 Active Objectives")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            filter_system = st.text_input("Filter by System", placeholder="e.g. Kachian")
        with col2:
            filter_faction = st.text_input("Filter by Faction", placeholder="e.g. Communism Interstellar")

        # Fetch objectives with filters
        params = {}
        if filter_system:
            params['system'] = filter_system
        if filter_faction:
            params['faction'] = filter_faction

        objectives_data = get_json('objectives', params=params)

        if objectives_data:
            for obj in objectives_data:
                with st.expander(f"🎯 {obj.get('title', 'Unnamed')} (Priority: {obj.get('priority', 'N/A')})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Type:** {obj.get('type', 'N/A')}")
                        st.write(f"**System:** {obj.get('system', 'N/A')}")
                        st.write(f"**Faction:** {obj.get('faction', 'N/A')}")
                    with col2:
                        st.write(f"**Start Date:** {obj.get('startdate', 'N/A')}")
                        st.write(f"**End Date:** {obj.get('enddate', 'N/A')}")
                        st.write(f"**Status:** {'Active' if obj.get('enddate') > datetime.now().isoformat() else 'Expired'}")

                    if obj.get('description'):
                        st.write(f"**Description:** {obj['description']}")

                    if obj.get('targets'):
                        st.write("**Targets:**")
                        for i, target in enumerate(obj['targets']):
                            st.write(f"  • Target {i+1}: {target.get('type', 'N/A')} "
                                   f"(Individual: {target.get('targetindividual', 0)}, "
                                   f"Overall: {target.get('targetoverall', 0)})")
        else:
            st.info("No objectives found with the current filters.")

    with tab2:
        st.header("➕ Create New BGS Objective")

        # Mission-Level Fields
        title = st.text_input("Title", placeholder="e.g. Go to War in Sol")
        priority = st.number_input("Priority", min_value=1, max_value=5, step=1, value=1)
        type_ = st.selectbox("Mission Type", [
            "recon", "win_war", "draw_war", "win_election", "draw_election",
            "boost", "expand", "reduce", "retreat", "equalise"
        ])
        system = st.text_input("Target System", placeholder="e.g. Sol")
        faction = st.text_input("Primary Faction", placeholder="e.g. Communism Interstellar")
        description = st.text_area("Description (optional)")

        startdate = st.date_input("Start Date", value=datetime.today())
        enddate = st.date_input("End Date")

        # Targets (multiple possible)
        st.subheader("🎯 Add Targets")
        num_targets = st.number_input("Number of Targets", min_value=1, max_value=5, value=1)
        targets = []

        for i in range(num_targets):
            st.markdown(f"---\n**🎯 Target {i + 1}**")
            target_type = st.selectbox(f"Target Type {i+1}", [
                "visit", "inf", "bv", "cb", "expl", "trade_prof", "bm_prof",
                "ground_cz", "space_cz", "murder", "mission_fail"
            ], key=f"type_{i}")

            station = system_override = faction_override = None
            if target_type == "visit":
                station = st.text_input(f"Station (optional)", key=f"station_{i}")
            if st.checkbox(f"Override system for Target {i+1}", key=f"sys_check_{i}"):
                system_override = st.text_input("Target System (Override)", key=f"system_{i}")
            if st.checkbox(f"Override faction for Target {i+1}", key=f"fac_check_{i}"):
                faction_override = st.text_input("Target Faction (Override)", key=f"faction_{i}")

            target_individual = st.number_input("Target Value per CMDR", min_value=0, key=f"indiv_{i}")
            target_overall = st.number_input("Overall Target Value", min_value=0, key=f"overall_{i}")

            settlements = []
            if target_type == "ground_cz":
                st.markdown("🏘️ Target Settlements:")
                num_settlements = st.number_input("Number of Settlements", min_value=0, max_value=5, value=0, key=f"settlement_count_{i}")
                for j in range(num_settlements):
                    name = st.text_input(f"Settlement {j+1} – Name", key=f"settlement_name_{i}_{j}")
                    t_indiv = st.number_input(f"Settlement {j+1} – Target per CMDR", min_value=0, key=f"settlement_indiv_{i}_{j}")
                    t_overall = st.number_input(f"Settlement {j+1} – Overall Target", min_value=0, key=f"settlement_overall_{i}_{j}")
                    settlements.append({
                        "name": name,
                        "targetindividual": t_indiv,
                        "targetoverall": t_overall
                    })

            target = {
                "type": target_type,
                "targetindividual": int(target_individual),
                "targetoverall": int(target_overall)
            }
            if station:
                target["station"] = station
            if system_override:
                target["system"] = system_override
            if faction_override:
                target["faction"] = faction_override
            if settlements:
                target["settlements"] = settlements

            targets.append(target)

        # Prepare final object
        objective = {
            "title": title,
            "priority": priority,
            "type": type_,
            "system": system,
            "faction": faction,
            "startdate": startdate.isoformat(),
            "enddate": enddate.isoformat(),
            "description": description,
            "targets": targets
        }

        st.subheader("🧾 JSON Preview")
        st.json(objective)

        if st.button("🚀 Create Objective", type="primary"):
            try:
                response = requests.post(
                    f"{API_BASE}/objectives",
                    json=objective,
                    headers={
                        'apikey': API_KEY,
                        'apiversion': API_VERSION,
                        'Content-Type': 'application/json'
                    }
                )
                if response.status_code == 201:
                    st.success("✅ Objective created successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create objective: {response.text}")
            except Exception as e:
                st.error(f"❌ Error creating objective: {str(e)}")

    with tab3:
        st.header("🗑️ Delete Objective")
        st.warning("⚠️ This action cannot be undone!")

        # Fetch all objectives for deletion
        all_objectives = get_json('objectives')

        if all_objectives:
            objective_options = {}
            for obj in all_objectives:
                key = f"{obj.get('id', 'Unknown')} - {obj.get('title', 'Unnamed')} ({obj.get('system', 'N/A')})"
                objective_options[key] = obj.get('id')

            selected_objective = st.selectbox(
                "Select Objective to Delete",
                options=list(objective_options.keys()),
                index=0 if objective_options else None
            )

            if selected_objective:
                objective_id = objective_options[selected_objective]

                # Show details of selected objective
                selected_obj = next((obj for obj in all_objectives if obj.get('id') == objective_id), None)
                if selected_obj:
                    st.write("**Objective Details:**")
                    st.json(selected_obj)

                col1, col2 = st.columns(2)
                with col1:
                    confirm_delete = st.checkbox("I confirm I want to delete this objective")
                with col2:
                    if st.button("🗑️ Delete Objective", type="secondary", disabled=not confirm_delete):
                        try:
                            response = requests.delete(
                                f"{API_BASE}/objectives/{objective_id}",
                                headers={
                                    'apikey': API_KEY,
                                    'apiversion': API_VERSION
                                }
                            )
                            if response.status_code == 200:
                                st.success("✅ Objective deleted successfully!")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete objective: {response.text}")
                        except Exception as e:
                            st.error(f"❌ Error deleting objective: {str(e)}")
        else:
            st.info("No objectives available for deletion.")
