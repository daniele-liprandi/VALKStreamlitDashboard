""" 
The model is 
    id = db.Column(db.Integer, primary_key=True)
    cmdr = db.Column(db.String(64), nullable=True)
    starsystem = db.Column(db.String(128), nullable=True)
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
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from urllib.parse import quote
from auth.auth import user_has_required_roles

def user_has_colonies_access(user):
    """
    Check if user has access to the editing of the colonies page.
    Requires admin, mods, or vet role.
    """
    required_roles = [
        "Administrator",  # admin
        "Moderator",  # mods  
        "Comrade [Veteran]", # vet
    ]
    
    return user_has_required_roles(user, required_roles)

def show_aggrid_table(df_show):
    """Show an AgGrid table where clicking a row opens the row's ravenurl in a new tab."""
    gb = GridOptionsBuilder.from_dataframe(df_show)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_side_bar()
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc="sum", editable=True)

    # JS handler: open the ravenurl field in a new tab when a row is clicked
    on_row_clicked = JsCode(
        """
        function(params) {
            try {
                const url = params.data && params.data.ravenurl;
                if (!url) { return; }
                // If URL doesn't start with http/https, prepend https://
                const finalUrl = /^https?:\/\//i.test(url) ? url : ('https://' + url);
                window.open(finalUrl, '_blank', 'noopener');
            } catch (e) {
                console.warn('Failed to open url from row click', e);
            }
        }
        """
    )

    gridOptions = gb.build()
    gridOptions['onRowClicked'] = on_row_clicked

    AgGrid(
        df_show,
        gridOptions=gridOptions,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="dark",
        height=400,
        fit_columns_on_grid_load=True,
    )

def render():
    st.title("Colonies Management")
    
    # Check if user can set priority (admin/mods/vet)
    can_set_prio = False
    if "user" in st.session_state and st.session_state.user:
        can_set_prio = user_has_colonies_access(st.session_state.user)

    st.header("Existing Colonies")
    colonies = get_json("colonies")
    if "error" in colonies:
        st.error(f"Error fetching colonies: {colonies['error']}")
    else:
        df = pd.DataFrame(colonies)
        if df.empty:
            st.info("No colonies found.")
        else:
            # Use shared helper which wires up row click behavior
            show_aggrid_table(df)
            
            # Admin section: Set priority for existing colonies
            if can_set_prio:
                st.markdown("---")
                st.subheader("🔧 Set Colonization Priority")
                st.info("Set priority levels for colonization goals. Higher priority colonies (1, 2, 3...) will appear on the home page. Set to 0 to remove from priority list.")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    # Create a list of system names for the dropdown
                    colony_options = {f"{c['starsystem']} (ID: {c['id']})": c['id'] for c in colonies}
                    selected_colony = st.selectbox(
                        "Select Colony",
                        options=list(colony_options.keys()),
                        help="Choose a colony to set its priority"
                    )
                
                with col2:
                    priority_value = st.number_input(
                        "Priority Level",
                        min_value=0,
                        max_value=10,
                        value=0,
                        help="0 = not priority, 1+ = priority level (higher = more important)"
                    )
                
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                    if st.button("Set Priority", type="primary", use_container_width=True):
                        colony_id = colony_options[selected_colony]
                        try:
                            response = post_json(
                                f"colonies/{colony_id}/priority",
                                payload={"priority": priority_value}
                            )
                            if isinstance(response, dict) and response.get("error"):
                                st.error(f"Error setting priority: {response['error']}")
                            else:
                                st.success(f"✅ Priority set to {priority_value} for {response.get('starsystem', 'colony')}")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error setting priority: {e}")

    st.header("Add New Colony")
    with st.form("add_colony_form"):
        # Pre-fill commander from session if available
        default_cmdr = None
        if "user" in st.session_state and st.session_state.user:
            # Streamlit session `user.username` is like 'Name#1234' in this app
            default_cmdr = st.session_state.user.get("username")

        cmdr = st.text_input("Commander Name (cmdr)", value=default_cmdr or "", max_chars=64)
        starsystem = st.text_input("Star System (starsystem)", max_chars=128, help="Required")


        submitted = st.form_submit_button("Add Colony")
        if submitted:
            if not starsystem:
                st.error("starsystem is a required field.")
            else:
                ravenurl = f"https://ravencolonial.com/#sys={quote(starsystem)}"
                payload = {
                    "cmdr": cmdr if cmdr else None,
                    "starsystem": starsystem,
                    "ravenurl": ravenurl
                }
                try:
                    response = post_json("colonies", payload=payload)
                    if isinstance(response, dict) and response.get("error"):
                        st.error(f"Error adding colony: {response['error']}")
                    else:
                        st.success(f"Colony added successfully with ID: {response.get('id')}\n URL: {ravenurl}")
                except Exception as e:
                    st.error(f"Error adding colony: {e}")