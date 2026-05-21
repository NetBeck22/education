import streamlit as st
import plotly.express as px
from utils.data_loader import load_muni, load_geojson

st.header("🗺️ Non-Belgian population share by municipality")
st.caption("Share of non-Belgian residents as % of total municipal population · Source: StatBel")

muni_pivot = load_muni()
geojson = load_geojson()

col_ctrl, col_map = st.columns([1, 3])

with col_ctrl:
    year = st.slider("Year", 2009, 2025, 2025)
    max_pct = st.slider("Color scale max (%)", 10, 80, 40)
    region_filter = st.multiselect(
        "Filter by region",
        sorted(muni_pivot["region_en"].dropna().unique().tolist()),
        default=sorted(muni_pivot["region_en"].dropna().unique().tolist()),
    )
    search = st.text_input("Search municipality", "")

df_map = muni_pivot[
    (muni_pivot["year"] == year) &
    (muni_pivot["region_en"].isin(region_filter))
].copy()
df_map["CD_REFNIS"] = df_map["CD_REFNIS"].astype(str)

fig = px.choropleth(
    df_map,
    geojson=geojson,
    locations="CD_REFNIS",
    featureidkey="properties.NSI_CODE",
    color="pct_etr",
    hover_name="TX_DESCR_NL",
    hover_data={
        "total": ":,",
        "ETR": ":,",
        "pct_etr": ":.1f",
        "CD_REFNIS": False
    },
    color_continuous_scale="OrRd",
    range_color=[0, max_pct],
    labels={"pct_etr": "% non-Belgian"}
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=600,
    paper_bgcolor="rgba(0,0,0,0)",
    geo=dict(bgcolor="rgba(0,0,0,0)")
)

with col_map:
    st.plotly_chart(fig, use_container_width=True)

st.divider()
col_t1, col_t2 = st.columns(2)

with col_t1:
    st.subheader("Top 10 — highest non-Belgian share")
    top10 = df_map.nlargest(10, "pct_etr")[
        ["TX_DESCR_NL", "TX_PROV_DESCR_NL", "BEL", "ETR", "total", "pct_etr"]
    ]
    top10.columns = ["Municipality", "Province", "Belgians", "Non-Belgians", "Total", "% Non-Belgian"]
    st.dataframe(top10, use_container_width=True, hide_index=True)

with col_t2:
    st.subheader("Top 10 — fastest growing non-Belgian share")
    if year > 2009:
        df_prev = muni_pivot[muni_pivot["year"] == year - 1].copy()
        df_prev["CD_REFNIS"] = df_prev["CD_REFNIS"].astype(str)
        df_growth = df_map.merge(
            df_prev[["CD_REFNIS", "pct_etr"]].rename(columns={"pct_etr": "pct_prev"}),
            on="CD_REFNIS",
            how="left",
        )
        df_growth["change"] = (df_growth["pct_etr"] - df_growth["pct_prev"]).round(2)
        top_growth = df_growth.nlargest(10, "change")[
            ["TX_DESCR_NL", "TX_PROV_DESCR_NL", "pct_prev", "pct_etr", "change"]
        ]
        top_growth.columns = ["Municipality", "Province", "% prev year", "% this year", "Change (pp)"]
        st.dataframe(top_growth, use_container_width=True, hide_index=True)
    else:
        st.info("Select a year after 2009 to see growth comparison.")

if search:
    st.divider()
    st.subheader(f"Search results for '{search}'")
    results = df_map[df_map["TX_DESCR_NL"].str.contains(search, case=False, na=False)]
    if len(results):
        st.dataframe(
            results[["TX_DESCR_NL", "TX_PROV_DESCR_NL", "BEL", "ETR", "total", "pct_etr"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.warning("No municipalities found.")