import streamlit as st
import plotly.express as px
import pandas as pd
from utils.data_loader import load_muni, load_geojson, load_region

THEME_CSS = """
<style>
h1 { font-size: 2rem !important; font-weight: 700; }
div[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E2DED8;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
hr { border-color: #E2DED8 !important; margin: 1.25rem 0; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.title("🇧🇪 Belgium Overview")
st.caption("Non-Belgian population share across 581 municipalities · StatBel 1992–2025")

muni = load_muni()
geo = load_geojson()
region_df = load_region()

year = st.slider("Year", 2009, 2025, 2025)

# ── National snapshot ──────────────────────────────────────────────────────────
df_year = muni[muni["year"] == year].copy()
total_pop = int(df_year["total"].sum())
total_etr = int(df_year["ETR"].sum())
pct_nat = total_etr / total_pop * 100

ref_year = max(2009, year - 10)
df_ref = muni[muni["year"] == ref_year]
pct_ref = df_ref["ETR"].sum() / df_ref["total"].sum() * 100

top_muni = df_year.loc[df_year["pct_etr"].idxmax()]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total population", f"{total_pop:,}")
c2.metric(
    "% non-Belgian",
    f"{pct_nat:.1f}%",
    delta=f"{pct_nat - pct_ref:+.1f} pp vs {ref_year}",
)
c3.metric("Highest municipality", top_muni["TX_DESCR_NL"], f"{top_muni['pct_etr']:.1f}%")
c4.metric("National average", f"{pct_nat:.1f}%")

st.divider()

# ── Map controls ───────────────────────────────────────────────────────────────
region_opts = ["All regions"] + sorted(muni["region_en"].dropna().unique())
sel_region = st.radio("Region", region_opts, horizontal=True)

search = st.text_input("Search municipality", "", placeholder="e.g. Gent, Liège, Molenbeek…")

# Filter map data
if sel_region == "All regions":
    df_map = df_year.copy()
else:
    df_map = df_year[df_year["region_en"] == sel_region].copy()

df_map["CD_REFNIS"] = df_map["CD_REFNIS"].astype(str)
df_map["national_avg"] = round(pct_nat, 1)

# ── Choropleth (Blues) ─────────────────────────────────────────────────────────
fig_map = px.choropleth(
    df_map,
    geojson=geo,
    locations="CD_REFNIS",
    featureidkey="properties.NSI_CODE",
    color="pct_etr",
    hover_name="TX_DESCR_NL",
    hover_data={
        "ETR":          ":,d",
        "total":        ":,d",
        "pct_etr":      ":.1f",
        "national_avg": ":.1f",
        "CD_REFNIS":    False,
    },
    color_continuous_scale="Blues",
    range_color=[0, 40],
    labels={
        "pct_etr":      "% non-Belgian",
        "ETR":          "Non-Belgians",
        "total":        "Total population",
        "national_avg": "National avg %",
    },
)
fig_map.update_geos(fitbounds="locations", visible=False)
fig_map.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=560,
    paper_bgcolor="rgba(0,0,0,0)",
    geo=dict(bgcolor="rgba(0,0,0,0)"),
    coloraxis_colorbar=dict(title="% non-Belgian", ticksuffix="%"),
)
st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# ── Bottom row ─────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Top 10 municipalities")
    top10 = (
        df_map.nlargest(10, "pct_etr")[["TX_DESCR_NL", "pct_etr", "ETR", "total"]]
        .copy()
        .sort_values("pct_etr")
    )
    top10.columns = ["Municipality", "pct", "Non-Belgians", "Total"]

    fig_bar = px.bar(
        top10,
        x="pct",
        y="Municipality",
        orientation="h",
        color="pct",
        color_continuous_scale="Blues",
        labels={"pct": "% non-Belgian"},
    )
    fig_bar.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        height=380,
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        yaxis=dict(title="", tickfont=dict(size=11)),
        xaxis=dict(title="% non-Belgian"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("Municipalities with the highest share of non-Belgian residents in the selected year.")

with col_r:
    st.subheader("National trend 1992–2025")
    trend = (
        region_df[
            region_df["Gender"].notna()
            & region_df["Marital Status"].isna()
            & region_df["Age Group"].isna()
            & region_df["Nationality"].notna()
            & region_df["Region"].notna()
        ]
        .groupby(["year", "Nationality"])["population"]
        .sum()
        .reset_index()
    )
    piv = trend.pivot(index="year", columns="Nationality", values="population").reset_index()
    piv.columns.name = None
    piv["pct"] = (piv["non-Belgians"] / (piv["Belgians"] + piv["non-Belgians"]) * 100).round(2)

    fig_trend = px.line(
        piv,
        x="year",
        y="pct",
        labels={"pct": "% non-Belgian", "year": "Year"},
        color_discrete_sequence=["#2E86AB"],
    )
    fig_trend.update_traces(line_width=2.5, mode="lines")
    fig_trend.update_layout(
        hovermode="x unified",
        height=380,
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#E0DDD8", ticksuffix="%"),
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    st.caption(
        "The non-Belgian share has grown from under 9% in 1992 to over 16% today, "
        "driven by EU mobility and increasing non-EU migration."
    )

# ── Municipality search result ─────────────────────────────────────────────────
if search:
    hits = df_map[df_map["TX_DESCR_NL"].str.contains(search, case=False, na=False)]
    st.divider()
    if len(hits):
        st.subheader(f"Results for '{search}'")
        st.dataframe(
            hits[["TX_DESCR_NL", "TX_PROV_DESCR_NL", "BEL", "ETR", "total", "pct_etr"]].rename(
                columns={
                    "TX_DESCR_NL": "Municipality",
                    "TX_PROV_DESCR_NL": "Province",
                    "BEL": "Belgians",
                    "ETR": "Non-Belgians",
                    "total": "Total",
                    "pct_etr": "% Non-Belgian",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No municipalities found.")
