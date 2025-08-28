import streamlit as st
import pandas as pd
import json
import ast
from datetime import datetime, timedelta
from api_client import get_json
from auth import user_has_access

st.set_page_config(layout="wide")

def render():
    if not user_has_access(st.session_state.user, '1_TableView'):
        st.error('Unauthorized')
        st.stop()

    st.title('📊 BGS Table Viewer')

    tables = [
        "event",
        "market_buy_event",
        "market_sell_event",
        "mission_completed_event",
        "mission_completed_influence",
        "mission_failed_event",
        "faction_kill_bond_event",
        "redeem_voucher_event",
        "sell_exploration_data_event",
        "multi_sell_exploration_data_event",
        "activity",
        "system",
        "faction",
        "cmdr"
    ]

    selected_table = st.selectbox("Select Table", tables)
    if not selected_table:
        st.stop()

    # Daten laden
    data = get_json(f'table/{selected_table}')
    if not data:
        st.warning("No data returned.")
        st.stop()

    df = pd.DataFrame(data)

    # Filter nur bei bestimmten Tabellen
    filters = {}
    if selected_table == "event":
        with st.expander("🔎 Filter Options", expanded=True):
            col1, col2, col3 = st.columns(3)
            filters['cmdr'] = col1.selectbox("Cmdr", [""] + sorted(df['cmdr'].dropna().unique().tolist()))
            filters['event'] = col2.selectbox("Event", [""] + sorted(df['event'].dropna().unique().tolist()))
            filters['tickid'] = col3.selectbox("Tick ID", [""] + sorted(df['tickid'].dropna().unique().tolist(), reverse=True))
            col4, col5 = st.columns(2)
            today = datetime.today().date()
            from_date = col4.date_input("From Date", value=today)
            to_date = col5.date_input("To Date", value=today + timedelta(days=1))

            if filters['cmdr']:
                df = df[df['cmdr'] == filters['cmdr']]
            if filters['event']:
                df = df[df['event'] == filters['event']]
            if filters['tickid']:
                df = df[df['tickid'] == filters['tickid']]
            if from_date or to_date:
                ts = pd.to_datetime(df['timestamp'], errors='coerce')
                # Zeitzone angleichen: falls keine vorhanden, auf UTC setzen
                if ts.dt.tz is None:
                    ts = ts.dt.tz_localize('UTC')
                else:
                    ts = ts.dt.tz_convert('UTC')
                if from_date:
                    from_dt = pd.to_datetime(from_date).tz_localize('UTC')
                    df = df[ts >= from_dt]
                if to_date:
                    to_dt = pd.to_datetime(to_date).tz_localize('UTC')
                    df = df[ts <= to_dt]

    # Index zurücksetzen, damit Anzeige und Auswahl übereinstimmen
    df = df.reset_index(drop=True)

    st.markdown(f"### 📄 Showing {len(df)} rows from `{selected_table}`")
    st.dataframe(df, use_container_width=True)

    # JSON Anzeige unterhalb bei Auswahl eines Datensatzes aus event
    if selected_table == "event" and "raw_json" in df.columns and not df.empty:
        selected_index = st.number_input(
            "Selected row index for raw_json view:",
            min_value=0,
            max_value=len(df) - 1,
            value=0,
            step=1,
            key="json_index"
        )

        def show_json(row):
            try:
                parsed = json.loads(row)
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(row)  # Sicherer als eval()
                except Exception as e:
                    st.error(f"Failed to parse raw_json: {e}")
                    return
            st.subheader("🧾 raw_json Preview")
            st.json(parsed)

        show_json(df.iloc[selected_index]["raw_json"])
    elif selected_table == "event" and df.empty:
        st.info("No entries to show raw_json.")
