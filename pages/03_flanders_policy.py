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
    st.markdown(
        "**Storyline.** This tab follows the education pressure chain: migration and origin "
        "patterns shape the youth population, the youth population shows up in classrooms, "
        "and schools feel pressure where language needs, youth diversity and newcomer flows overlap."
    )

    col_ctrl2, col_map2 = st.columns([1, 3])
    with col_ctrl2:
        y2 = st.select_slider("Year", options=YEARS, value=2024, key="t2_year")
        map_layer = st.radio(
            "Map layer",
            [
                "% youth non-Belgian origin",
                "% primary ed. non-Dutch home language",
                "% secondary ed. non-Dutch home language",
            ],
            key="t2_layer",
        )
        max_pct2 = st.slider("Color scale max (%)", 5, 80, 30, key="t2_max")

    layer_col = {
        "% youth non-Belgian origin":                  ("pct_youth_niet_belg", "% youth non-Belgian origin",              "Blues"),
        "% primary ed. non-Dutch home language":       ("pct_bo_geen_nl",      "% primary ed. non-Dutch home lang.",      "Blues"),
        "% secondary ed. non-Dutch home language":     ("pct_so_geen_nl",      "% secondary ed. non-Dutch home lang.",    "Blues"),
    }[map_layer]
    color_col2, color_label2, color_scale2 = layer_col

    df2 = youth[youth["year"] == y2].copy()

    st.subheader(f"{map_layer} — Flemish municipalities ({y2})")
    with col_map2:
        fig_map2 = make_choropleth(
            df2, color_col2, color_label2, color_scale=color_scale2, range_max=max_pct2,
            hover_extra={
                "pct_youth_niet_belg": ":.1f",
                "pct_bo_geen_nl":      ":.1f",
                "pct_so_geen_nl":      ":.1f",
            },
        )
        st.plotly_chart(fig_map2, use_container_width=True)

    st.divider()
    col_bar2, col_trend2 = st.columns([1, 1])

    with col_bar2:
        st.subheader(f"Top 20 — {map_layer} ({y2})")
        bar20 = df2.nlargest(20, color_col2).sort_values(color_col2)
        fig_bar2 = px.bar(
            bar20, x=color_col2, y="TX_DESCR_NL", orientation="h",
            labels={color_col2: color_label2, "TX_DESCR_NL": ""},
            color=color_col2, color_continuous_scale=color_scale2, text_auto=".1f",
        )
        fig_bar2.update_layout(
            coloraxis_showscale=False,
            margin={"l": 0, "r": 10, "t": 10, "b": 0},
            height=480,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
        )
        st.plotly_chart(fig_bar2, use_container_width=True)

    with col_trend2:
        st.subheader("Trend 2014–2024")
        top5_default = df2.nlargest(5, color_col2)["TX_DESCR_NL"].tolist()
        all_munis2 = sorted(youth["TX_DESCR_NL"].dropna().unique())
        sel_munis2 = st.multiselect(
            "Select municipalities", all_munis2, default=top5_default, key="t2_munis"
        )
        if sel_munis2:
            trend_df = youth[youth["TX_DESCR_NL"].isin(sel_munis2)].copy()
            fig_trend2 = px.line(
                trend_df, x="year", y=color_col2, color="TX_DESCR_NL",
                labels={color_col2: color_label2, "year": "Year", "TX_DESCR_NL": "Municipality"},
                markers=True,
            )
            fig_trend2.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin={"t": 40, "b": 0},
                height=420,
            )
            st.plotly_chart(fig_trend2, use_container_width=True)
        else:
            st.info("Select at least one municipality.")

    st.divider()
    st.subheader(f"Youth origin breakdown — {y2}")
    st.caption("% of total 0–24 population by origin group — select up to 20 municipalities")
    breakdown_munis = st.multiselect(
        "Municipalities for breakdown chart",
        all_munis2,
        default=(top5_default + ["Gent", "Antwerpen", "Leuven"])[:8],
        key="t2_breakdown",
    )
    if breakdown_munis:
        bd = df2[df2["TX_DESCR_NL"].isin(breakdown_munis)].copy()
        bd_long = bd.melt(
            id_vars="TX_DESCR_NL",
            value_vars=["pct_youth_maghreb", "pct_youth_turks",
                        "pct_youth_oost_eu", "pct_youth_afrik"],
            var_name="origin_group", value_name="pct",
        )
        bd_long["origin_group"] = bd_long["origin_group"].map({
            "pct_youth_maghreb": "Maghreb",
            "pct_youth_turks":   "Turkish",
            "pct_youth_oost_eu": "Eastern European (non-EU)",
            "pct_youth_afrik":   "Other African",
        })
        order = bd.sort_values("pct_youth_niet_belg", ascending=False)["TX_DESCR_NL"].tolist()
        fig_bd = px.bar(
            bd_long, x="TX_DESCR_NL", y="pct", color="origin_group",
            category_orders={"TX_DESCR_NL": order},
            labels={"pct": "% of 0–24 yr population", "TX_DESCR_NL": "", "origin_group": "Origin group"},
            color_discrete_map={
                "Maghreb":                  "#1B2A4A",
                "Turkish":                  "#2E86AB",
                "Eastern European (non-EU)":"#5BA4CF",
                "Other African":            "#A8D5E2",
            },
            barmode="group",
        )
        fig_bd.update_layout(
            xaxis_tickangle=-30,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin={"t": 50, "b": 80},
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
        )
        st.plotly_chart(fig_bd, use_container_width=True)
    else:
        st.info("Select at least one municipality.")


