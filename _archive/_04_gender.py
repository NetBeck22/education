import streamlit as st
import plotly.express as px
import pandas as pd
from utils.data_loader import load_region

st.header("⚧ Gender ratio in the population")
st.caption("Men-to-women ratio by region and year · Source: StatBel 1992–2025")

region = load_region()

# Gender-level rows: Marital Status=NaN, Age Group=NaN, Gender not NaN
gender = region[
    region["Gender"].notna()
    & region["Marital Status"].isna()
    & region["Age Group"].isna()
    & region["Nationality"].notna()
    & region["Region"].notna()
].copy()

nat_choice = st.radio(
    "Nationality",
    ["non-Belgians", "Belgians"],
    horizontal=True,
    help="Choose which group's gender ratio to examine",
)

data = gender[gender["Nationality"] == nat_choice]

# Pivot to Men/Women columns and compute ratio
pivot = (
    data.pivot_table(
        index=["year", "Region"],
        columns="Gender",
        values="population",
        aggfunc="sum",
    )
    .reset_index()
)
pivot.columns.name = None
pivot["ratio"] = (pivot["Men"] / pivot["Women"]).round(3)

# Heatmap: Region × Year
st.subheader("Heatmap — Men/Women ratio")
heatmap_data = pivot.pivot(index="Region", columns="year", values="ratio")

fig1 = px.imshow(
    heatmap_data,
    color_continuous_scale="RdBu_r",
    color_continuous_midpoint=1.0,
    aspect="auto",
    labels={"color": "Men / Women"},
    title=f"Men/Women ratio — {nat_choice}",
)
fig1.update_layout(height=280, margin={"t": 40})
st.plotly_chart(fig1, use_container_width=True)

# Line chart over time
st.subheader("Trend over time")
fig2 = px.line(
    pivot,
    x="year",
    y="ratio",
    color="Region",
    markers=True,
    labels={"ratio": "Men / Women", "year": "Year"},
    title=f"Men/Women ratio by region — {nat_choice}",
)
fig2.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="Parity (1.0)")
fig2.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig2, use_container_width=True)

# Absolute counts for a selected year
st.divider()
st.subheader("Absolute counts — selected year")
year = st.slider(
    "Year",
    int(data["year"].min()),
    int(data["year"].max()),
    2024,
)
year_data = data[data["year"] == year]

fig3 = px.bar(
    year_data,
    x="Region",
    y="population",
    color="Gender",
    barmode="group",
    color_discrete_map={"Men": "#4c78a8", "Women": "#e45756"},
    labels={"population": "Population"},
    title=f"{nat_choice} — Men vs Women by region ({year})",
)
fig3.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig3, use_container_width=True)

# Summary table
st.subheader(f"Summary table — {year}")
tbl = pivot[pivot["year"] == year][["Region", "Men", "Women", "ratio"]].copy()
tbl.columns = ["Region", "Men", "Women", "Men/Women ratio"]
tbl["Men/Women ratio"] = tbl["Men/Women ratio"].map("{:.3f}".format)
st.dataframe(tbl, use_container_width=True, hide_index=True)
