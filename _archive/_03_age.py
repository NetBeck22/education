import streamlit as st
import plotly.express as px
import pandas as pd
from utils.data_loader import load_region

st.header("👥 Age structure by nationality")
st.caption("Age breakdown across Belgians and non-Belgians · Source: StatBel 1992–2025")

region = load_region()

AGE_ORDER = ["Less than 18 years", "From 18 to 64 years", "65 years and more"]
COLOR_MAP = {"Belgians": "#1f77b4", "non-Belgians": "#ff7f0e"}

# Age Group rows always have a specific Marital Status — sum over both Gender and Marital Status
age = (
    region[
        region["Age Group"].notna()
        & region["Nationality"].notna()
        & region["Region"].notna()
    ]
    .groupby(["year", "Region", "Nationality", "Age Group"])["population"]
    .sum()
    .reset_index()
)

# Controls
col1, col2 = st.columns(2)
with col1:
    year = st.slider("Year", int(age["year"].min()), int(age["year"].max()), 2024)
with col2:
    region_opts = ["All regions"] + sorted(age["Region"].unique())
    sel_region = st.selectbox("Region", region_opts)

df = age[age["year"] == year].copy()
if sel_region != "All regions":
    df = df[df["Region"] == sel_region]

df_agg = df.groupby(["Nationality", "Age Group"])["population"].sum().reset_index()
df_agg["Age Group"] = pd.Categorical(df_agg["Age Group"], categories=AGE_ORDER, ordered=True)
df_agg = df_agg.sort_values(["Nationality", "Age Group"])

total_by_nat = df_agg.groupby("Nationality")["population"].transform("sum")
df_agg["pct"] = (df_agg["population"] / total_by_nat * 100).round(1)

col_a, col_b = st.columns(2)
with col_a:
    fig1 = px.bar(
        df_agg,
        x="Age Group",
        y="population",
        color="Nationality",
        barmode="group",
        color_discrete_map=COLOR_MAP,
        labels={"population": "Population", "Age Group": ""},
        title=f"Population by age group — {year}",
    )
    fig1.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    fig2 = px.bar(
        df_agg,
        x="Age Group",
        y="pct",
        color="Nationality",
        barmode="group",
        color_discrete_map=COLOR_MAP,
        labels={"pct": "% within nationality", "Age Group": ""},
        title=f"Age distribution within nationality — {year}",
    )
    fig2.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig2, use_container_width=True)

# Age structure over time
st.divider()
st.subheader("Age structure over time")
nat_choice = st.radio("Nationality", ["Belgians", "non-Belgians"], horizontal=True)

time_df = age.copy()
if sel_region != "All regions":
    time_df = time_df[time_df["Region"] == sel_region]

time_agg = (
    time_df[time_df["Nationality"] == nat_choice]
    .groupby(["year", "Age Group"])["population"]
    .sum()
    .reset_index()
)
time_agg["Age Group"] = pd.Categorical(time_agg["Age Group"], categories=AGE_ORDER, ordered=True)
time_agg = time_agg.sort_values(["year", "Age Group"])

# Also compute share within nationality per year
time_total = time_agg.groupby("year")["population"].transform("sum")
time_agg["pct"] = (time_agg["population"] / time_total * 100).round(1)

tab1, tab2 = st.tabs(["Absolute", "Share (%)"])
with tab1:
    fig3 = px.area(
        time_agg,
        x="year",
        y="population",
        color="Age Group",
        labels={"population": "Population", "year": "Year", "Age Group": "Age group"},
        title=f"Age structure over time — {nat_choice}",
    )
    fig3.update_layout(hovermode="x unified")
    st.plotly_chart(fig3, use_container_width=True)

with tab2:
    fig4 = px.area(
        time_agg,
        x="year",
        y="pct",
        color="Age Group",
        labels={"pct": "Share (%)", "year": "Year", "Age Group": "Age group"},
        title=f"Age share over time — {nat_choice}",
    )
    fig4.update_layout(hovermode="x unified")
    st.plotly_chart(fig4, use_container_width=True)
