import streamlit as st
from datetime import datetime
from api_client import get_json
from pages.system_info import chip_css, chip

def _truncate(s: str, n: int = 40) -> str:
    """Truncate string to n characters"""
    if not s:
        return ""
    s = str(s).strip()
    return (s[:n] + "…") if len(s) > n else s


def _fetch_target_progress(target: dict, obj: dict) -> dict:
    """Fetch current tick progress for a specific target"""
    try:
        target_type = target.get("type", "").lower()
        system = target.get("system") or obj.get("system")
        faction = target.get("faction") or obj.get("faction")
        
        # Map target types to API endpoints and data extraction
        if target_type == "space_cz":
            # Fetch space CZ data for current tick
            data = get_json("syntheticcz-summary", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                total = sum(row.get("cz_count", 0) for row in data if row.get("starsystem") == system)
                return {"total": total, "label": "CZs completed"}
        
        elif target_type == "ground_cz":
            # Fetch ground CZ data for current tick
            data = get_json("syntheticgroundcz-summary", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                total = sum(row.get("cz_count", 0) for row in data if row.get("starsystem") == system)
                return {"total": total, "label": "Ground CZs completed"}
        
        elif target_type == "bv":
            # Fetch bounty vouchers
            data = get_json("summary/bounty-vouchers", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                total = sum(row.get("total", 0) for row in data)
                return {"total": total, "label": "CR in bounties"}
        
        elif target_type == "cb":
            # Fetch combat bonds
            data = get_json("summary/combat-bonds", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                total = sum(row.get("total", 0) for row in data)
                return {"total": total, "label": "CR in bonds"}
        
        elif target_type == "inf":
            # Fetch influence data
            data = get_json("summary/influence-by-faction", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                # Sum influence for the specific faction
                total = sum(row.get("influence_gained", 0) for row in data if row.get("faction") == faction)
                return {"total": total, "label": "INF gained"}
        
        elif target_type == "expl":
            # Fetch exploration data
            data = get_json("summary/exploration-sales", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                total = sum(row.get("total", 0) for row in data)
                return {"total": total, "label": "CR in exploration"}
        
        elif target_type == "trade_prof":
            # Fetch trade profit data
            data = get_json("summary/market-events", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                total = sum(row.get("total_profit", 0) for row in data)
                return {"total": total, "label": "CR profit"}
        
        elif target_type == "mission_fail":
            # Fetch mission failures
            data = get_json("summary/missions-failed", params={"period": "ct", "system_name": system})
            if data and isinstance(data, list):
                total = len(data)
                return {"total": total, "label": "missions failed"}
        
        return {"total": 0, "label": ""}
    except Exception as e:
        # Silently fail and return 0 to avoid breaking the UI
        return {"total": 0, "label": ""}


def _get_status(obj: dict) -> str:
    """Determine if objective is active or expired"""
    try:
        if obj.get("enddate"):
            end = datetime.fromisoformat(obj["enddate"].replace("Z", ""))
            if end < datetime.utcnow():
                return "Expired"
        return "Active"
    except Exception:
        return "Active"


def _get_target_icon(target_type: str) -> str:
    """Return emoji icon for target type"""
    icons = {
        "visit": "🛸",
        "inf": "📈",
        "bv": "💰",
        "cb": "🎯",
        "expl": "🔭",
        "trade_prof": "📦",
        "bm_prof": "⛏️",
        "ground_cz": "⚔️",
        "space_cz": "🚀",
        "murder": "💀",
        "mission_fail": "❌"
    }
    return icons.get(target_type.lower(), "🎯")


def render_objective_card(obj: dict):
    """Render a compact, readable objective card"""
    status = _get_status(obj)
    status_color = "🟢" if status == "Active" else "🔴"
    
    # Priority styling
    priority = int(obj.get("priority", 0))
    priority_stars = "⭐" * min(priority, 5)
    
    # Card header
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(255,75,75,0.1), rgba(255,140,0,0.1));
        border-left: 4px solid #FF4B4B;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    ">
        <h3 style="margin: 0; color: #FFD700;">
            {status_color} {obj.get('title', 'Unnamed Objective')}
        </h3>
        <p style="margin: 0.5rem 0 0 0; color: #87CEEB; font-size: 0.9rem;">
            {priority_stars} Priority {priority} | 📍 {obj.get('system', 'N/A')} | 🏴 {obj.get('faction', 'N/A')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Description
    if obj.get("description"):
        st.markdown(f"**📋 Description:** {obj['description']}")
    
    # Targets
    targets = obj.get("targets", [])
    if targets:
        st.markdown("**🎯 Targets:**")
        for idx, target in enumerate(targets, 1):
            icon = _get_target_icon(target.get("type", ""))
            target_type = (target.get("type") or "unknown").upper()
            system = target.get("system") or obj.get("system") or "N/A"
            
            # Progress bar
            progress = int(target.get("progress", 0))
            target_indiv = target.get("targetindividual", 0)
            target_overall = target.get("targetoverall", 0)
            
            # Fetch current tick progress
            progress_data = _fetch_target_progress(target, obj)
            current_total = progress_data.get("total", 0)
            progress_label = progress_data.get("label", "")
            
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.markdown(f"{icon} **{target_type}** @ {system}")
            with col2:
                if target_indiv > 0:
                    st.markdown(f"Target/CMDR: **{target_indiv:,}**")
            with col3:
                if target_overall > 0:
                    st.markdown(f"Target Overall: **{target_overall:,}**")
            
            # Show current tick progress
            if current_total > 0:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"📊 **Current Tick:**")
                with col2:
                    # Format the number based on type
                    if "CR" in progress_label:
                        formatted_total = f"{current_total:,.0f}"
                    else:
                        formatted_total = f"{int(current_total):,}"
                    
                    st.markdown(f"**{formatted_total}** {progress_label}")
                    
                    # Calculate percentage if target is set
                    if target_overall > 0 and "CR" not in progress_label:
                        percentage = min((current_total / target_overall) * 100, 100)
                        st.progress(percentage / 100.0)
                        st.caption(f"{percentage:.1f}% of overall target")
            
            if progress > 0:
                st.progress(min(progress / 100.0, 1.0))
            
            # Settlements for ground CZ
            settlements = target.get("settlements", [])
            if settlements and target.get("type") == "ground_cz":
                with st.expander(f"🏘️ Settlements ({len(settlements)})"):
                    for settlement in settlements:
                        st.markdown(f"- **{settlement.get('name')}**: {settlement.get('targetindividual', 0):,} per CMDR, {settlement.get('targetoverall', 0):,} overall")
    
    # Dates
    col1, col2 = st.columns(2)
    with col1:
        if obj.get("startdate"):
            start = obj["startdate"].split("T")[0]
            st.markdown(f"🗓️ **Start:** {start}")
    with col2:
        if obj.get("enddate"):
            end = obj["enddate"].split("T")[0]
            st.markdown(f"🏁 **End:** {end}")
    
    st.markdown("---")

def render():
    """Render the home page"""
    st.set_page_config(page_title="🏠 Sinistra Home", layout="wide")
    
    # Welcome header
    user = st.session_state.get('user', {})
    username = user.get('username', 'Comrade')
    
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="
            background: linear-gradient(45deg, #FF4B4B, #FF8C00, #FFD700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 3rem;
            font-weight: bold;
        ">
            ⚒️ Welcome to Sinistra, {username}! ⚒️
        </h1>
        <p style="color: #87CEEB; font-size: 1.2rem; margin-top: 1rem;">
            From each according to their ability, to each according to their needs
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick action buttons
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📑 24h System Report", use_container_width=True, type="primary"):
            st.session_state['navigation_target'] = "📑 24h System Report"
            st.rerun()
    
    with col2:
        if st.button("⚔️ CZ Summary", use_container_width=True, type="primary"):
            st.session_state['navigation_target'] = "⚔️ CZ Summary"
            st.rerun()
    
    with col3:
        if st.button("🌏 Colonies", use_container_width=True, type="primary"):
            st.session_state['navigation_target'] = "🌏 Colonies"
            st.rerun()
    
    st.markdown("---")
    
    # Colonization Goals and Active Objectives Section
    # Use responsive layout: side by side on large screens, stacked on small screens
    try:
        # Fetch priority colonies
        priority_colonies = get_json('colonies/priority')
        has_priority_colonies = priority_colonies and len(priority_colonies) > 0
    except Exception as e:
        priority_colonies = []
        has_priority_colonies = False
    
    # Create columns for responsive layout if we have priority colonies
    if has_priority_colonies:
        # On large screens: objectives on left (65%), colonies on right (35%)
        # On small screens: will stack automatically
        col_objectives, gap, col_colonies = st.columns([55,10, 35])
        
        with col_colonies:
            st.markdown("## 🌍 Colonization Goals")
           
            for colony in priority_colonies[:2]:  # Show top 2 priority colonies
                priority = colony.get('priority', 0)
                system = colony.get('starsystem', 'Unknown')
                cmdr = colony.get('cmdr', 'N/A')
                ravenurl = colony.get('ravenurl', '')
                
                # Priority badge
                priority_stars = "⭐" * min(priority, 5)
                
                st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(255,75,75,0.1), rgba(255,140,0,0.1));
                        border-left: 4px solid #FF4B4B;
                        border-radius: 8px;
                        padding: 1rem;
                        margin-bottom: 1rem;
                    ">
                    <h3 style="margin: 0; color: #FFD700;">
                        {priority_stars} {system}
                    </h3>
                    <p style="margin: 0.25rem 0; color: #87CEEB; font-size: 0.9rem;">
                        Commander: {cmdr}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add button below the card using Streamlit's link_button
                if ravenurl:
                    st.link_button(
                        "🔗 Open on Raven Colonial",
                        ravenurl,
                        use_container_width=True,
                        type="secondary"
                    )
                
                st.markdown("<br>", unsafe_allow_html=True)
                    
        with col_objectives:
            st.markdown("## 🎯 Current Objectives")
            _render_objectives_section()
    else:
        # No priority colonies, show objectives full width
        st.markdown("## 🎯 Current Objectives")
        _render_objectives_section()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>The mine to the miner, and the space to the spacer</p>
    </div>
    """, unsafe_allow_html=True)


def _render_objectives_section():
    """Helper function to render the objectives section"""
    try:
        # Fetch active objectives
        objectives_data = get_json('objectives', params={'active': 'false'})
        
        if objectives_data:
            # Separate active and expired
            now = datetime.utcnow()
            active_objectives = []
            expired_objectives = []
            
            for obj in objectives_data:
                if _get_status(obj) == "Active":
                    active_objectives.append(obj)
                else:
                    expired_objectives.append(obj)
            
            # Sort by priority (highest first)
            active_objectives.sort(key=lambda x: int(x.get('priority', 0)), reverse=True)
            
            if active_objectives:
                for obj in active_objectives:
                    render_objective_card(obj)
            else:
                st.info("No active objectives at the moment.")
            
            # Show expired objectives in expander
            if expired_objectives:
                with st.expander(f"📜 Expired Objectives ({len(expired_objectives)})"):
                    for obj in expired_objectives:
                        render_objective_card(obj)
        else:
            st.info("No current objectives exist.")
            
    except Exception as e:
        st.warning(f"⚠️ Could not load objectives: {str(e)}")
        st.info("You can still access all features using the quick action buttons above.")

