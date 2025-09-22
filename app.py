import streamlit as st
from auth import auth
from auth import login_page

# Check for login and display login page if needed
if not auth.is_logged_in():
    login_page.render()
    st.stop()  # Stop execution if not logged in

st.set_page_config(page_title="Sinistra", layout="wide")

# Sinistra Theme: Red, Orange, Yellow, Light Blue
st.markdown("""
    <style>
        :root {
            --sinistra-red: #FF4B4B;
            --sinistra-orange: #FF8C00;
            --sinistra-yellow: #FFD700;
            --sinistra-light-blue: #87CEEB;
        }
        
        body {
            background-color: #0e1117;
            color: #ffffff;
        }
        .block-container {
            padding-top: 2rem;
        }
        
        /* Sidebar styling with gradient */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a1a 0%, #2a1a1a 100%);
            border-right: 2px solid var(--sinistra-red);
        }

        /* Seiten-Navigation (oben links) ausblenden */
        [data-testid="stSidebarNav"] {
            display: none;
        }

        /* App title styling */
        [data-testid="stSidebar"] h1 {
            color: var(--sinistra-red) !important;
            font-weight: bold !important;
        }

        /* Menu items with colorful styling */
        [data-testid="stSidebar"] .stRadio > div {
            background: linear-gradient(45deg, rgba(255,75,75,0.1), rgba(255,140,0,0.1));
            border-radius: 10px;
            padding: 10px;
            border: 1px solid var(--sinistra-orange);
        }
        
        /* Radio button labels */
        [data-testid="stSidebar"] .stRadio label {
            color: var(--sinistra-yellow) !important;
            font-weight: 500 !important;
        }
        
        /* Selected radio button */
        [data-testid="stSidebar"] .stRadio input:checked + div {
            background: none !important;
            color: var(--sinistra-red) !important;
            font-weight: bold !important;
        }

        /* Login success message */
        .stSuccess {
            background: linear-gradient(90deg, var(--sinistra-red), var(--sinistra-orange)) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
        }

        /* Login form styling */
        .stAlert {
            background: linear-gradient(135deg, rgba(255,75,75,0.2), rgba(255,140,0,0.2));
            color: var(--sinistra-yellow);
            border: 1px solid var(--sinistra-light-blue);
            border-radius: 8px;
        }

        /* Buttons */
        .stButton > button {
            background: linear-gradient(45deg, var(--sinistra-red), var(--sinistra-orange));
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background: linear-gradient(45deg, var(--sinistra-orange), var(--sinistra-yellow));
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255,75,75,0.3);
        }

        /* Trennlinie unter Logo */
        .sidebar-logo-separator {
            border-top: 2px solid var(--sinistra-orange);
            margin: 0.5rem 0;
            box-shadow: 0 1px 3px var(--sinistra-red);
        }
        
        /* Main content area accents */
        .main .block-container {
            border-top: 3px solid var(--sinistra-light-blue);
        }
        
        /* Data tables and metrics */
        .metric-container {
            background: linear-gradient(135deg, rgba(135,206,235,0.1), rgba(255,215,0,0.1));
            border-radius: 8px;
            border-left: 4px solid var(--sinistra-light-blue);
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar mit Logo und Menü
with st.sidebar:
    st.image("assets/CIU.png", width=210)
    st.markdown('<div class="sidebar-logo-separator"></div>', unsafe_allow_html=True)
    
    # Benutzername und Tenant anzeigen (works with both login methods)
    username = st.session_state.user.get('username', 'Unknown')
    tenant = st.session_state.user.get('tenant_name', 'No Tenant')
    login_type = st.session_state.user.get('login_type', 'Unknown')
    is_admin = st.session_state.user.get('is_admin', False)
    
    # Show user info
    st.success(f"User: {username}")
    if tenant:
        st.success(f"Tenant: {tenant}")
    st.info(f"Login Type: {login_type}")
    if is_admin:
        st.success("Admin: Yes")
    
    # Logout-Button
    if st.button("Logout"):
        # Use the auth logout function that handles both login types
        auth.logout()
        st.rerun()
        
    page = st.radio(
        "📂 Menu",
        [
            "📊 Table Viewer",
            "📈 Evaluations",
            "🧑 Cmdrs",
            "🌏 Colonies",
            "🏆 Leaderboard",
            "🎯 Objectives",
            "🪙 Redeem Vouchers",
            "⚔️ CZ Summary",
            "📑 24h System Report",
            "🛰️ System Info (EDDN)",
            "🤖 Discord Management"
        ],
        index=5
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
elif page == "🌏 Colonies":
    from pages import colonies
    colonies.render()
elif page == "🏆 Leaderboard":
    from pages import leaderboard
    leaderboard.render()
elif page == "🎯 Objectives":
    from pages import objectives
    objectives.render()
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
elif page == "🤖 Discord Management":
    from pages import discord_management
    discord_management.render()
