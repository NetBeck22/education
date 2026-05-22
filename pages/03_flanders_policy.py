import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.data_loader import load_newcomers, load_origin, load_geojson, load_flanders_youth

st.markdown("""
<style>
h1 { font-size: 2rem !important; font-weight: 700; }
hr { border-color: #E2DED8 !important; margin: 1.25rem 0; }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Flanders Policy Insights")
st.caption(
    "Language integration pressure · Youth & school pressure · Newcomer flows — "
    "Flemish municipalities only · Sources: Agentschap Integratie & Inburgering, StatBel, provincies.incijfers.be"
)

newcomers  = load_newcomers()
origin     = load_origin()
geojson    = load_geojson()
youth      = load_flanders_youth()

origin_vl  = origin[origin["TX_RGN_DESCR_NL"] == "Vlaams Gewest"].copy()
origin_vl["CD_REFNIS"] = origin_vl["CD_REFNIS"].astype(str)

YEARS = list(range(2014, 2025))

# ── Shared choropleth helper ───────────────────────────────────────────────────
def make_choropleth(df, color_col, label, color_scale="Blues", range_max=None,
                    hover_extra=None, height=520):
    hover = {color_col: ":.2f", "CD_REFNIS": False}
    if hover_extra:
        hover.update(hover_extra)
    if range_max is None:
        range_max = float(df[color_col].quantile(0.95))
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="CD_REFNIS",
        featureidkey="properties.NSI_CODE",
        color=color_col,
        hover_name="TX_DESCR_NL",
        hover_data=hover,
        color_continuous_scale=color_scale,
        range_color=[0, range_max],
        labels={color_col: label},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def minmax(s):
    lo, hi = s.min(), s.max()
    return ((s - lo) / (hi - lo) * 100).round(1) if hi > lo else s * 0


def province_mean(df, value_col):
    return (
        df.groupby("TX_PROV_DESCR_NL", as_index=False)[value_col]
        .mean()
        .sort_values(value_col, ascending=False)
    )


def add_play_choropleth(df, color_col, label, color_scale="Blues", range_max=None, height=520):
    if range_max is None:
        range_max = float(df[color_col].quantile(0.95))
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="CD_REFNIS",
        featureidkey="properties.NSI_CODE",
        color=color_col,
        animation_frame="year",
        hover_name="TX_DESCR_NL",
        hover_data={color_col: ":.2f", "TX_PROV_DESCR_NL": True, "CD_REFNIS": False},
        color_continuous_scale=color_scale,
        range_color=[0, range_max],
        labels={color_col: label, "year": "Year"},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


tab1, tab2, tab3 = st.tabs([
    "🗣️ Language Integration Needs",
    "👶 Youth & School Pressure",
    "📈 Newcomer Flows",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Language Integration Needs
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Integration Pressure Score — Flemish municipalities")

    col_ctrl, col_main = st.columns([1, 3])
    with col_ctrl:
        score_year = st.select_slider("Year", options=YEARS, value=2024, key="t1_year")
        max_scale  = st.slider("Color scale max (score)", 20, 100, 70, key="t1_max")
        st.info(
            "**Score = avg of 3 normalised indicators (0–100):**\n\n"
            "1. % non-EU nationality\n"
            "2. Newcomers per 1,000 residents\n"
            "3. % pupils with home language ≠ Dutch "
            "(avg primary + secondary education)"
        )

    o_yr = origin_vl[origin_vl["year"] == score_year][
        ["CD_REFNIS", "TX_DESCR_NL", "TX_PROV_DESCR_NL", "pct_non_eu27"]
    ].copy()
    n_yr = newcomers[newcomers["year"] == score_year][
        ["CD_REFNIS", "nieuwkomers_per_1000"]
    ].copy()
    y_yr = youth[youth["year"] == score_year][
        ["CD_REFNIS", "pct_geen_nl_avg", "pct_bo_geen_nl", "pct_so_geen_nl"]
    ].copy()

    merged = o_yr.merge(n_yr, on="CD_REFNIS", how="left").merge(y_yr, on="CD_REFNIS", how="left")
    merged["score_niet_eu"]   = minmax(merged["pct_non_eu27"])
    merged["score_nw_rate"]   = minmax(merged["nieuwkomers_per_1000"])
    merged["score_school_nl"] = minmax(merged["pct_geen_nl_avg"])
    merged["integration_score"] = (
        merged[["score_niet_eu", "score_nw_rate", "score_school_nl"]].mean(axis=1).round(1)
    )

    with col_main:
        fig1 = make_choropleth(
            merged, "integration_score", "Integration pressure score",
            color_scale="Blues", range_max=max_scale,
            hover_extra={
                "pct_non_eu27":         ":.1f",
                "nieuwkomers_per_1000": ":.1f",
                "pct_geen_nl_avg":      ":.1f",
            },
        )
        st.plotly_chart(fig1, use_container_width=True)

    with st.expander("Play 2014-2024: integration pressure over time", expanded=False):
        frames = []
        for yr in YEARS:
            o_all = origin_vl[origin_vl["year"] == yr][
                ["CD_REFNIS", "TX_DESCR_NL", "TX_PROV_DESCR_NL", "pct_non_eu27"]
            ].copy()
            n_all = newcomers[newcomers["year"] == yr][
                ["CD_REFNIS", "nieuwkomers_per_1000"]
            ].copy()
            y_all = youth[youth["year"] == yr][
                ["CD_REFNIS", "pct_geen_nl_avg"]
            ].copy()
            frame = o_all.merge(n_all, on="CD_REFNIS", how="left").merge(y_all, on="CD_REFNIS", how="left")
            frame["score_niet_eu"] = minmax(frame["pct_non_eu27"])
            frame["score_nw_rate"] = minmax(frame["nieuwkomers_per_1000"])
            frame["score_school_nl"] = minmax(frame["pct_geen_nl_avg"])
            frame["integration_score"] = (
                frame[["score_niet_eu", "score_nw_rate", "score_school_nl"]].mean(axis=1).round(1)
            )
            frame["year"] = yr
            frames.append(frame)
        score_anim = pd.concat(frames, ignore_index=True)
        st.plotly_chart(
            add_play_choropleth(
                score_anim, "integration_score", "Integration pressure score",
                color_scale="Blues", range_max=max_scale, height=560
            ),
            use_container_width=True,
        )
        st.caption("Use the play button to scan the full available 2014-2024 scope.")

    st.divider()
    st.subheader(f"Top 20 — highest integration pressure ({score_year})")
    top20 = (
        merged.nlargest(20, "integration_score")
        [["TX_DESCR_NL", "TX_PROV_DESCR_NL",
          "pct_non_eu27", "nieuwkomers_per_1000", "pct_geen_nl_avg", "integration_score"]]
        .rename(columns={
            "TX_DESCR_NL":          "Municipality",
            "TX_PROV_DESCR_NL":     "Province",
            "pct_non_eu27":         "% non-EU",
            "nieuwkomers_per_1000": "Newcomers / 1,000",
            "pct_geen_nl_avg":      "% non-Dutch home lang. (primary+secondary)",
            "integration_score":    "Pressure score",
        })
    )
    st.dataframe(top20, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Score component breakdown — top 20")
    top20_comp = merged.nlargest(20, "integration_score").sort_values("integration_score")
    fig_comp = go.Figure()
    for col, label, color in [
        ("score_niet_eu",   "% non-EU (normalised)",                          "#1B2A4A"),
        ("score_nw_rate",   "Newcomers / 1,000 residents (normalised)",        "#2E86AB"),
        ("score_school_nl", "% non-Dutch home lang. primary+secondary (norm)", "#A8D5E2"),
    ]:
        fig_comp.add_bar(
            y=top20_comp["TX_DESCR_NL"], x=top20_comp[col] / 3,
            name=label, orientation="h", marker_color=color,
        )
    fig_comp.update_layout(
        barmode="stack",
        xaxis_title="Contribution to score (each max 33.3)",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin={"l": 0, "r": 10, "t": 40, "b": 0},
        height=480,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
    )
    st.plotly_chart(fig_comp, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Youth & School Pressure
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Education pressure in Flanders, 2014-2024")
    st.markdown(
        "This section keeps the education story to three visuals. The goal is to show where "
        "education pressure is structurally highest, how it moved between 2014 and 2024, and "
        "which municipalities policy makers should look at first. The school-pressure score is "
        "a simple index: home language in primary and secondary education carries the most weight, "
        "then youth with non-Belgian origin, then newcomer intensity. It should be read as a "
        "planning signal, not as a judgement of school quality."
    )

    edu_frames = []
    for yr in YEARS:
        y_yr = youth[youth["year"] == yr].copy()
        n_yr = newcomers[newcomers["year"] == yr][
            ["CD_REFNIS", "nieuwkomers_per_1000"]
        ].copy()
        o_yr = origin_vl[origin_vl["year"] == yr][
            ["CD_REFNIS", "pct_non_eu27"]
        ].copy()
        frame = y_yr.merge(n_yr, on="CD_REFNIS", how="left").merge(o_yr, on="CD_REFNIS", how="left")
        frame["pct_geen_nl_avg"] = frame[["pct_bo_geen_nl", "pct_so_geen_nl"]].mean(axis=1)
        edu_frames.append(frame)

    edu_all = pd.concat(edu_frames, ignore_index=True)
    edu_all["school_pressure_score"] = (
        minmax(edu_all["pct_geen_nl_avg"]).fillna(0) * 0.45
        + minmax(edu_all["pct_youth_niet_belg"]).fillna(0) * 0.35
        + minmax(edu_all["nieuwkomers_per_1000"].fillna(0)) * 0.20
    ).round(1)

    edu_2014 = edu_all[edu_all["year"] == 2014][
        ["CD_REFNIS", "school_pressure_score", "pct_geen_nl_avg", "pct_youth_niet_belg"]
    ].rename(columns={
        "school_pressure_score": "score_2014",
        "pct_geen_nl_avg": "home_language_2014",
        "pct_youth_niet_belg": "youth_origin_2014",
    })
    edu_2024 = edu_all[edu_all["year"] == 2024].merge(edu_2014, on="CD_REFNIS", how="left")
    edu_2024["score_change_2014_2024"] = (edu_2024["school_pressure_score"] - edu_2024["score_2014"]).round(1)
    edu_2024["home_language_change_2014_2024"] = (edu_2024["pct_geen_nl_avg"] - edu_2024["home_language_2014"]).round(1)
    edu_2024["youth_origin_change_2014_2024"] = (edu_2024["pct_youth_niet_belg"] - edu_2024["youth_origin_2014"]).round(1)

    province_year = (
        edu_all.groupby(["year", "TX_PROV_DESCR_NL"], as_index=False)
        .agg(
            school_pressure_score=("school_pressure_score", "mean"),
            pct_geen_nl_avg=("pct_geen_nl_avg", "mean"),
            pct_youth_niet_belg=("pct_youth_niet_belg", "mean"),
            newcomers_per_1000=("nieuwkomers_per_1000", "mean"),
        )
    )
    province_2014 = province_year[province_year["year"] == 2014][
        ["TX_PROV_DESCR_NL", "school_pressure_score"]
    ].rename(columns={"school_pressure_score": "score_2014"})
    province_2024 = province_year[province_year["year"] == 2024].merge(province_2014, on="TX_PROV_DESCR_NL", how="left")
    province_2024["score_change"] = (
        province_2024["school_pressure_score"] - province_2024["score_2014"]
    ).round(1)

    top_province = province_2024.sort_values("school_pressure_score", ascending=False).iloc[0]
    fastest_province = province_2024.sort_values("score_change", ascending=False).iloc[0]
    top_muni = edu_2024.sort_values("school_pressure_score", ascending=False).iloc[0]
    fastest_muni = edu_2024.sort_values("score_change_2014_2024", ascending=False).iloc[0]

    st.markdown(
        f"In 2024, **{top_province['TX_PROV_DESCR_NL']}** has the highest average education-pressure "
        f"score. The strongest increase since 2014 is in **{fastest_province['TX_PROV_DESCR_NL']}**. "
        f"At municipality level, **{top_muni['TX_DESCR_NL']}** is the highest-pressure case in 2024, "
        f"while **{fastest_muni['TX_DESCR_NL']}** shows the sharpest increase over the full 2014-2024 period. "
        "For policy, that means the story is not only about the biggest cities today. It is also about "
        "places where school-language needs and youth diversity are rising quickly enough that capacity "
        "planning should start before pressure becomes visible in outcomes."
    )

    st.divider()
    st.subheader("1. Province picture: where is pressure highest, and how did it move?")
    st.markdown(
        "This first chart is the easiest one to present. It keeps the view at province level and uses "
        "the play button to move year by year from 2014 to 2024. A rising province score means that "
        "more municipalities in that province combine non-Dutch home-language signals, a more diverse "
        "youth population, and newcomer intake."
    )
    fig_province_play = px.bar(
        province_year.sort_values(["year", "school_pressure_score"]),
        x="school_pressure_score",
        y="TX_PROV_DESCR_NL",
        orientation="h",
        color="school_pressure_score",
        animation_frame="year",
        range_x=[0, max(100, float(province_year["school_pressure_score"].max()) * 1.05)],
        color_continuous_scale="YlOrRd",
        text="school_pressure_score",
        labels={
            "school_pressure_score": "Education pressure score",
            "TX_PROV_DESCR_NL": "Province",
            "year": "Year",
        },
    )
    fig_province_play.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig_province_play.update_layout(
        height=430,
        coloraxis_showscale=False,
        margin={"l": 0, "r": 20, "t": 20, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
    )
    st.plotly_chart(fig_province_play, use_container_width=True)

    st.markdown(
        "The policy reading is straightforward: provinces with high levels need structural support, "
        "while provinces with the fastest growth need earlier planning. This distinction matters because "
        "a province can still be below the top level but already be moving in the direction of higher "
        "language-support demand."
    )

    st.divider()
    st.subheader("2. Municipality map: where is pressure concentrated?")
    st.markdown(
        "The map adds the local layer. The play button is useful here because it shows whether pressure "
        "is stable around the same municipalities or spreading into new areas. Darker municipalities are "
        "not 'worse'; they are places where schools may need more language support, parent communication, "
        "transition guidance and coordination with integration services."
    )
    fig_edu_map = add_play_choropleth(
        edu_all,
        "school_pressure_score",
        "Education pressure score",
        color_scale="YlOrRd",
        range_max=max(70, float(edu_all["school_pressure_score"].quantile(0.98))),
        height=590,
    )
    st.plotly_chart(fig_edu_map, use_container_width=True)

    st.markdown(
        f"By 2024, the highest municipal score is in **{top_muni['TX_DESCR_NL']}**. "
        "When a municipality stays dark for several years, the response should be structural: stable "
        "language-support capacity, multilingual parent outreach, and predictable cooperation between "
        "schools and local services. When a municipality becomes darker only recently, the response is "
        "more about early warning and capacity planning."
    )

    st.divider()
    st.subheader("3. Municipality follow-up: which places should policy makers discuss first?")
    st.markdown(
        "The final chart turns the map into an action list. Choose a province and compare the highest "
        "pressure municipalities across all years from 2014 to 2024. This keeps the discussion concrete: "
        "which places need sustained support, and which places are rising fast?"
    )
    province_options = province_2024.sort_values("school_pressure_score", ascending=False)["TX_PROV_DESCR_NL"].tolist()
    selected_edu_province = st.selectbox(
        "Province",
        province_options,
        key="t2_three_graph_province",
    )
    province_2024_munis = (
        edu_2024[edu_2024["TX_PROV_DESCR_NL"] == selected_edu_province]
        .sort_values("school_pressure_score", ascending=False)
    )
    default_munis = province_2024_munis.head(8)["TX_DESCR_NL"].tolist()
    selected_munis = st.multiselect(
        "Municipalities to compare",
        province_2024_munis["TX_DESCR_NL"].tolist(),
        default=default_munis,
        key="t2_three_graph_munis",
    )
    if selected_munis:
        muni_trend = edu_all[edu_all["TX_DESCR_NL"].isin(selected_munis)].copy()
        fig_muni_trend = px.line(
            muni_trend,
            x="year",
            y="school_pressure_score",
            color="TX_DESCR_NL",
            markers=True,
            labels={
                "year": "Year",
                "school_pressure_score": "Education pressure score",
                "TX_DESCR_NL": "Municipality",
            },
        )
        fig_muni_trend.update_layout(
            height=470,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin={"l": 0, "r": 10, "t": 45, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
        )
        st.plotly_chart(fig_muni_trend, use_container_width=True)

        selected_summary = edu_2024[edu_2024["TX_DESCR_NL"].isin(selected_munis)].sort_values(
            "score_change_2014_2024", ascending=False
        )
        fastest_selected = selected_summary.iloc[0]
        highest_selected = selected_summary.sort_values("school_pressure_score", ascending=False).iloc[0]
        st.markdown(
            f"For **{selected_edu_province}**, the selected municipalities show two different policy questions. "
            f"**{highest_selected['TX_DESCR_NL']}** has the highest 2024 pressure among the selected places, "
            f"so it is a candidate for sustained support. **{fastest_selected['TX_DESCR_NL']}** rose the most "
            f"between 2014 and 2024, so it is a candidate for early capacity planning. Together, these two "
            "readings help avoid a common mistake: only funding current hotspots while missing municipalities "
            "where demand is building."
        )
    else:
        st.info("Select at least one municipality.")


# TAB 3 — Newcomer Flows
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Newcomer flows — Flemish municipalities")
    st.caption("Newcomers registered via integration trajectory · 2014–2024")

    col_ctrl3, col_map3 = st.columns([1, 3])
    with col_ctrl3:
        y3 = st.select_slider("Year", options=YEARS, value=2024, key="t3_year")
        map_metric = st.radio(
            "Map metric",
            [
                "Newcomers / 1,000 residents",
                "Total newcomers",
                "Non-EU newcomers / 1,000",
            ],
            key="t3_metric",
        )
        max_map3 = st.slider("Color scale max", 5, 100, 30, key="t3_max")

    metric_col = {
        "Newcomers / 1,000 residents": "nieuwkomers_per_1000",
        "Total newcomers":             "nieuwkomers",
        "Non-EU newcomers / 1,000":    "nieuwkomers_niet_eu_per_1000",
    }[map_metric]

    df3 = newcomers[newcomers["year"] == y3].copy()

    with col_map3:
        fig3 = make_choropleth(
            df3, metric_col, map_metric,
            color_scale="Blues", range_max=max_map3,
            hover_extra={
                "nieuwkomers":          ":.0f",
                "nieuwkomers_niet_eu":  ":.0f",
                "nieuwkomers_per_1000": ":.1f",
            },
        )
        st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Play 2014-2024: newcomer map over time", expanded=False):
        st.plotly_chart(
            add_play_choropleth(
                newcomers, metric_col, map_metric,
                color_scale="Blues", range_max=max_map3, height=560
            ),
            use_container_width=True,
        )

    st.subheader(f"Province overview — three newcomer measures ({y3})")
    province_newcomers = (
        df3.groupby("TX_PROV_DESCR_NL", as_index=False)
        .agg(
            newcomers_per_1000=("nieuwkomers_per_1000", "mean"),
            non_eu_per_1000=("nieuwkomers_niet_eu_per_1000", "mean"),
            total_newcomers=("nieuwkomers", "sum"),
        )
        .sort_values("newcomers_per_1000", ascending=False)
    )
    prov_long = province_newcomers.melt(
        id_vars="TX_PROV_DESCR_NL",
        value_vars=["newcomers_per_1000", "non_eu_per_1000", "total_newcomers"],
        var_name="measure",
        value_name="value",
    )
    prov_long["measure"] = prov_long["measure"].map({
        "newcomers_per_1000": "Newcomers / 1,000",
        "non_eu_per_1000": "Non-EU / 1,000",
        "total_newcomers": "Total newcomers",
    })
    fig_prov_newcomers = px.bar(
        prov_long,
        x="TX_PROV_DESCR_NL",
        y="value",
        color="measure",
        barmode="group",
        labels={"TX_PROV_DESCR_NL": "Province", "value": "Value", "measure": "Measure"},
        color_discrete_map={
            "Newcomers / 1,000": "#2E86AB",
            "Non-EU / 1,000": "#1B2A4A",
            "Total newcomers": "#E09F3E",
        },
    )
    fig_prov_newcomers.update_layout(
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin={"l": 0, "r": 10, "t": 40, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
    )
    st.plotly_chart(fig_prov_newcomers, use_container_width=True)

    st.divider()
    st.subheader(f"EU vs non-EU newcomers — Top 20 municipalities ({y3})")
    top20_nw = (
        df3.nlargest(20, "nieuwkomers")
        [["TX_DESCR_NL", "nieuwkomers_eu", "nieuwkomers_niet_eu"]]
        .sort_values("nieuwkomers_niet_eu", ascending=True)
    )
    fig_compare = go.Figure()
    fig_compare.add_bar(
        y=top20_nw["TX_DESCR_NL"], x=top20_nw["nieuwkomers_eu"],
        name="EU newcomers", orientation="h", marker_color="#2E86AB",
    )
    fig_compare.add_bar(
        y=top20_nw["TX_DESCR_NL"], x=top20_nw["nieuwkomers_niet_eu"],
        name="Non-EU newcomers", orientation="h", marker_color="#1B2A4A",
    )
    fig_compare.update_layout(
        barmode="stack",
        xaxis_title="Number of newcomers",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin={"l": 0, "r": 10, "t": 40, "b": 0},
        height=480,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.divider()
    st.subheader("Newcomer flow over time — municipality comparison")
    all_nw_munis = sorted(newcomers["TX_DESCR_NL"].dropna().unique())
    defaults3 = [m for m in ["Antwerpen", "Gent", "Leuven", "Mechelen", "Aalst"]
                 if m in all_nw_munis]
    sel_flow = st.multiselect(
        "Select municipalities", all_nw_munis,
        default=defaults3 or all_nw_munis[:5],
        key="t3_flow_munis",
    )
    flow_metric = st.radio(
        "Metric",
        ["nieuwkomers_per_1000", "nieuwkomers", "nieuwkomers_niet_eu"],
        format_func=lambda x: {
            "nieuwkomers_per_1000": "Newcomers / 1,000 residents",
            "nieuwkomers":          "Total newcomers",
            "nieuwkomers_niet_eu":  "Non-EU newcomers",
        }[x],
        horizontal=True,
        key="t3_flow_metric",
    )
    FLOW_LABELS = {
        "nieuwkomers_per_1000": "Newcomers / 1,000 residents",
        "nieuwkomers":          "Total newcomers",
        "nieuwkomers_niet_eu":  "Non-EU newcomers",
    }
    if sel_flow:
        flow_df = newcomers[newcomers["TX_DESCR_NL"].isin(sel_flow)].copy()
        fig_flow = px.line(
            flow_df, x="year", y=flow_metric, color="TX_DESCR_NL",
            labels={
                flow_metric:    FLOW_LABELS[flow_metric],
                "year":         "Year",
                "TX_DESCR_NL":  "Municipality",
            },
            markers=True,
        )
        fig_flow.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_flow, use_container_width=True)
    else:
        st.info("Select at least one municipality.")
