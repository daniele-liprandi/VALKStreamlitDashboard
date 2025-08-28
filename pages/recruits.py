import streamlit as st
import pandas as pd
import plotly.express as px
from api_client import get_json
from auth import user_has_access
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def render():
    if not user_has_access(st.session_state.user, '5_Recruits'):
        st.error('Unauthorized')
        st.stop()

    st.title("🆕 Recruits Overview")

    try:
        data = get_json("summary/recruits")
        if not data:
            st.warning("No Recruits-Data found.")
            return

        df = pd.DataFrame(data)
        df.fillna(0, inplace=True)



        rename_map = {
            "bounty_claims": "Bounty Claims (Cr.)",
            "bounty_fines": "Bounty Fines (Cr.)",
            "combat_bonds": "Combat Bonds (Cr.)",
            "commander": "Cmdr.",
            "days_since_join": "Days since join",
            "exp_value": "Exp. Value (Cr.)",
            "has_data": "Has Data",
            "last_active": "Last Active",
            "mission_count": "# of Missions",
            "tonnage": "Tonnage (t)"
        }
        df.rename(columns=rename_map, inplace=True)

        df.insert(0, "No.", range(1, len(df) + 1))

        ordered_cols = ["No.", "Cmdr.", "Has Data", "Last Active", "Days since join", "Tonnage (t)",
                        "# of Missions", "Bounty Claims (Cr.)", "Exp. Value (Cr.)", "Combat Bonds (Cr.)",
                        "Bounty Fines (Cr.)"]
        df = df[[col for col in ordered_cols if col in df.columns]]

        numeric_cols = [col for col in df.columns if col not in ["No.", "Cmdr.", "Has Data", "Last Active"]]

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(
            enableRowGroup=True,
            enablePivot=True,
            enableValue=True,
            filter=True,
            sortable=True,
            resizable=True
        )
        gb.configure_side_bar()
        gb.configure_selection("single")
        gb.configure_grid_options(groupDisplayType="multipleColumns", rowGroupPanelShow="always", sideBar=True)

        for colname, width in [("No.", 70), ("Cmdr.", 150)]:
            if colname in df.columns:
                gb.configure_column(colname, width=width, pinned="left", resizable=False, minWidth=width, maxWidth=width)

        for col in numeric_cols:
            if col in df.columns:
                gb.configure_column(
                    col,
                    type=["numericColumn", "rightAligned"],
                    valueFormatter="(value != null) ? value.toLocaleString('en-US') : ''",
                    width=120,
                    minWidth=120
                )

        grid_options = gb.build()

        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.NO_UPDATE,
            enable_enterprise_modules=True,
            allow_unsafe_jscode=True,
            domLayout="normal",
            height=min(500, 70 + 35 * len(df))
        )

    except Exception as e:
        st.error(f"Error loading Recruits: {e}")