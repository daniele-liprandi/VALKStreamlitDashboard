import streamlit as st
import pandas as pd
import plotly.express as px
from api_client import get_json
from auth import user_has_access
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

def render():
    if not user_has_access(st.session_state.user, '6_RedeemVouchers'):
        st.error('Unauthorized')
        st.stop()

    st.title("🪙 Bounty Voucher Redemptions")

    # Period selection
    period_labels = {
        "cd": "Today",
        "ld": "Yesterday",
        "cw": "Current Week",
        "lw": "Last Week",
        "cm": "Current Month",
        "lm": "Last Month",
        "2m": "Last 2 Months",
        "y": "Current Year",
        "all": "All Time"
    }
    selected_label = st.selectbox("Select period:", list(period_labels.values()))
    selected_period = [k for k, v in period_labels.items() if v == selected_label][0]

    try:
        data = get_json(f"bounty-vouchers?period={selected_period}")
        if not data:
            st.warning("No voucher data found.")
            return

        df = pd.DataFrame(data)
        if df.empty:
            st.warning("No voucher data found.")
            return

        # Readable column names
        rename_map = {
            "cmdr": "Cmdr",
            "squadron_rank": "Squadron Rank",
            "tickid": "Tick ID",
            "timestamp": "Timestamp",
            "system": "Star System",
            "faction": "Faction",
            "amount": "Voucher Amount",
            "redeem_time": "Redemption Time"
        }
        df.rename(columns=rename_map, inplace=True)

        # Filter selection boxes
        cmdr_list = sorted(df["Cmdr"].dropna().unique())
        starsystem_list = sorted(df["Star System"].dropna().unique())
        faction_list = sorted(df["Faction"].dropna().unique())

        col1, col2, col3 = st.columns(3)
        with col1:
            selected_cmdr = st.multiselect("Select Cmdr:", cmdr_list)
        with col2:
            selected_starsystem = st.multiselect("Select Star System:", starsystem_list)
        with col3:
            selected_faction = st.multiselect("Select Faction:", faction_list)

        # Apply filters
        filtered_df = df.copy()
        if selected_cmdr:
            filtered_df = filtered_df[filtered_df["Cmdr"].isin(selected_cmdr)]
        if selected_starsystem:
            filtered_df = filtered_df[filtered_df["Star System"].isin(selected_starsystem)]
        if selected_faction:
            filtered_df = filtered_df[filtered_df["Faction"].isin(selected_faction)]

        # Prepare summary row
        def get_group_sum(params):
            field = params['colDef']['field']
            if field == "Voucher Amount":
                return f"{params['values'].sum():,.0f}"
            return ""

        gb = GridOptionsBuilder.from_dataframe(filtered_df)
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
        gb.configure_column("Voucher Amount", type=["numericColumn", "rightAligned"],
                            valueFormatter="(value != null) ? value.toLocaleString('en-US') : ''",
                            aggFunc="sum", footerValueGetter="sum")
        gb.configure_column("Cmdr", width=150, pinned="left")
        gb.configure_column("Star System", width=150)
        gb.configure_column("Faction", width=150)
        gb.configure_column("Redemption Time", width=180)
        gb.configure_grid_options(
            groupIncludeFooter=True,
            groupIncludeTotalFooter=True
        )
        grid_options = gb.build()

        st.subheader("Voucher Redemptions (Table)")
        grid_response = AgGrid(
            filtered_df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.NO_UPDATE,
            enable_enterprise_modules=True,
            allow_unsafe_jscode=True,
            domLayout="normal",
            height=min(500, 70 + 35 * len(filtered_df))
        )

        visible_df = pd.DataFrame(grid_response["data"])

        st.subheader("📊 Voucher Amount by Cmdr (Pie Chart)")
        pie_df = visible_df.groupby("Cmdr", as_index=False)["Voucher Amount"].sum()
        pie_df = pie_df[pie_df["Voucher Amount"] > 0]
        pie_df = pie_df[pie_df["Cmdr"].notnull() & (pie_df["Cmdr"].str.strip() != "")]
        if not pie_df.empty:
            fig = px.pie(
                pie_df,
                names="Cmdr",
                values="Voucher Amount",
                title="Total Redeemed Voucher Amount per Cmdr",
                hole=0.4
            )
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No voucher data available for the chart.")

    except Exception as e:
        st.error(f"Error loading voucher data: {e}")
