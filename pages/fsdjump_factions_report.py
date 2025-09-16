import streamlit as st
import pandas as pd
from api_client import get_json

from _global import STATE_COLORS

def color_state(val):
    color = STATE_COLORS.get(val, "#181c22")
    return f'background-color: {color}; color: #fff;' if val and val != "None" else ''

def color_states_cell(cell):
    # cell ist ein String mit evtl. mehreren States, getrennt durch Komma
    if not cell:
        return ""
    states = [s.strip() for s in cell.split(",") if s.strip()]
    if not states:
        return ""
    # Wenn mehrere States, nehme die Farbe des ersten, aber färbe alle gleich
    color = STATE_COLORS.get(states[0], "#181c22")
    return f'background-color: {color}; color: #fff;'

def fmt_pct(x: float) -> str:
    try:
        return f"{x:.2%}"
    except Exception:
        return ""

def render():
    st.title("📑 24h System Report - Minor Factions")
    st.text("Shows minor factions present in systems with FSD jumps in the last 24 hours.")

    # CSS für feste Spaltenbreiten und Influence rechtsbündig
    st.markdown("""
    <style>
    .stDataFrame thead tr th:nth-child(1),
    .stDataFrame tbody tr td:nth-child(1) { min-width: 200px; max-width: 200px; }
    .stDataFrame thead tr th:nth-child(2),
    .stDataFrame tbody tr td:nth-child(2) { min-width: 100px; max-width: 100px; }
    .stDataFrame thead tr th:nth-child(3),
    .stDataFrame tbody tr td:nth-child(3) { min-width: 120px; max-width: 120px; }
    .stDataFrame thead tr th:nth-child(4),
    .stDataFrame tbody tr td:nth-child(4) { min-width: 110px; max-width: 110px; text-align: center; }
    .stDataFrame thead tr th:nth-child(5),
    .stDataFrame tbody tr td:nth-child(5) { min-width: 90px; max-width: 90px; text-align: right !important; }
    .stDataFrame thead tr th:nth-child(6),
    .stDataFrame tbody tr td:nth-child(6) { min-width: 120px; max-width: 120px; }
    .stDataFrame thead tr th:nth-child(7),
    .stDataFrame tbody tr td:nth-child(7) { min-width: 120px; max-width: 120px; }
    </style>
    """, unsafe_allow_html=True)

    try:
        data = get_json("/fsdjump-factions")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    if not data or len(data) == 0:
        st.warning("No data found.")
        return

    # --- Filter-Auswahl vorbereiten ---
    # Alle Minor Factions, States, Pending, Recovering sammeln
    all_systems = sorted({entry.get("StarSystem", "Unknown") for entry in data})
    all_factions = set()
    all_states = set()
    all_pending = set()
    all_recovering = set()
    for entry in data:
        for f in entry.get("Factions", []):
            all_factions.add(f.get("Name", ""))
            state = f.get("FactionState", "")
            if state and state != "None":
                all_states.add(state)
            for ps in f.get("PendingStates", []):
                s = ps.get("State", "")
                if s:
                    all_pending.add(s)
            for rs in f.get("RecoveringStates", []):
                s = rs.get("State", "")
                if s:
                    all_recovering.add(s)
    all_factions = sorted([x for x in all_factions if x])
    all_states = sorted([x for x in all_states if x])
    all_pending = sorted([x for x in all_pending if x])
    all_recovering = sorted([x for x in all_recovering if x])

    # --- Filter-Widgets ---
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        selected_system = st.selectbox("System", ["All systems"] + all_systems)
    with col2:
        selected_faction = st.selectbox("Minor Faction", ["All factions"] + all_factions)
    with col3:
        selected_state = st.selectbox("State", ["All states"] + all_states)
    with col4:
        selected_pending = st.selectbox("Pending", ["All pending"] + all_pending)
    with col5:
        selected_recovering = st.selectbox("Recovering", ["All recovering"] + all_recovering)

    # --- Filter-Logik ---
    def system_matches(entry):
        # System-Filter
        if selected_system != "All systems" and entry.get("StarSystem", "") != selected_system:
            return False
        # Faction-Filter
        if selected_faction != "All factions":
            if not any(f.get("Name", "") == selected_faction for f in entry.get("Factions", [])):
                return False
        # State-Filter
        if selected_state != "All states":
            if not any(f.get("FactionState", "") == selected_state for f in entry.get("Factions", [])):
                return False
        # Pending-Filter
        if selected_pending != "All pending":
            found = False
            for f in entry.get("Factions", []):
                if any(ps.get("State", "") == selected_pending for ps in f.get("PendingStates", [])):
                    found = True
                    break
            if not found:
                return False
        # Recovering-Filter
        if selected_recovering != "All recovering":
            found = False
            for f in entry.get("Factions", []):
                if any(rs.get("State", "") == selected_recovering for rs in f.get("RecoveringStates", [])):
                    found = True
                    break
            if not found:
                return False
        return True

    filtered_data = [entry for entry in data if system_matches(entry)]

    if not filtered_data:
        st.info("No systems match the filter.")
        return

    for entry in filtered_data:
        sys_name = entry.get("StarSystem", "Unknown")
        sys_addr = entry.get("SystemAddress", "")
        timestamp = entry.get("Timestamp", "")
        factions = entry.get("Factions", [])

        st.subheader(f"{sys_name}")
        st.caption(f"SystemAddress: {sys_addr} | Timestamp: {timestamp}")

        if not factions:
            st.info("No minor factions found.")
            continue

        df = pd.DataFrame([
            {
                "Name": f.get("Name", ""),
                "Allegiance": f.get("Allegiance", ""),
                "Government": f.get("Government", ""),
                "State": "" if f.get("FactionState", "") == "None" else f.get("FactionState", ""),
                "Influence": f.get("Influence", 0.0),
                "Pending": ", ".join([ps.get("State", "") for ps in f.get("PendingStates", [])]),
                "Recovering": ", ".join([rs.get("State", "") for rs in f.get("RecoveringStates", [])])
            }
            for f in factions
        ])

        # Sort by Influence descending
        df = df.sort_values(by="Influence", ascending=False).reset_index(drop=True)
        df.index = df.index + 1  # Start numbering at 1
        df.index.name = "#"

        styled = (
            df.style
              .applymap(color_state, subset=["State"])
              .applymap(color_states_cell, subset=["Pending"])
              .applymap(color_states_cell, subset=["Recovering"])
              .format({"Influence": fmt_pct})
              .set_properties(subset=["Influence"], **{
                  "text-align": "right",
                  "min-width": "90px", "max-width": "90px"
              })
              .set_properties(subset=["Name"], **{
                  "min-width": "200px", "max-width": "200px"
              })
              .set_properties(subset=["Allegiance"], **{
                  "min-width": "100px", "max-width": "100px"
              })
              .set_properties(subset=["Government"], **{
                  "min-width": "120px", "max-width": "120px"
              })
              .set_properties(subset=["State"], **{
                  "text-align": "center",
                  "min-width": "110px", "max-width": "110px"
              })
              .set_properties(subset=["Pending"], **{
                  "min-width": "120px", "max-width": "120px"
              })
              .set_properties(subset=["Recovering"], **{
                  "min-width": "120px", "max-width": "120px"
              })
        )

        st.table(styled)
