import streamlit as st
import plotly.express as px
import pandas as pd
from utils.data_loader import load_muni, load_geojson

st.header("🔄 Naturalization signals")
st.caption(
    "Municipalities where non-Belgian population shrank while Belgian population grew — "
    "a proxy for naturalization · Source: StatBel 2009–2025"
)

muni = load_muni()
geojson = load_geojson()

# Year-over-year deltas per municipality
df = muni.sort_values(["CD_REFNIS", "year"]).copy()
df["delta_etr"] = df.groupby("CD_REFNIS")["ETR"].diff()
df["delta_bel"] = df.groupby("CD_REFNIS")["BEL"].diff()
df["delta_pct"] = df.groupby("CD_REFNIS")["pct_etr"].diff().round(2)

# Naturalization score: ETR decrease only when BEL also increased in the same year
# (distinguishes naturalization from pure emigration)
etr_drop = (-df["delta_etr"]).clip(lower=0)
bel_rise = df["delta_bel"] > 0
df["nat_score"] = etr_drop.where(bel_rise, 0)
df["CD_REFNIS"] = df["CD_REFNIS"].astype(str)

# Controls
col_ctrl, col_map = st.columns([1, 3])
with col_ctrl:
    year = st.slider("Year", 2010, 2025, 2024)
    threshold = st.slider("Min. signal (persons)", 10, 500, 50, step=10)
    region_opts = sorted(muni["region_en"].dropna().unique())
    sel_regions = st.multiselect("Filter by region", region_opts, default=region_opts)

year_df = df[
    (df["year"] == year)
    & (df["region_en"].isin(sel_regions))
].copy()

map_df = year_df[year_df["nat_score"] >= threshold]

fig_map = px.choropleth(
    map_df,
    geojson=geojson,
    locations="CD_REFNIS",
    featureidkey="properties.NSI_CODE",
    color="nat_score",
    hover_name="TX_DESCR_NL",
    hover_data={
        "delta_etr": ":,.0f",
        "delta_bel": ":,.0f",
        "delta_pct": ":.2f",
        "CD_REFNIS": False,
    },
    color_continuous_scale="Purples",
    labels={
        "nat_score": "Signal",
        "delta_etr": "Δ Non-Belgians",
        "delta_bel": "Δ Belgians",
        "delta_pct": "Δ % Non-Belgian",
    },
)
fig_map.update_geos(fitbounds="locations", visible=False)
fig_map.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=560,
    paper_bgcolor="rgba(0,0,0,0)",
    geo=dict(bgcolor="rgba(0,0,0,0)"),
)
with col_map:
    if map_df.empty:
        st.info("No municipalities meet the current signal threshold. Lower the 'Min. signal' slider to see results.")
    else:
        st.plotly_chart(fig_map, use_container_width=True)

# Top municipalities table
st.divider()
st.subheader(f"Top 20 municipalities by signal strength — {year}")
top20 = year_df.nlargest(20, "nat_score")[
    [
        "TX_DESCR_NL",
        "TX_PROV_DESCR_NL",
        "region_en",
        "ETR",
        "delta_etr",
        "BEL",
        "delta_bel",
        "pct_etr",
        "delta_pct",
        "nat_score",
    ]
].copy()
top20.columns = [
    "Municipality",
    "Province",
    "Region",
    "Non-Belgians",
    "Δ Non-Belgians",
    "Belgians",
    "Δ Belgians",
    "% Non-Belgian",
    "Δ % Non-Belgian",
    "Signal",
]
st.dataframe(top20, use_container_width=True, hide_index=True)

# National aggregate signal over time
st.divider()
st.subheader("National aggregate signal over time")
annual = (
    df[df["nat_score"].notna()]
    .groupby("year")["nat_score"]
    .sum()
    .reset_index()
)
fig_line = px.line(
    annual,
    x="year",
    y="nat_score",
    markers=True,
    labels={"nat_score": "Aggregate signal (persons)", "year": "Year"},
    title="Sum of naturalization signal across all municipalities",
)
fig_line.update_layout(hovermode="x unified")
st.plotly_chart(fig_line, use_container_width=True)

# Distribution of signal by region
st.subheader("Signal distribution by region")
region_annual = (
    df[df["nat_score"].notna() & df["region_en"].isin(sel_regions)]
    .groupby(["year", "region_en"])["nat_score"]
    .sum()
    .reset_index()
    .rename(columns={"region_en": "Region"})
)
fig_reg = px.area(
    region_annual,
    x="year",
    y="nat_score",
    color="Region",
    labels={"nat_score": "Aggregate signal", "year": "Year"},
    title="Naturalization signal by region over time",
)
fig_reg.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig_reg, use_container_width=True)