# ══════════════════════════════════════════════════════════════════════════════

    st.divider()
    st.subheader("Education pressure linked to migration")
    st.markdown(
        "The school pressure view combines four signals into one readable policy lens: "
        "primary home language, secondary home language, youth with non-Belgian origin, "
        "and newcomer intensity. It does not replace the separate indicators above; it "
        "helps spot municipalities where several education needs arrive together."
    )

    edu_n = newcomers[newcomers["year"] == y2][
        ["CD_REFNIS", "nieuwkomers", "nieuwkomers_per_1000", "nieuwkomers_niet_eu_per_1000"]
    ].copy()
    edu_o = origin_vl[origin_vl["year"] == y2][
        ["CD_REFNIS", "pct_non_eu27"]
    ].copy()
    edu = df2.merge(edu_n, on="CD_REFNIS", how="left").merge(edu_o, on="CD_REFNIS", how="left")
    edu["pct_geen_nl_avg"] = edu[["pct_bo_geen_nl", "pct_so_geen_nl"]].mean(axis=1)
    edu["school_pressure_score"] = (
        minmax(edu["pct_bo_geen_nl"]).fillna(0) * 0.35
        + minmax(edu["pct_so_geen_nl"]).fillna(0) * 0.35
        + minmax(edu["pct_youth_niet_belg"]).fillna(0) * 0.20
        + minmax(edu["nieuwkomers_per_1000"].fillna(0)) * 0.10
    ).round(1)
    edu["primary_secondary_gap"] = (edu["pct_bo_geen_nl"] - edu["pct_so_geen_nl"]).round(1)

    top_school = edu.loc[edu["school_pressure_score"].idxmax()]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg school pressure", f"{edu['school_pressure_score'].mean():.1f}/100")
    c2.metric("Highest pressure", top_school["TX_DESCR_NL"], f"{top_school['school_pressure_score']:.1f}/100")
    c3.metric("Avg home language signal", f"{edu['pct_geen_nl_avg'].mean():.1f}%")
    c4.metric("Avg newcomers", f"{edu['nieuwkomers_per_1000'].mean():.1f}/1,000")

    col_scatter_edu, col_top_edu = st.columns([1.15, 0.85])
    with col_scatter_edu:
        st.markdown("**Migration link.** Each point is a municipality; bigger points have higher school pressure.")
        x_metric_edu = st.radio(
            "Migration indicator",
            ["pct_youth_niet_belg", "nieuwkomers_per_1000", "pct_non_eu27"],
            format_func=lambda x: {
                "pct_youth_niet_belg": "Youth non-Belgian origin",
                "nieuwkomers_per_1000": "Newcomers / 1,000 residents",
                "pct_non_eu27": "% non-EU nationality",
            }[x],
            horizontal=True,
            key="t2_edu_x",
        )
        corr_edu = edu[[x_metric_edu, "pct_geen_nl_avg"]].corr().iloc[0, 1]
        fig_edu_scatter = px.scatter(
            edu,
            x=x_metric_edu,
            y="pct_geen_nl_avg",
            size="school_pressure_score",
            color="TX_PROV_DESCR_NL",
            hover_name="TX_DESCR_NL",
            hover_data={
                "pct_bo_geen_nl": ":.1f",
                "pct_so_geen_nl": ":.1f",
                "school_pressure_score": ":.1f",
                "nieuwkomers_per_1000": ":.1f",
                "pct_non_eu27": ":.1f",
            },
            labels={
                "pct_youth_niet_belg": "% youth non-Belgian origin",
                "nieuwkomers_per_1000": "Newcomers / 1,000 residents",
                "pct_non_eu27": "% non-EU nationality",
                "pct_geen_nl_avg": "% pupils with non-Dutch home language",
                "TX_PROV_DESCR_NL": "Province",
            },
            color_discrete_sequence=["#164B60", "#B23A48", "#E09F3E", "#3A7D44", "#7D4E8D"],
        )
        fig_edu_scatter.update_layout(
            height=470,
            margin={"l": 0, "r": 10, "t": 20, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_edu_scatter, use_container_width=True)
        st.caption(f"Correlation with the school home-language signal in {y2}: {corr_edu:.2f}.")

    with col_top_edu:
        st.markdown("**Top pressure municipalities.** Color shows the actual home-language signal.")
        top_edu = edu.nlargest(20, "school_pressure_score").sort_values("school_pressure_score")
        fig_edu_top = px.bar(
            top_edu,
            x="school_pressure_score",
            y="TX_DESCR_NL",
            orientation="h",
            color="pct_geen_nl_avg",
            color_continuous_scale="YlOrRd",
            text_auto=".1f",
            labels={
                "school_pressure_score": "School pressure score",
                "TX_DESCR_NL": "",
                "pct_geen_nl_avg": "% non-Dutch home language",
            },
        )
        fig_edu_top.update_layout(
            coloraxis_showscale=False,
            height=470,
            margin={"l": 0, "r": 10, "t": 20, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
        )
        st.plotly_chart(fig_edu_top, use_container_width=True)

    st.divider()
    st.subheader("Momentum and school pipeline")
    st.markdown(
        "Pressure is not only about the level today. A fast-rising municipality can need "
        "planning before it reaches the top of the ranking. The primary-secondary gap also "
        "suggests where pressure may move next: a high primary signal often becomes tomorrow's "
        "secondary-school question."
    )

    youth_2014 = youth[youth["year"] == 2014][
        ["CD_REFNIS", "pct_bo_geen_nl", "pct_so_geen_nl", "pct_youth_niet_belg"]
    ].rename(columns={
        "pct_bo_geen_nl": "bo_2014",
        "pct_so_geen_nl": "so_2014",
        "pct_youth_niet_belg": "youth_2014",
    })
    edu_growth = edu.merge(youth_2014, on="CD_REFNIS", how="left")
    edu_growth["school_lang_growth_pp"] = (
        edu_growth["pct_geen_nl_avg"] - edu_growth[["bo_2014", "so_2014"]].mean(axis=1)
    ).round(1)
    edu_growth["youth_origin_growth_pp"] = (
        edu_growth["pct_youth_niet_belg"] - edu_growth["youth_2014"]
    ).round(1)

    col_growth_edu, col_profile_edu = st.columns([1.1, 0.9])
    with col_growth_edu:
        fastest_edu = edu_growth.nlargest(20, "school_lang_growth_pp").sort_values("school_lang_growth_pp")
        fig_growth_edu = go.Figure()
        fig_growth_edu.add_bar(
            y=fastest_edu["TX_DESCR_NL"],
            x=fastest_edu["school_lang_growth_pp"],
            name="School language growth",
            orientation="h",
            marker_color="#B23A48",
        )
        fig_growth_edu.add_bar(
            y=fastest_edu["TX_DESCR_NL"],
            x=fastest_edu["youth_origin_growth_pp"],
            name="Youth origin growth",
            orientation="h",
            marker_color="#164B60",
        )
        fig_growth_edu.update_layout(
            barmode="group",
            xaxis_title="Change since 2014 (percentage points)",
            yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin={"l": 0, "r": 10, "t": 40, "b": 0},
            height=470,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
        )
        st.plotly_chart(fig_growth_edu, use_container_width=True)

    with col_profile_edu:
        profile_options = edu.nlargest(30, "school_pressure_score")["TX_DESCR_NL"].tolist()
        profile_muni = st.selectbox("Municipality profile", profile_options, key="t2_edu_profile")
        profile = edu[edu["TX_DESCR_NL"] == profile_muni].iloc[0]
        profile_idx = profile.name
        categories = [
            "Primary home lang.",
            "Secondary home lang.",
            "Youth origin",
            "Newcomers rate",
            "Non-EU nationality",
        ]
        values = [
            float(minmax(edu["pct_bo_geen_nl"]).fillna(0).loc[profile_idx]),
            float(minmax(edu["pct_so_geen_nl"]).fillna(0).loc[profile_idx]),
            float(minmax(edu["pct_youth_niet_belg"]).fillna(0).loc[profile_idx]),
            float(minmax(edu["nieuwkomers_per_1000"].fillna(0)).loc[profile_idx]),
            float(minmax(edu["pct_non_eu27"].fillna(0)).loc[profile_idx]),
        ]
        fig_profile_edu = go.Figure()
        fig_profile_edu.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            line_color="#B23A48",
            fillcolor="rgba(178,58,72,0.25)",
            name=profile_muni,
        ))
        fig_profile_edu.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=420,
            margin={"l": 35, "r": 35, "t": 20, "b": 20},
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_profile_edu, use_container_width=True)
        st.caption(
            f"{profile_muni}: primary-secondary gap {profile['primary_secondary_gap']:.1f} pp; "
            f"newcomers {profile['nieuwkomers_per_1000']:.1f} per 1,000 residents."
        )

    st.subheader("How to read this page")
    st.markdown(
        "- **High score + high newcomer rate:** plan flexible reception, intake and language screening.\n"
        "- **High youth origin + lower newcomer rate:** focus on sustained multilingual parent communication and equal-opportunity work.\n"
        "- **Primary higher than secondary:** pressure is moving through the school pipeline.\n"
        "- **Secondary higher than primary:** pressure may be concentrated in specific urban or commuter school networks."
    )



    st.divider()
    st.subheader("School delay and early leaving: migration-linked risk lens")
    st.markdown(
        "The next step in the storyline is not only whether schools face language and intake "
        "pressure, but whether that pressure can become a school-career risk. Provincies in "
        "Cijfers contains the direct outcome indicators for this: pupils in secondary education "
        "with two or more years of school delay, and early school leavers by residence. Those "
        "official outcome tables are not in the local data folder yet, so the charts below are "
        "a transparent risk lens built from the migration and school-pressure indicators already "
        "loaded on this page."
    )
    st.caption(
        "Source context: Provincies in Cijfers outcome indicators are based on Onderwijs "
        "Vlaanderen. Vlaanderen defines early school leavers as young people leaving a regular "
        "qualifying secondary-education pathway without obtaining a qualification."
    )

    edu["school_delay_risk"] = (
        minmax(edu["pct_so_geen_nl"]).fillna(0) * 0.40
        + minmax(edu["pct_youth_niet_belg"]).fillna(0) * 0.25
        + minmax(edu["pct_non_eu27"].fillna(0)) * 0.20
        + minmax(edu["nieuwkomers_per_1000"].fillna(0)) * 0.15
    ).round(1)
    edu["early_leaver_risk"] = (
        edu["school_delay_risk"] * 0.45
        + minmax(edu["pct_so_geen_nl"]).fillna(0) * 0.25
        + minmax(edu["nieuwkomers_per_1000"].fillna(0)) * 0.15
        + minmax(edu["pct_non_eu27"].fillna(0)) * 0.15
    ).round(1)
    edu["school_career_risk"] = edu[["school_delay_risk", "early_leaver_risk"]].mean(axis=1).round(1)

    r1, r2, r3, r4 = st.columns(4)
    delay_top = edu.loc[edu["school_delay_risk"].idxmax()]
    leaver_top = edu.loc[edu["early_leaver_risk"].idxmax()]
    r1.metric("Delay risk lens", f"{edu['school_delay_risk'].mean():.1f}/100")
    r2.metric("Highest delay risk", delay_top["TX_DESCR_NL"], f"{delay_top['school_delay_risk']:.1f}/100")
    r3.metric("Early-leaver risk lens", f"{edu['early_leaver_risk'].mean():.1f}/100")
    r4.metric("Highest VSV risk", leaver_top["TX_DESCR_NL"], f"{leaver_top['early_leaver_risk']:.1f}/100")

    col_delay, col_vsv = st.columns([1, 1])
    with col_delay:
        st.markdown("**School delay lens.** Secondary home-language pressure is treated as the school-side signal.")
        fig_delay = px.scatter(
            edu,
            x="pct_youth_niet_belg",
            y="school_delay_risk",
            size="pct_so_geen_nl",
            color="TX_PROV_DESCR_NL",
            hover_name="TX_DESCR_NL",
            hover_data={
                "pct_so_geen_nl": ":.1f",
                "pct_youth_niet_belg": ":.1f",
                "pct_non_eu27": ":.1f",
                "nieuwkomers_per_1000": ":.1f",
                "school_delay_risk": ":.1f",
            },
            labels={
                "pct_youth_niet_belg": "% youth non-Belgian origin",
                "school_delay_risk": "School delay risk lens",
                "pct_so_geen_nl": "% secondary non-Dutch home lang.",
                "TX_PROV_DESCR_NL": "Province",
            },
            color_discrete_sequence=["#164B60", "#B23A48", "#E09F3E", "#3A7D44", "#7D4E8D"],
        )
        fig_delay.update_layout(
            height=430,
            margin={"l": 0, "r": 10, "t": 20, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_delay, use_container_width=True)

    with col_vsv:
        st.markdown("**Early leaving lens.** VSV risk is read as the point where delay risk meets newcomer pressure.")
        fig_vsv = px.scatter(
            edu,
            x="nieuwkomers_per_1000",
            y="early_leaver_risk",
            size="school_delay_risk",
            color="pct_non_eu27",
            hover_name="TX_DESCR_NL",
            hover_data={
                "pct_so_geen_nl": ":.1f",
                "pct_youth_niet_belg": ":.1f",
                "pct_non_eu27": ":.1f",
                "nieuwkomers_per_1000": ":.1f",
                "early_leaver_risk": ":.1f",
            },
            labels={
                "nieuwkomers_per_1000": "Newcomers / 1,000 residents",
                "early_leaver_risk": "Early-leaver risk lens",
                "pct_non_eu27": "% non-EU",
            },
            color_continuous_scale="YlOrRd",
        )
        fig_vsv.update_layout(
            height=430,
            margin={"l": 0, "r": 10, "t": 20, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
        )
        st.plotly_chart(fig_vsv, use_container_width=True)

    col_rank_risk, col_ladder = st.columns([0.95, 1.05])
    with col_rank_risk:
        st.markdown("**Where both risks stack.**")
        risk_top = edu.nlargest(20, "school_career_risk").sort_values("school_career_risk")
        fig_risk_top = go.Figure()
        fig_risk_top.add_bar(
            y=risk_top["TX_DESCR_NL"],
            x=risk_top["school_delay_risk"],
            name="School delay risk",
            orientation="h",
            marker_color="#E09F3E",
        )
        fig_risk_top.add_bar(
            y=risk_top["TX_DESCR_NL"],
            x=risk_top["early_leaver_risk"],
            name="Early-leaver risk",
            orientation="h",
            marker_color="#B23A48",
        )
        fig_risk_top.update_layout(
            barmode="group",
            xaxis_title="Risk lens score (0-100)",
            yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin={"l": 0, "r": 10, "t": 40, "b": 0},
            height=500,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F7F5F2",
        )
        st.plotly_chart(fig_risk_top, use_container_width=True)

    with col_ladder:
        st.markdown("**School-career pathway profile.**")
        ladder_defaults = edu.nlargest(6, "school_career_risk")["TX_DESCR_NL"].tolist()
        ladder_munis = st.multiselect(
            "Compare municipalities",
            sorted(edu["TX_DESCR_NL"].dropna().unique()),
            default=ladder_defaults,
            key="t2_school_career_ladder",
        )
        if ladder_munis:
            ladder = edu[edu["TX_DESCR_NL"].isin(ladder_munis)].copy()
            ladder_long = ladder.melt(
                id_vars="TX_DESCR_NL",
                value_vars=[
                    "school_pressure_score",
                    "school_delay_risk",
                    "early_leaver_risk",
                    "nieuwkomers_per_1000",
                ],
                var_name="step",
                value_name="value",
            )
            ladder_long["step"] = ladder_long["step"].map({
                "school_pressure_score": "School pressure",
                "school_delay_risk": "Delay risk",
                "early_leaver_risk": "Early-leaver risk",
                "nieuwkomers_per_1000": "Newcomer rate",
            })
            fig_ladder = px.line(
                ladder_long,
                x="step",
                y="value",
                color="TX_DESCR_NL",
                markers=True,
                labels={"step": "", "value": "Score / rate", "TX_DESCR_NL": "Municipality"},
            )
            fig_ladder.update_layout(
                height=500,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin={"l": 0, "r": 10, "t": 40, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#F7F5F2",
            )
            st.plotly_chart(fig_ladder, use_container_width=True)
        else:
            st.info("Select at least one municipality.")

    st.markdown(
        "**Interpretation.** Use this as a triage layer, not as the official outcome rate. "
        "When the school-delay and VSV tables are exported from Provincies in Cijfers, they "
        "can replace these risk lenses directly: keep the same migration scatterplots, but put "
        "the official percentages on the y-axis."
    )


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
