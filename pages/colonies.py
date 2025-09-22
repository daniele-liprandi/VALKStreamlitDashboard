""" 
The model is 
    id = db.Column(db.Integer, primary_key=True)
    cmdr = db.Column(db.String(64), nullable=True)
    starsystem = db.Column(db.String(128), nullable=True)
    systemaddress = db.Column(db.BigInteger, nullable=True)
    ravenurl = db.Column(db.String(256), nullable=True)

the API endpoints are:
GET /api/colonies - Lists all colonies
POST /api/colonies - Adds a new colony

This page is the streamlit frontend for it
 """

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from api_client import get_json, post_json
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def render():
    st.title("Colonies Management")

    st.header("Existing Colonies")
    colonies = get_json("colonies")
    if "error" in colonies:
        st.error(f"Error fetching colonies: {colonies['error']}")
    else:
        df = pd.DataFrame(colonies)
        if df.empty:
            st.info("No colonies found.")
        else:
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationAutoPageSize=True, paginationPageSize=10)
            gb.configure_default_column(editable=True, groupable=True)
            grid_options = gb.build()
            AgGrid(
                df,
                gridOptions=grid_options,
                enable_enterprise_modules=False,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                theme="dark",
                height=400,
                fit_columns_on_grid_load=True,
            )

    st.header("Add New Colony")
    with st.form("add_colony_form"):
        cmdr = st.text_input("Commander Name (cmdr)", max_chars=64)
        starsystem = st.text_input("Star System (starsystem)", max_chars=128, help="Required")
        systemaddress = st.number_input("System Address (systemaddress)", min_value=0, step=1, help="Required")
        ravenurl = st.text_input("Raven URL (ravenurl)", max_chars=256)

        submitted = st.form_submit_button("Add Colony")
        if submitted:
            if not starsystem or not systemaddress:
                st.error("starsystem and systemaddress are required fields.")
            else:
                payload = {
                    "cmdr": cmdr if cmdr else None,
                    "starsystem": starsystem,
                    "systemaddress": systemaddress, #TODO retrieve automatically
                    "ravenurl": ravenurl if ravenurl else None #TODO formulate automatically
                }
                response = post_json("colonies", payload=payload)
                if "error" in response:
                    st.error(f"Error adding colony: {response['error']}")
                else:
                    st.success(f"Colony added successfully with ID: {response.get('id')}")