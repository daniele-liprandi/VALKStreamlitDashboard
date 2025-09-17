
import streamlit as st
import pandas as pd
from datetime import datetime
from api_client import get_json
from auth import user_has_access
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def render():
    if not user_has_access(st.session_state.user, '2_Evaluations'):
        st.error('Unauthorized')
        st.stop()

    st.title("📈 Evaluations")

    mode = st.radio("Choose mode", ["Full", "Top 5"], horizontal=True)
    key_prefix = "top5/" if mode == "Top 5" else ""

    # Zeitraumfilter wie im Leaderboard
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
    selected_label = st.selectbox("Select Period:", list(period_labels.values()))
    selected_period = [k for k, v in period_labels.items() if v == selected_label][0]

    # Load Cmdr info
    cmdr_info = {}
    try:
        cmdrs_raw = get_json("table/cmdr")
        for row in cmdrs_raw:
            name = row.get("name")
            squadron_rank = row.get("squadron_rank", "")
            rank = row.get("rank_combat", "")
            if name:
                cmdr_info[name] = {
                    "squadron_rank": squadron_rank,
                    "rank": rank
                }
    except Exception as e:
        st.warning(f"⚠️ Cmdr info not loaded: {e}")

    endpoints = {
        "Market Events": "market-events",
        "Missions Completed": "missions-completed",
        "Missions Failed": "missions-failed",
        "Influence by Faction": "influence-by-faction",
        "Influence EIC": "influence-eic",
        "Bounty Vouchers": "bounty-vouchers",
        "Combat Bonds": "combat-bonds",
        "Exploration Sales": "exploration-sales",
        "Bounty Fines": "bounty-fines"
    }

    for label, path in endpoints.items():
        try:
            data = get_json(f"summary/{key_prefix}{path}?period={selected_period}")
            if not data:
                continue

            st.markdown(f"### 📊 {label}")
            df = pd.DataFrame(data)

            # Rename columns
            rename_map = {
                "cmdr": "Cmdr.",
                "missions_completed": "Missions completed",
                "missions_failed": "Missions failed",
                "faction_name": "Faction",
                "influence": "Influence",
                "total_buy": "Buy (Cr.)",
                "total_sell": "Sell (Cr.)",
                "total_transaction_volume": "Total Volume (Cr.)",
                "total_trade_quantity": "Total Quantity (tons)",
                "bounty_vouchers": "Bounty Vouchers (Cr.)",
                "combat_bonds": "Combat Bonds (Cr.)",
                "total_exploration_sales": "Exploration Sales (Cr.)",
                "bounty_fines": "Bounty Fines (Cr.)"
            }
            df.rename(columns=rename_map, inplace=True)

            # Add "No." as first column
            df.insert(0, "No.", range(1, len(df) + 1))

            # Insert Cmdr metadata
            if "Cmdr." in df.columns:
                cmdr_index = df.columns.get_loc("Cmdr.")
                df.insert(cmdr_index + 1, "Sq.-Rank",
                          df["Cmdr."].map(lambda x: cmdr_info.get(x, {}).get("squadron_rank", "")))

            # Convert numeric columns
            numeric_cols = [
                "Buy (Cr.)", "Sell (Cr.)",
                "Bounty Vouchers (Cr.)", "Combat Bonds (Cr.)", "Exploration Sales (Cr.)", "Bounty Fines (Cr.)"
            ]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Grid configuration
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_side_bar()
            gb.configure_selection("single")
            gb.configure_grid_options(
                suppressAutoSize=True,
                suppressColumnVirtualisation=True,
                suppressSizeToFit=True
            )

            # Fix column widths and pinning for first three columns
            for colname, width in [("No.", 70), ("Cmdr.", 150), ("Sq.-Rank", 140)]:
                if colname in df.columns:
                    gb.configure_column(
                        colname,
                        pinned="left",
                        resizable=False,
                        width=width,
                        minWidth=width,
                        maxWidth=width
                    )

            # Format all currency columns as Euro using Intl.NumberFormat
            for col in ["Buy (Cr.)", "Sell (Cr.)", "Bounty Vouchers (Cr.)", "Combat Bonds (Cr.)",
                        "Exploration Sales (Cr.)", "Bounty Fines (Cr.)"]:
                if col in df.columns:
                    gb.configure_column(
                        col,
                        type=["numericColumn", "rightAligned"],
                        valueFormatter="(value != null) ? value.toLocaleString('en-US') : ''"
                    )

            grid_options = gb.build()

            AgGrid(
                df,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.NO_UPDATE,
                enable_enterprise_modules=True,
                allow_unsafe_jscode=True,
                domLayout="normal",
                height=min(500, 70 + 35 * len(df))
            )

        except Exception as e:
            st.error(f"Error loading {label}: {e}")
