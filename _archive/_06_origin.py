import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.data_loader import load_origin, load_geojson

st.header("🌍 Population by origin group — municipality level")
st.caption(
    "Belgian background / neighbouring countries / EU27 / non-EU27 · "
    "Source: StatBel 2000–2025"
)

origin = load_origin()
geojson = load_geojson()

# ── Controls ─────────────────────────────────────────────────────────────────
LAYERS = {
    "Belgian background":           ("pct_belgian_bg",    "belgian_bg",    "Blues_r"),
    "Neighbouring countries":       ("pct_neighbouring",  "neighbouring",  "Greens"),
    "EU27 foreigners (excl. neigh.)":("pct_eu27",         "eu27",          "Oranges"),
    "Non-EU27 foreigners":          ("pct_non_eu27",       "non_eu27",      "Reds"),
    "All foreigners":               ("pct_all_foreign",   None,            "OrRd"),
}

col_ctrl, col_map = st.columns([1, 3])
with col_ctrl:
    year = st.slider("Year", 2000, 2025, 2024)
    layer_label = st.radio("Show", list(LAYERS.keys()))
    pct_col, abs_col, color_scale = LAYERS[layer_label]
    max_pct = st.slider(
        "Color scale max (%)",
        5, 100,
        {"Belgian background": 95, "All foreigners": 60}.get(layer_label, 40),
    )
    regions = sorted(origin["region_en"].dropna().unique())
    sel_regions = st.multiselect("Filter by region", regions, default=regions)

# ── Map data ─────────────────────────────────────────────────────────────────
df = origin[
    (origin["year"] == year) & origin["region_en"].isin(sel_regions)
].copy()
df["CD_REFNIS"] = df["CD_REFNIS"].astype(str)

hover_data = {
    "total":            ":,",
    "pct_belgian_bg":   ":.1f",
    "pct_neighbouring": ":.1f",
    "pct_eu27":         ":.1f",
    "pct_non_eu27":     ":.1f",
    "CD_REFNIS":        False,
}

fig_map = px.choropleth(
    df,
    geojson=geojson,
    locations="CD_REFNIS",
    featureidkey="properties.NSI_CODE",
    color=pct_col,
    hover_name="TX_DESCR_NL",
    hover_data=hover_data,
    color_continuous_scale=color_scale,
    range_color=[0, max_pct],
    labels={
        pct_col:            f"% {layer_label}",
        "total":            "Total population",
        "pct_belgian_bg":   "% Belgian bg",
        "pct_neighbouring": "% Neighbouring",
        "pct_eu27":         "% EU27",
        "pct_non_eu27":     "% Non-EU27",
    },
)
fig_map.update_geos(fitbounds="locations", visible=False)
fig_map.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=580,
    paper_bgcolor="rgba(0,0,0,0)",
    geo=dict(bgcolor="rgba(0,0,0,0)"),
)

with col_map:
    st.plotly_chart(fig_map, use_container_width=True)

# ── Top-10 table ──────────────────────────────────────────────────────────────
st.divider()
col_t1, col_t2 = st.columns(2)

with col_t1:
    st.subheader(f"Top 10 — highest {layer_label} share ({year})")
    top10 = df.nlargest(10, pct_col)[
        ["TX_DESCR_NL", "TX_PROV_DESCR_NL", "belgian_bg", "neighbouring", "eu27", "non_eu27", "total", pct_col]
    ].copy()
    top10.columns = ["Municipality", "Province", "Belgian bg", "Neighbouring", "EU27", "Non-EU27", "Total", f"% {layer_label}"]
    st.dataframe(top10, use_container_width=True, hide_index=True)

with col_t2:
    st.subheader(f"Top 10 — highest Non-EU27 share ({year})")
    top_noneu = df.nlargest(10, "pct_non_eu")[
        ["TX_DESCR_NL", "TX_PROV_DESCR_NL", "non_eu27", "total", "pct_non_eu"]
    ].copy()
    top_noneu.columns = ["Municipality", "Province", "Non-EU27", "Total", "% Non-EU27"]
    st.dataframe(top_noneu, use_container_width=True, hide_index=True)

# ── Composition breakdown for selected year ───────────────────────────────────
st.divider()
st.subheader("National composition breakdown over time")

# Aggregate nationally per year
nat = (
    origin.groupby("year")[["belgian_bg", "neighbouring", "eu27", "non_eu27", "total"]]
    .sum()
    .reset_index()
)
for col in ["belgian_bg", "neighbouring", "eu27", "non_eu27"]:
    nat[f"pct_{col}"] = (nat[col] / nat["total"] * 100).round(2)

nat_long = nat.melt(
    id_vars="year",
    value_vars=["pct_belgian_bg", "pct_neighbouring", "pct_eu27", "pct_non_eu27"],
    var_name="group",
    value_name="pct",
)
nat_long["group"] = nat_long["group"].map({
    "pct_belgian_bg":   "Belgian background",
    "pct_neighbouring": "Neighbouring countries",
    "pct_eu27":         "EU27 (excl. neigh.)",
    "pct_non_eu27":     "Non-EU27",
})

fig_nat = px.area(
    nat_long,
    x="year", y="pct", color="group",
    color_discrete_map={
        "Belgian background":      "#1f77b4",
        "Neighbouring countries":  "#2ca02c",
        "EU27 (excl. neigh.)":    "#ff7f0e",
        "Non-EU27":               "#d62728",
    },
    labels={"pct": "Share (%)", "year": "Year", "group": "Origin group"},
    title="National population share by origin group 2000–2025",
)
fig_nat.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig_nat, use_container_width=True)

# ── Municipality search ───────────────────────────────────────────────────────
st.divider()
search = st.text_input("Search municipality (time series)")
if search:
    hits = origin[origin["TX_DESCR_NL"].str.contains(search, case=False, na=False)]
    munis = hits["TX_DESCR_NL"].unique()
    if len(munis) == 0:
        st.warning("No municipalities found.")
    else:
        sel_muni = st.selectbox("Select municipality", sorted(munis)) if len(munis) > 1 else munis[0]
        muni_ts = origin[origin["TX_DESCR_NL"] == sel_muni].sort_values("year")
        ts_long = muni_ts.melt(
            id_vars="year",
            value_vars=["pct_belgian_bg", "pct_neighbouring", "pct_eu27", "pct_non_eu27"],
            var_name="group", value_name="pct",
        )
        ts_long["group"] = ts_long["group"].map({
            "pct_belgian_bg":   "Belgian background",
            "pct_neighbouring": "Neighbouring countries",
            "pct_eu27":         "EU27 (excl. neigh.)",
            "pct_non_eu27":     "Non-EU27",
        })
        fig_ts = px.area(
            ts_long, x="year", y="pct", color="group",
            color_discrete_map={
                "Belgian background":      "#1f77b4",
                "Neighbouring countries":  "#2ca02c",
                "EU27 (excl. neigh.)":    "#ff7f0e",
                "Non-EU27":               "#d62728",
            },
            labels={"pct": "Share (%)", "year": "Year", "group": "Origin group"},
            title=f"Origin composition over time — {sel_muni}",
        )
        fig_ts.update_layout(hovermode="x unified")
        st.plotly_chart(fig_ts, use_container_width=True)

        st.dataframe(
            muni_ts[["year","belgian_bg","neighbouring","eu27","non_eu27","total",
                      "pct_belgian_bg","pct_neighbouring","pct_eu27","pct_non_eu27"]].sort_values("year"),
            use_container_width=True, hide_index=True
        )
