import streamlit as st
from datetime import datetime
import json
from api_client import get_json, post_json, delete_json  # delete_json importieren
from auth.auth import user_has_access
from urllib.parse import quote
from pages.system_info import (
    chip_css, chip, render_grouped_header, render_conflicts_table, render_minor_factions_table,
    fetch_system_activities, render_system_activities_table,
    fetch_faction_activities, render_faction_activities_table,
)



def _truncate(s: str, n: int = 80) -> str:
    if not s:
        return ""
    s = str(s).strip()
    return (s[:n] + "…") if len(s) > n else s


_TARGET_CLASS = {
    "visit": "info",
    "inf": "ok",
    "bv": "ok",
    "cb": "ok",
    "expl": "sky",
    "trade_prof": "sky",
    "bm_prof": "vio",
    "ground_cz": "warn",
    "space_cz": "warn",
    "murder": "red",
    "mission_fail": "red",
}


# Hilfsfunktionen für Chips
def _chip(label, value, klass="neut"):
    if value in (None, "", "-", "null"):
        return ""
    return chip(label, value, klass)


def _objective_chip_row(obj: dict) -> str:
    from datetime import datetime
    status = "Active"
    try:
        if obj.get("enddate") and obj["enddate"] < datetime.utcnow().isoformat():
            status = "Expired"
    except Exception:
        pass

    # Zeilenweise Chips aufbauen
    row1 = [
        _chip("Title", obj.get("title") or "—", "info"),
        _chip("Type", (obj.get("type") or "—").upper(), "ok"),
        _chip("Priority", obj.get("priority") or "0", "vio"),
        _chip("System", obj.get("system") or "—", "info"),
        _chip("Faction", obj.get("faction") or "—", "ok"),
    ]
    row2 = [
        _chip("Start", obj.get("startdate") or "—", "neut"),
        _chip("End", obj.get("enddate") or "—", "neut"),
        _chip("Status", status, "sky"),
    ]
    row3 = [
        _chip("Desc", _truncate(obj.get("description")), "neut"),
    ]

    html = [chip_css()]  # Styles einmalig einfügen
    html.append('<div class ="valk-title">Objective Info</div>')
    for row in [row1, row2, row3]:
        html.append(f'<div class="valk-badges">{"".join([c for c in row if c])}</div>')

    return "\n".join(html)


