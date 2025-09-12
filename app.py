import streamlit as st
from auth import verify_user

st.set_page_config(page_title="VALK Dashboard", layout="wide")

# Verbesserter CSS-Block: Menüeinträge hell, Login-Status gelb
st.markdown("""
    <style>
        body {
            background-color: #0e1117;
            color: #ffffff;
        }
        .block-container {
            padding-top: 2rem;
        }
        [data-testid="stSidebar"] {
            background-color: #1e1e1e;
        }

        /* Seiten-Navigation (oben links) ausblenden */
        [data-testid="stSidebarNav"] {
            display: none;
        }

        /* Menüeinträge: Textfarbe weiß/gold */
        section[data-testid="stSidebar"] * {
            color: #FFD700 !important;
        }

        /* Login-Status lesbar und gelb */
        .stAlert {
            background-color: #1e1e1e;
            color: #FFD700;
            border: 1px solid #FFD700;
        }

        /* Trennlinie unter Logo */
        .sidebar-logo-separator {
            border-top: 1px solid #444;
            margin: 0.5rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# Login-Ansicht
if "user" not in st.session_state:
    with st.sidebar:
        st.image("assets/VALT_logo.jpg", width=210)
        st.markdown('<div class="sidebar-logo-separator"></div>', unsafe_allow_html=True)
    with st.form("login_form"):
        st.title("Login")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        api_key = st.text_input("API-Key", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            result = verify_user(user, pw, api_key)
            if result:
                st.session_state.user = result
                st.session_state.api_key = api_key
                st.session_state.tenant_name = result.get("tenant_name", "")
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()

# Sidebar mit Logo und Menü
with st.sidebar:
    st.image("assets/VALT_logo.jpg", width=210)
    st.markdown('<div class="sidebar-logo-separator"></div>', unsafe_allow_html=True)
    # Benutzername und Tenant anzeigen
    username = st.session_state.user.get('username', 'Unbekannt')
    tenant = st.session_state.user.get('tenant_name', 'Kein Tenant')
    st.success(f"User: {username}")
    st.success(f"Tenant: {tenant}")
    # Logout-Button
    if st.button("Logout"):
        st.session_state.pop("user", None)
        st.session_state.pop("api_key", None)
        st.session_state.pop("tenant_name", None)
        st.rerun()
    page = st.radio(
        "📂 Menu",
        [
            "📊 Table Viewer",
            "📈 Evaluations",
            "🧑 Cmdrs",
            "🏆 Leaderboard",
            "🎯 Objectives",
            "🆕 Recruits",
            "🪙 Redeem Vouchers",
            "⚔️ CZ Summary",
            "📑 24h System Report",
            "🛰️ System Info (EDDN)"
        ],
        index=3
    )

# Seitenlogik
if page == "📊 Table Viewer":
    from pages import view_table
    view_table.render()
elif page == "📈 Evaluations":
    from pages import evaluations
    evaluations.render()
elif page == "🧑 Cmdrs":
    from pages import cmdrs
    cmdrs.render()
elif page == "🏆 Leaderboard":
    from pages import leaderboard
    leaderboard.render()
elif page == "🎯 Objectives":
    from pages import objectives
    objectives.render()
elif page == "🆕 Recruits":
    from pages import recruits
    recruits.render()
elif page == "🪙 Redeem Vouchers":
    from pages import redeem_vouchers
    redeem_vouchers.render()
elif page == "⚔️ CZ Summary":
    from pages import cz_summary
    cz_summary.main()
elif page == "📑 24h System Report":
    from pages import fsdjump_factions_report
    fsdjump_factions_report.render()
elif page == "🛰️ System Info (EDDN)":
    from pages import system_info
    system_info.render()
