import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from api_client import get_json
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def aggrid_fixed(df, height=300, key=None, col_widths=None, always_scroll=True):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=True, filter=True)
    # Feste Spaltenbreiten setzen
    if col_widths:
        for col, width in col_widths.items():
            gb.configure_column(col, width=width)
    grid_options = gb.build()
    # Höhe dynamisch nach Zeilenzahl anpassen (maximal 600px)
    if df is not None and not df.empty:
        # Für Cmdr Distribution: Zeilenhöhe dynamisch, aber Grid immer scrollbar
        if always_scroll:
            height = min(600, 40 + 35 * len(df))
            if height > 400:
                height = 400  # Zeige max. 400px, Rest per Scrollbar
        else:
            height = min(600, 40 + 35 * len(df))
    # Workaround: key immer eindeutig, abhängig von Tab, Periode, System und Grid-Typ
    return AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.NO_UPDATE,
        height=height,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=False,
        key=key
    )

def main():
    st.title("⚔️ CZ Summary")

    period_labels = {
        "ct": "Current Tick (since last BGS tick)",
        "cd": "Current Day (today)",
        "ld": "Last Day (yesterday)",
        "cw": "Current Week",
        "lw": "Last Week",
        "cm": "Current Month",
        "lm": "Last Month",
        "2m": "Last 2 Months",
        "y": "Current Year",
        "all": "Complete History"
    }

    def on_period_change():
        st.session_state['period_changed'] = True

    # Initialisierung für Session State
    if "selected_label" not in st.session_state:
        st.session_state["selected_label"] = list(period_labels.values())[0]
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = 0
    if "spacecz_system" not in st.session_state:
        st.session_state["spacecz_system"] = None
    if "groundcz_system" not in st.session_state:
        st.session_state["groundcz_system"] = None

    selected_label = st.selectbox(
        "Select Period:",
        list(period_labels.values()),
        index=list(period_labels.values()).index(st.session_state["selected_label"]),
        key="selected_label",
        on_change=on_period_change
    )
    selected_period = [k for k, v in period_labels.items() if v == selected_label][0]

    tab1, tab2 = st.tabs(["🚀 Space CZ", "🔫 Ground CZ"])

    # SPACE CZ TAB
    with tab1:
        st.subheader("🚀 Space CZ Summary")
        st.session_state["active_tab"] = 0
        params = {
            "period": selected_period
        }
        data = get_json(f"syntheticcz-summary?period={params['period']}")
        # Prüfe ob Liste oder Dict
        if not data or (isinstance(data, dict) and not data.get("summary")) or (isinstance(data, list) and not data):
            st.info("No Space CZ data found for selected filters.")
        else:
            # Falls Liste: aggregiere wie bei Ground CZ
            if isinstance(data, list):
                df = pd.DataFrame(data)
                if df.empty:
                    st.info("No Space CZ data found for selected filters.")
                else:
                    # System-Filter Dropdown
                    systems = sorted(df["starsystem"].unique())
                    # System-Filter: key abhängig von Periode und Tab
                    system_key = f"spacecz_system_{selected_period}"
                    if st.session_state.get(system_key) not in systems:
                        st.session_state[system_key] = systems[0]
                    selected_system = st.selectbox(
                        "Select Starsystem:",
                        systems,
                        key=system_key
                    )
                    filtered_df = df[df["starsystem"] == selected_system]
                    st.markdown(f"**{selected_system} - Space CZ Summary**")
                    cz_types = ["Low", "Medium", "High"]
                    cz_counts = {t: filtered_df[filtered_df["cz_type"].str.lower() == t.lower()]["cz_count"].sum() for t in cz_types}
                    total_cz = filtered_df["cz_count"].sum()
                    st.markdown(f"Total: {total_cz} CZs")
                    cz_df = pd.DataFrame([{"Type": t, "Count": cz_counts[t]} for t in cz_types])
                    aggrid_fixed(
                        cz_df,
                        height=150,
                        key=f"{selected_system}_{selected_period}_space_cz",
                        col_widths={"Type": 100, "Count": 80}
                    )

                    # Cmdr Distribution
                    cmdr_dist = []
                    for cmdr in filtered_df["cmdr"].unique():
                        row = {"Cmdr": cmdr}
                        for t in cz_types:
                            row[t] = filtered_df[(filtered_df["cmdr"] == cmdr) & (filtered_df["cz_type"].str.lower() == t.lower())]["cz_count"].sum()
                        row["Total"] = filtered_df[filtered_df["cmdr"] == cmdr]["cz_count"].sum()
                        cmdr_dist.append(row)
                    dist_df = pd.DataFrame(cmdr_dist)
                    dist_df = dist_df[["Cmdr"] + cz_types + ["Total"]]
                    st.markdown("Cmdr Distribution:")
                    aggrid_fixed(
                        dist_df,
                        height=min(400, 40 + 35 * len(dist_df)),
                        key=f"{selected_system}_{selected_period}_space_cmdr",
                        col_widths={"Cmdr": 180, "Low": 80, "Medium": 80, "High": 80, "Total": 80},
                        always_scroll=True
                    )
            else:
                summary = data.get("summary", {})
                cz_types = ["Low", "Medium", "High"]
                cz_counts = {t: summary.get(t.lower(), 0) for t in cz_types}
                total_cz = sum(cz_counts.values())
                st.markdown(f"**{summary.get('system', 'System')} - Space CZ Summary**")
                st.markdown(f"Total: {total_cz} CZs")
                cz_df = pd.DataFrame([{"Type": t, "Count": cz_counts[t]} for t in cz_types])
                aggrid_fixed(
                    cz_df,
                    height=150,
                    key=f"single_space_cz_{selected_period}",
                    col_widths={"Type": 100, "Count": 80}
                )
                dist = data.get("cmdr_distribution", [])
                if dist:
                    dist_df = pd.DataFrame(dist)
                    dist_df = dist_df.rename(columns={"low": "Low", "medium": "Medium", "high": "High", "total": "Total"})
                    dist_df = dist_df[["cmdr", "Low", "Medium", "High", "Total"]]
                    dist_df = dist_df.rename(columns={"cmdr": "Cmdr"})
                    st.markdown("Cmdr Distribution:")
                    aggrid_fixed(
                        dist_df,
                        height=min(400, 40 + 35 * len(dist_df)),
                        key=f"single_space_cmdr_{selected_period}",
                        col_widths={"Cmdr": 180, "Low": 80, "Medium": 80, "High": 80, "Total": 80},
                        always_scroll=True
                    )
                else:
                    st.info("No Cmdr distribution data available.")

    # GROUND CZ TAB
    with tab2:
        st.subheader("🔫 Ground CZ Summary")
        st.session_state["active_tab"] = 1
        params = {
            "period": selected_period
        }
        data = get_json(f"syntheticgroundcz-summary?period={params['period']}")
        if not data or (isinstance(data, list) and not data):
            st.info("No Ground CZ data found for selected filters.")
        else:
            if isinstance(data, list):
                df = pd.DataFrame(data)
                if df.empty:
                    st.info("No Ground CZ data found for selected filters.")
                else:
                    # System-Filter Dropdown
                    systems = sorted(df["starsystem"].unique())
                    system_key = f"groundcz_system_{selected_period}"
                    if st.session_state.get(system_key) not in systems:
                        st.session_state[system_key] = systems[0]
                    selected_system = st.selectbox(
                        "Select Starsystem:",
                        systems,
                        key=system_key
                    )
                    filtered_df = df[df["starsystem"] == selected_system]
                    st.markdown(f"**{selected_system} - Ground CZ Summary**")
                    cz_types = ["Low", "Medium", "High"]
                    cz_counts = {t: filtered_df[filtered_df["cz_type"].str.lower() == t.lower()]["cz_count"].sum() for t in cz_types}
                    total_cz = filtered_df["cz_count"].sum()
                    st.markdown(f"Total Ground CZs: {total_cz}")
                    cz_df = pd.DataFrame([{"Type": t, "Count": cz_counts[t]} for t in cz_types])
                    aggrid_fixed(
                        cz_df,
                        height=150,
                        key=f"{selected_system}_{selected_period}_ground_cz",
                        col_widths={"Type": 100, "Count": 80}
                    )

                    # Settlements
                    settlements = filtered_df.groupby("settlement")["cz_count"].sum().reset_index()
                    settlements = settlements.rename(columns={"cz_count": "CZs", "settlement": "Settlement"})
                    st.markdown("Settlements:")
                    aggrid_fixed(
                        settlements,
                        height=min(400, 40 + 35 * len(settlements)),
                        key=f"{selected_system}_{selected_period}_ground_settlements",
                        col_widths={"Settlement": 320, "CZs": 100}
                    )

                    # Cmdr Distribution
                    cmdr_dist = []
                    for cmdr in filtered_df["cmdr"].unique():
                        row = {"Cmdr": cmdr}
                        for t in cz_types:
                            row[t] = filtered_df[(filtered_df["cmdr"] == cmdr) & (filtered_df["cz_type"].str.lower() == t.lower())]["cz_count"].sum()
                        row["Total"] = filtered_df[filtered_df["cmdr"] == cmdr]["cz_count"].sum()
                        cmdr_dist.append(row)
                    dist_df = pd.DataFrame(cmdr_dist)
                    dist_df = dist_df[["Cmdr"] + cz_types + ["Total"]]
                    st.markdown("Cmdr Distribution:")
                    aggrid_fixed(
                        dist_df,
                        height=min(400, 40 + 35 * len(dist_df)),
                        key=f"{selected_system}_{selected_period}_ground_cmdr",
                        col_widths={"Cmdr": 200, "Low": 100, "Medium": 100, "High": 100, "Total": 100},
                        always_scroll=True
                    )
            else:
                summary = data.get("summary", {})
                cz_types = ["Low", "Medium", "High"]
                cz_counts = {t: summary.get(t.lower(), 0) for t in cz_types}
                total_cz = sum(cz_counts.values())
                st.markdown(f"**{summary.get('system', 'System')} - Ground CZ Summary**")
                st.markdown(f"Total Ground CZs: {total_cz}")
                cz_df = pd.DataFrame([{"Type": t, "Count": cz_counts[t]} for t in cz_types])
                aggrid_fixed(
                    cz_df,
                    height=150,
                    key=f"single_ground_cz_{selected_period}",
                    col_widths={"Type": 100, "Count": 80}
                )
                settlements = data.get("settlements", [])
                if settlements:
                    set_df = pd.DataFrame(settlements)
                    set_df = set_df.rename(columns={"settlement": "Settlement", "czs": "CZs"})
                    set_df = set_df[["Settlement", "CZs"]]
                    st.markdown("Settlements:")
                    aggrid_fixed(
                        set_df,
                        height=min(400, 40 + 35 * len(set_df)),
                        key=f"single_ground_settlements_{selected_period}",
                        col_widths={"Settlement": 320, "CZs": 100}
                    )
                else:
                    st.info("No settlement data available.")
                dist = data.get("cmdr_distribution", [])
                if dist:
                    dist_df = pd.DataFrame(dist)
                    dist_df = dist_df.rename(columns={"low": "Low", "medium": "Medium", "high": "High", "total": "Total"})
                    dist_df = dist_df[["cmdr", "Low", "Medium", "High", "Total"]]
                    dist_df = dist_df.rename(columns={"cmdr": "Cmdr"})
                    st.markdown("Cmdr Distribution:")
                    aggrid_fixed(
                        dist_df,
                        height=min(400, 40 + 35 * len(dist_df)),
                        key=f"single_ground_cmdr_{selected_period}",
                        col_widths={"Cmdr": 200, "Low": 100, "Medium": 100, "High": 100, "Total": 100},
                        always_scroll=True
                    )
                else:
                    st.info("No Cmdr distribution data available.")

if __name__ == "__main__":
    main()
