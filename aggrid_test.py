import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# Testdaten
df = pd.DataFrame({
    "No.": [1, 2],
    "Cmdr.": ["Test1", "Test2"],
    "Buy (Cr.)": [123456789, 987654321],
    "Sell (Cr.)": [456789123, 654321987]
})

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_side_bar()
gb.configure_selection("single")
gb.configure_grid_options(groupDisplayType="multipleColumns")


gb.configure_column(
    "Buy (Cr.)",
    type=["numericColumn", "rightAligned"],
    valueFormatter="(value != null) ? 'TEST: ' + value : ''"
)

grid_options = gb.build()

AgGrid(
    df,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.NO_UPDATE,
    enable_enterprise_modules=True,
    allow_unsafe_jscode=True,
    theme="balham",
    height=200
)
