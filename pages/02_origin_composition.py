import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.data_loader import load_origin, load_region

THEME_CSS = """
<style>
h1 { font-size: 2rem !important; font-weight: 700; }
hr { border-color: #E2DED8 !important; margin: 1.25rem 0; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.title("🌍 Origin & Composition")
st.caption(
    "How Belgium's population breaks down by origin group, age, and gender · StatBel 2000–2025"
)

origin = load_origin()
region_df = load_region()

ORIGIN_COLS = ["belgian_bg", "neighbouring", "eu27", "non_eu27"]
ORIGIN_LABELS = ["Belgian background", "Neighbouring countries", "EU27", "Non-EU27"]
ORIGIN_COLORS = ["#1B2A4A", "#2E86AB", "#5BA4CF", "#A8D5E2"]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Sankey: origin groups → regions
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Population flows by origin group")

col_ctrl, col_insight = st.columns([3, 1])

with col_ctrl:
    year_s = st.slider("Year", 2000, 2025, 2024, key="sankey_year")
    view_s = st.radio(
        "View",
        ["Population count", "% of region total"],
        horizontal=True,
        key="sankey_view",
    )

agg = (
    origin[origin["year"] == year_s]
    .groupby("region_en")[ORIGIN_COLS + ["total"]]
    .sum()
    .reset_index()
)
agg = agg[agg["region_en"].notna()].sort_values("region_en").reset_index(drop=True)
regions = agg["region_en"].tolist()
all_labels = ORIGIN_LABELS + regions

source_idx, target_idx, link_values = [], [], []
for r_pos, row in agg.iterrows():
    region_node = len(ORIGIN_LABELS) + r_pos
    for o_pos, col in enumerate(ORIGIN_COLS):
        val = row[col]
        if view_s == "% of region total" and row["total"] > 0:
            val = val / row["total"] * 100
        source_idx.append(o_pos)
        target_idx.append(region_node)
        link_values.append(float(val) if not pd.isna(val) else 0.0)

node_colors = ORIGIN_COLORS + ["#B5C9E0", "#7BA7C9", "#3D6E96"]

fig_sankey = go.Figure(
    go.Sankey(
        node=dict(
            pad=18,
            thickness=22,
            line=dict(color="#E2DED8", width=0.5),
            label=all_labels,
            color=node_colors,
        ),
        link=dict(
            source=source_idx,
            target=target_idx,
            value=link_values,
            color="rgba(46, 134, 171, 0.18)",
        ),
    )
)
fig_sankey.update_layout(
    height=400,
    margin={"t": 10, "b": 10, "l": 10, "r": 10},
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12, color="#1B2A4A"),
)

with col_ctrl:
    st.plotly_chart(fig_sankey, use_container_width=True)
    st.caption(
        "Flows show how each origin group distributes across Belgium's three regions. "
        "Belgian-background residents dominate all three; non-EU27 share is highest in Brussels."
    )

with col_insight:
    st.markdown("**Reading this chart**")
    st.markdown(
        "Left nodes are origin groups. Right nodes are regions. "
        "Wider bands = larger population flows. "
        "Toggle between total counts and share of each region's population to compare concentration."
    )
    st.divider()

    # Quick stats for selected year
    nat_totals = agg[ORIGIN_COLS].sum()
    grand_total = nat_totals.sum()
    st.markdown("**National mix**")
    for label, col in zip(ORIGIN_LABELS, ORIGIN_COLS):
        pct = nat_totals[col] / grand_total * 100
        st.markdown(f"- {label}: **{pct:.1f}%**")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Age breakdown by nationality
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Age breakdown by nationality")

AGE_MAP = {
    "Less than 18 years": "Under 18",
    "From 18 to 64 years": "18–64",
    "65 years and more":  "65+",
}
AGE_ORDER = ["Under 18", "18–64", "65+"]

age_raw = (
    region_df[
        region_df["Age Group"].notna()
        & region_df["Nationality"].notna()
        & region_df["Region"].notna()
    ]
    .groupby(["year", "Nationality", "Age Group"])["population"]
    .sum()
    .reset_index()
)

year_a = st.slider(
    "Year",
    int(age_raw["year"].min()),
    int(age_raw["year"].max()),
    2024,
    key="age_year",
)

age_yr = age_raw[age_raw["year"] == year_a].copy()
total_by_nat = age_yr.groupby("Nationality")["population"].transform("sum")
age_yr["pct"] = (age_yr["population"] / total_by_nat * 100).round(1)
age_yr["Age group"] = age_yr["Age Group"].map(AGE_MAP)

fig_age = px.bar(
    age_yr,
    x="pct",
    y="Nationality",
    color="Age group",
    orientation="h",
    barmode="group",
    color_discrete_sequence=["#1B2A4A", "#2E86AB", "#A8D5E2"],
    labels={"pct": "% within nationality", "Nationality": ""},
    category_orders={"Age group": AGE_ORDER},
    hover_data={"population": ":,d"},
)
fig_age.update_layout(
    height=260,
    margin={"t": 10, "b": 10, "l": 10, "r": 10},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#F7F5F2",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, title=""),
    xaxis=dict(title="% within nationality", ticksuffix="%"),
    yaxis=dict(title=""),
)
st.plotly_chart(fig_age, use_container_width=True)
st.caption(
    "Non-Belgians skew younger than Belgians: a larger share falls in the working-age 18–64 band "
    "and a smaller share in the 65+ bracket, reflecting more recent migration patterns."
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Gender breakdown by nationality
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Gender breakdown by nationality")

gender_raw = (
    region_df[
        region_df["Gender"].notna()
        & region_df["Marital Status"].isna()
        & region_df["Age Group"].isna()
        & region_df["Nationality"].notna()
        & region_df["Region"].notna()
    ]
    .groupby(["year", "Nationality", "Gender"])["population"]
    .sum()
    .reset_index()
)

year_g = st.slider(
    "Year",
    int(gender_raw["year"].min()),
    int(gender_raw["year"].max()),
    2024,
    key="gender_year",
)

gender_yr = gender_raw[gender_raw["year"] == year_g].copy()
total_by_nat_g = gender_yr.groupby("Nationality")["population"].transform("sum")
gender_yr["pct"] = (gender_yr["population"] / total_by_nat_g * 100).round(1)

fig_gen = px.bar(
    gender_yr,
    x="pct",
    y="Nationality",
    color="Gender",
    orientation="h",
    barmode="group",
    color_discrete_map={"Men": "#1B2A4A", "Women": "#2E86AB"},
    labels={"pct": "% within nationality", "Nationality": ""},
    hover_data={"population": ":,d"},
)
fig_gen.update_layout(
    height=240,
    margin={"t": 10, "b": 10, "l": 10, "r": 10},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#F7F5F2",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, title=""),
    xaxis=dict(title="% within nationality", ticksuffix="%"),
    yaxis=dict(title=""),
)
st.plotly_chart(fig_gen, use_container_width=True)
st.caption(
    "Non-Belgian men slightly outnumber women nationally, particularly in labour-migration streams. "
    "The Belgian population shows near-parity, with women slightly more numerous due to longevity."
)