def _target_chip_row(obj: dict, t: dict) -> str:
    ttype = (t.get("type") or "-").strip().lower()
    klass = _TARGET_CLASS.get(ttype, "neut")
    system = t.get("system") or obj.get("system") or "—"
    station = t.get("station") or "—"
    faction = t.get("faction") or obj.get("faction") or "—"
    indiv = int((t.get("targetindividual") or 0) or 0)
    overall = int((t.get("targetoverall") or 0) or 0)
    prog = int((t.get("progress") or 0) or 0)

    chips = [
        _chip("Type", (ttype or "-").upper(), klass),
        _chip("System", system, "info"),
        _chip("Station", station, "neut") if station != "—" else "",
        _chip("Faction", faction, "ok") if faction != "—" else "",
        _chip("Target/CMDR", f"{indiv:,}".replace(",", "."), "sky"),
        _chip("Target Overall", f"{overall:,}".replace(",", "."), "sky"),
        _chip("Progress", f"{prog:,}%".replace(",", "."), "vio"),
        _chip("Target ID", t.get("id") or "—", "neut"),
    ]
    return chip_css() + f'<div class ="valk-title">Target Info</div><div class="valk-badges">{"".join([c for c in chips if c])}</div>'


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
            filter_faction = st.text_input("Filter by Faction", placeholder="e.g. East India Company")

        # Fetch objectives with filters
        params = {}
        if filter_system:
            params['system'] = filter_system
        if filter_faction:
            params['faction'] = filter_faction

        objectives_data = get_json('objectives', params=params)

        if objectives_data:

            # Haupt-Rendering-Schleife
            for obj_idx, obj in enumerate(objectives_data):
                # Oberer Expander je Objective (Titel enthält System & Index, damit eindeutig)
                header = f"🎯 {obj.get('title', 'Unnamed')} — {obj.get('system', 'n/a')} · #{obj_idx + 1}"
                with st.expander(header, expanded=False):
                    # Objective NUR als Chips
                    st.markdown(_objective_chip_row(obj), unsafe_allow_html=True)

                    # Targets
                    targets = obj.get("targets") or []
                    if targets:
                        #st.subheader("🎯 Targets")
                        for t_idx, t in enumerate(targets):
                            # Target-Expander (nur Chips im Kopf)
                            title = f"{(t.get('type') or 'TARGET').upper()} — {t.get('system') or obj.get('system') or 'n/a'} · #{t_idx + 1}"
                            with st.expander(title, expanded=False):
                                st.markdown(_target_chip_row(obj, t), unsafe_allow_html=True)

                                # Untergeordneter Expander: System-Infos (Header-Chips identisch zu system_info.py)
                                sys_name = (t.get("system") or obj.get("system") or "").strip()
                                if sys_name:
                                    sys_title = f"🪐 {sys_name} — System Info · target#{t_idx + 1}"
                                    with st.expander(sys_title, expanded=False):
                                        try:
                                            data = get_json(f"system-summary/{quote(sys_name, safe='')}")
                                            entry = data if isinstance(data, dict) else (
                                                data[0] if (isinstance(data, list) and data) else {})
                                            sysinfo = entry.get("system_info", {}) or {}
                                            pp_list = entry.get("powerplays") or []
                                            conflicts = entry.get("conflicts", []) or []
                                            pp0 = pp_list[0] if pp_list else {}

                                            # identische Kopf-Chips wie auf der Systemseite
                                            render_grouped_header(sysinfo, pp0, len(conflicts))

                                            # Buttons: eine Zeile, vier Aktionen
                                            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

                                            clicked = {
                                                "sys_ct": c1.button("System Activities (CT)",
                                                                    key=f"obj_sys_ct_{sys_name}_{t_idx}"),
                                                "sys_lt": c2.button("System Activities (LT)",
                                                                    key=f"obj_sys_lt_{sys_name}_{t_idx}"),
                                                "fac_ct": c3.button("Faction Activities (CT)",
                                                                    key=f"obj_fac_ct_{sys_name}_{t_idx}"),
                                                "fac_lt": c4.button("Faction Activities (LT)",
                                                                    key=f"obj_fac_lt_{sys_name}_{t_idx}"),
                                            }

                                            # System Activities
                                            if clicked["sys_ct"] or clicked["sys_lt"]:
                                                period = "ct" if clicked["sys_ct"] else "lt"
                                                rows = fetch_system_activities(sys_name, period)
                                                with st.expander(
                                                        f"🛰️ System Activities — {sys_name} [{period.upper()}]",
                                                        expanded=True):
                                                    render_system_activities_table(rows)

                                            # Faction Activities
                                            if clicked["fac_ct"] or clicked["fac_lt"]:
                                                period = "ct" if clicked["fac_ct"] else "lt"
                                                rows = fetch_faction_activities(sys_name, period)
                                                with st.expander(
                                                        f"🏳️ Faction Activities — {sys_name} [{period.upper()}]",
                                                        expanded=True):
                                                    render_faction_activities_table(rows)

                                            # Minor Factions
                                            with st.expander("👥 Minor Factions", expanded=False):
                                                factions = entry.get("factions") or []
                                                render_minor_factions_table(factions)

                                            # Conflicts
                                            with st.expander("⚔️ Conflicts", expanded=False):
                                                if conflicts:
                                                    render_conflicts_table(conflicts)
                                                else:
                                                    st.info("No conflicts in this system.")


                                        except Exception as e:
                                            st.error(f"Error loading system info for {sys_name}: {e}")
                                else:
                                    st.info("No system defined for this target.")
                    else:
                        st.info("No targets defined.")



        else:
            st.info("No objectives found with the current filters.")

    with tab2:
        st.header("➕ Create New BGS Objective")

        # Mission-Level Fields
        title = st.text_input("Title", placeholder="e.g. Go to War in Sol", key="title_input")
        priority = st.number_input("Priority", min_value=1, max_value=5, step=1, value=1, key="priority_input")
        type_ = st.selectbox("Mission Type", [
            "recon", "win_war", "draw_war", "win_election", "draw_election",
            "boost", "expand", "reduce", "retreat", "equalise"
        ], key="type_input")
        system = st.text_input("Target System", placeholder="e.g. Sol", key="system_input")
        faction = st.text_input("Primary Faction", placeholder="e.g. East India Company", key="faction_input")
        description = st.text_area("Description (optional)", key="desc_input")

        startdate = st.date_input("Start Date", value=datetime.today(), key="startdate_input")
        enddate = st.date_input("End Date", key="enddate_input")

        # Targets (multiple possible)
        st.subheader("🎯 Add Targets")
        num_targets = st.number_input("Number of Targets", min_value=1, max_value=5, value=1, key="num_targets_input")
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

        if st.button("🚀 Create Objective", type="primary"):
            try:
                response = post_json('objectives', objective)
                if response and response.get('id'):
                    st.success("✅ Objective created successfully!")
                    # Seite neu laden, damit Felder und Listen aktualisiert werden
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create objective: {response}")
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
                            response = delete_json(f"objectives/{objective_id}")
                            if response and response.get('success'):
                                st.success("✅ Objective deleted successfully!")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete objective: {response}")
                        except Exception as e:
                            st.error(f"❌ Error deleting objective: {str(e)}")
        else:
            st.info("No objectives available for deletion.")
