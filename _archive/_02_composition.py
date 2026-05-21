import streamlit as st
import plotly.express as px
import pandas as pd
from utils.data_loader import load_region

st.header("📈 Population composition over time")
st.caption("Belgian vs non-Belgian population by region · Source: StatBel 1992–2025")

region = load_region()

# Sum over gender to get population totals by year / region / nationality
# (gender-level rows have Marital Status=NaN and Age Group=NaN in this dataset)
base = (
    region[
        region["Gender"].notna()
        & region["Marital Status"].isna()
        & region["Age Group"].isna()
        & region["Nationality"].notna()
        & region["Region"].notna()
    ]
    .groupby(["year", "Region", "Nationality"])["population"]
    .sum()
    .reset_index()
)

regions_all = sorted(base["Region"].unique())
col_ctrl, col_view = st.columns([2, 1])
with col_ctrl:
    sel_regions = st.multiselect("Filter by region", regions_all, default=regions_all)
with col_view:
    view = st.radio("View", ["Absolute count", "Percentage share"], horizontal=True)

df = base[base["Region"].isin(sel_regions)]
agg = df.groupby(["year", "Nationality"])["population"].sum().reset_index()

if view == "Percentage share":
    total_per_year = agg.groupby("year")["population"].transform("sum")
    agg["population"] = (agg["population"] / total_per_year * 100).round(2)
    y_label = "Share (%)"
else:
    y_label = "Population"

COLOR_MAP = {"Belgians": "#1f77b4", "non-Belgians": "#ff7f0e"}

fig = px.area(
    agg,
    x="year",
    y="population",
    color="Nationality",
    color_discrete_map=COLOR_MAP,
    labels={"population": y_label, "year": "Year"},
    title="Belgian vs non-Belgian population 1992–2025",
)
fig.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig, use_container_width=True)

# Per-region breakdown when multiple regions selected
if len(sel_regions) > 1:
    st.subheader("Breakdown by region")
    region_agg = (
        df.groupby(["year", "Region", "Nationality"])["population"]
        .sum()
        .reset_index()
    )
    fig2 = px.area(
        region_agg,
        x="year",
        y="population",
        color="Nationality",
        facet_col="Region",
        facet_col_wrap=3,
        color_discrete_map=COLOR_MAP,
        labels={"population": "Population", "year": "Year"},
    )
    fig2.update_layout(height=380, showlegend=False)
    fig2.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(fig2, use_container_width=True)

# Snapshot table for selected year
st.divider()
st.subheader("Snapshot — selected year")
snap_year = st.slider("Year", int(base["year"].min()), int(base["year"].max()), 2024)
snap = (
    base[base["year"] == snap_year]
    .pivot_table(index="Region", columns="Nationality", values="population", aggfunc="sum")
    .reset_index()
)
snap.columns.name = None
snap["Total"] = snap.get("Belgians", 0) + snap.get("non-Belgians", 0)
snap["% non-Belgian"] = (snap.get("non-Belgians", 0) / snap["Total"] * 100).round(1)
snap = snap.rename(columns={"Belgians": "Belgians", "non-Belgians": "Non-Belgians"})
st.dataframe(snap, use_container_width=True, hide_index=True)
