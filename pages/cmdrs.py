import streamlit as st
import pandas as pd
from api_client import get_json
from auth import user_has_access
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def render():
    if not user_has_access(st.session_state.user, "3_Cmdrs"):
        st.error("Unauthorized")
        st.stop()

    st.title("🧑 Cmdr Overview")

    try:
        raw_data = get_json("table/cmdr")
        if not raw_data:
            st.warning("No Cmdr data found.")
            return

        df = pd.DataFrame(raw_data)

        # Format & rename columns
        df = pd.DataFrame({
            "Cmdr": df["name"],
            "Squadron": df["squadron_name"],
            "Sq.-Rank": df["squadron_rank"],
            "Comb.-Rank": df["rank_combat"],
            "Trade-Rank": df["rank_trade"],
            "Expl.-Rank": df["rank_explore"],
            "CQC-Rank": df["rank_cqc"],
            "Empire-Rank": df["rank_empire"],
            "Fed.-Rank": df["rank_federation"],
            "Power": df["rank_power"]
        })

        # Grid Options
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(filter=True, editable=False, groupable=True)
        gb.configure_grid_options(domLayout='normal')
        grid_options = gb.build()

        st.markdown("### 🔍 Cmdr Data Grid – Filter, Sort & Group")

        AgGrid(
            df,
            gridOptions=grid_options,
            height=600,
            theme="alpine",
            update_mode=GridUpdateMode.NO_UPDATE,
            enable_enterprise_modules=True
        )

    except Exception as e:
        st.error(f"Failed to load Cmdr data: {e}")
