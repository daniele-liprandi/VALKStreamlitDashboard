import streamlit as st
import pandas as pd
import plotly.express as px
from api_client import get_json
from auth import user_has_access
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def render():
    if not user_has_access(st.session_state.user, '4_Leadership'):
        st.error('Unauthorized')
        st.stop()

    st.title("🏆 Leaderboard")

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

    try:
        data = get_json(f"summary/leaderboard?period={selected_period}")
        if not data:
            st.warning("No Leaderboard-Data found.")
            return

        df = pd.DataFrame(data)
        df = df.fillna(0).infer_objects(copy=False)

        rename_map = {
            "cmdr": "Cmdr.",
            "squadron_rank": "Sq.-Rank",
            "rank": "Sq.-Rank",
            "total_buy": "Buy (Cr.)",
            "total_sell": "Sell (Cr.)",
            "profit": "Profit (Cr.)",
            "profitability": "Profit (%)",
            "bounty_vouchers": "BVs (Cr.)",
            "combat_bonds": "CBs (Cr.)",
            "exploration_sales": "Expo. (Cr.)",
            "missions_completed": "M.compl.",
            "missions_failed": "M.failed",
            "influence_eic": "Inf.-EIC",
            "total_quantity": "Q. (t)",
            "total_volume": "Vol. (Cr.)",
            "bounty_fines": "Fines (Cr.)"
        }
        df.rename(columns=rename_map, inplace=True)

        # Replace missing or 0 values in Sq.-Rank with "n/a"
        if "Sq.-Rank" in df.columns:
            df["Sq.-Rank"] = df["Sq.-Rank"].replace(0, pd.NA)
            df["Sq.-Rank"] = df["Sq.-Rank"].fillna("n/a")

        df.insert(0, "No.", range(1, len(df) + 1))

        ordered_cols = ["No.", "Cmdr.", "Sq.-Rank", "Buy (Cr.)", "Sell (Cr.)", "Profit (Cr.)", "Profit (%)",
                        "Vol. (Cr.)", "Q. (t)", "BVs (Cr.)", "CBs (Cr.)", "Expo. (Cr.)", "M.compl.", "M.failed",
                        "Inf.-EIC", "Fines (Cr.)"]
        df = df[[col for col in ordered_cols if col in df.columns]]

        numeric_cols = [col for col in df.columns if col not in ["No.", "Cmdr.", "Sq.-Rank"]]

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

        for colname, width in [("No.", 70), ("Cmdr.", 150), ("Sq.-Rank", 140)]:
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

        # Extract only currently visible rows from grid
        visible_df = pd.DataFrame(grid_response["data"])

        st.subheader("📊 Distribution by Cmdr (Pie Chart)")

        # Available metrics for charting
        plotly_options = {
            "M.compl.": "Missions Completed",
            "M.failed": "Missions Failed",
            "Inf.-EIC": "Influence (East India Company)",
            "Buy (Cr.)": "Total Buy",
            "Sell (Cr.)": "Total Sell",
            "Profit (Cr.)": "Profit",
            "Vol. (Cr.)": "Market Volume",
            "Q. (t)": "Market Quantity",
            "BVs (Cr.)": "Bounty Vouchers",
            "CBs (Cr.)": "Combat Bonds",
            "Expo. (Cr.)": "Exploration Sales",
            "Fines (Cr.)": "Bounty Fines"
        }

        selected_metric = st.selectbox(
            "Select metric to visualize:",
            options=list(plotly_options.keys()),
            format_func=lambda k: plotly_options[k]
        )

        # Check if selected metric is in dataframe
        if selected_metric in visible_df.columns:
            pie_df = visible_df[["Cmdr.", selected_metric]].copy()
            pie_df = pie_df[pie_df[selected_metric] > 0]
            pie_df = pie_df[pie_df["Cmdr."].notnull() & (pie_df["Cmdr."].str.strip() != "")]

            if not pie_df.empty:
                fig = px.pie(
                    pie_df,
                    names="Cmdr.",
                    values=selected_metric,
                    title=f"{plotly_options[selected_metric]} by Cmdr",
                    hole=0.4
                )
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for the selected metric.")
        else:
            st.warning(f"Column '{selected_metric}' not found in the dataset.")

        st.subheader("📊 Buy / Sell / Profit per Cmdr (Bar Chart)")

        required_columns = ["Cmdr.", "Buy (Cr.)", "Sell (Cr.)", "Profit (Cr.)"]

        if all(col in visible_df.columns for col in required_columns):
            # Filter Cmdrs with any non-zero financial data
            bar_df = visible_df[required_columns].copy()
            bar_df = bar_df[
                (bar_df["Buy (Cr.)"] > 0) | (bar_df["Sell (Cr.)"] > 0) | (bar_df["Profit (Cr.)"] != 0)
                ]

            if not bar_df.empty:
                # Transform into long format for grouped bar chart
                bar_df_long = bar_df.melt(id_vars="Cmdr.", var_name="Category", value_name="Value")

                fig = px.bar(
                    bar_df_long,
                    x="Cmdr.",
                    y="Value",
                    color="Category",
                    barmode="group",
                    title="Buy, Sell and Profit by Cmdr",
                    text_auto=".2s"
                )

                fig.update_layout(xaxis_title="Cmdr", yaxis_title="Credits", legend_title="Category")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No financial data available for plotting.")
        else:
            st.warning("Required columns ('Buy (Cr.)', 'Sell (Cr.)', 'Profit (Cr.)') are missing.")

    except Exception as e:
        st.error(f"Error loading Leaderboard: {e}")