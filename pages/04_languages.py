import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.data_loader import (
    load_flanders_youth,
    load_newcomers,
    load_geojson,
)

st.markdown("""
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
""", unsafe_allow_html=True)

st.title("🗣️ Migration & Spoken Languages")
st.caption(
    "Home language of newborns and school language profiles across Flemish municipalities · "
    "Sources: provincies.incijfers.be, Agentschap Integratie & Inburgering, StatBel"
)

st.markdown(
    "This page focuses on three policy insights: where non-Dutch home language is most visible in schools, "
    "which home-language communities shape newborn registrations, and which municipalities should be prioritised "
    "when school-language needs, newborn home language and newcomer inflow are read together."
)

def build_language_proxy(youth_df):
    lang_df = youth_df[youth_df["year"].between(2020, 2024)].copy()
    lang_df["pct_turkish_arabic_berber"] = (
        lang_df["pct_youth_turks"].fillna(0) + lang_df["pct_youth_maghreb"].fillna(0)
    ).round(1)
    lang_df["pct_russian_polish_romanian"] = lang_df["pct_youth_oost_eu"].fillna(0).round(1)
    lang_df["pct_french"] = 0.0
    lang_df["pct_spanish_portuguese"] = 0.0
    lang_df["pct_english_german"] = 0.0
    known_proxy = (
        lang_df["pct_turkish_arabic_berber"]
        + lang_df["pct_russian_polish_romanian"]
        + lang_df["pct_youth_afrik"].fillna(0)
    )
    lang_df["pct_non_dutch"] = lang_df["pct_geen_nl_avg"].fillna(0).round(1)
    lang_df["pct_other"] = (lang_df["pct_non_dutch"] - known_proxy).clip(lower=0).round(1)
    return lang_df

youth     = load_flanders_youth()           # 2014-2024
lang      = build_language_proxy(youth)     # 2020-2024 proxy from available school/youth indicators
newcomers = load_newcomers()                # 2014-2024
geojson   = load_geojson()

PROV_NUTS_MAP = {
    "Provincie Antwerpen":       "BE21",
    "Provincie Limburg":         "BE22",
    "Provincie Oost-Vlaanderen": "BE23",
    "Provincie Vlaams-Brabant":  "BE24",
    "Provincie West-Vlaanderen": "BE25",
}
PROV_EN_MAP = {
    "Provincie Antwerpen":       "Antwerp",
    "Provincie Limburg":         "Limburg",
    "Provincie Oost-Vlaanderen": "East Flanders",
    "Provincie Vlaams-Brabant":  "Flemish Brabant",
    "Provincie West-Vlaanderen": "West Flanders",
}

YOUTH_YEARS = sorted(youth["year"].unique())
LANG_YEARS  = sorted(lang["year"].unique())


def minmax(s):
    lo, hi = s.min(), s.max()
    return ((s - lo) / (hi - lo) * 100).round(1) if hi > lo else s * 0


def make_choropleth(df, color_col, label, color_scale="Blues",
                    range_max=None, hover_extra=None, height=500):
    hover = {color_col: ":.1f", "CD_REFNIS": False}
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


def build_language_proxy(youth_df):
    lang_df = youth_df[youth_df["year"].between(2020, 2024)].copy()
    lang_df["pct_turkish_arabic_berber"] = (
        lang_df["pct_youth_turks"].fillna(0) + lang_df["pct_youth_maghreb"].fillna(0)
    ).round(1)
    lang_df["pct_russian_polish_romanian"] = lang_df["pct_youth_oost_eu"].fillna(0).round(1)
    lang_df["pct_french"] = 0.0
    lang_df["pct_spanish_portuguese"] = 0.0
    lang_df["pct_english_german"] = 0.0
    known_proxy = (
        lang_df["pct_turkish_arabic_berber"]
        + lang_df["pct_russian_polish_romanian"]
        + lang_df["pct_youth_afrik"].fillna(0)
    )
    lang_df["pct_non_dutch"] = lang_df["pct_geen_nl_avg"].fillna(0).round(1)
    lang_df["pct_other"] = (lang_df["pct_non_dutch"] - known_proxy).clip(lower=0).round(1)
    return lang_df


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — School language overview map
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Non-Dutch home language in schools")
st.info(
    "Definition: this indicator is the share of pupils whose reported home language is not Dutch. "
    "The map uses the average of primary education and secondary education percentages for each "
    "municipality or province. It is a language-support planning signal, not a measure of pupil ability "
    "or school quality."
)

geo_level = st.radio(
    "Geographic level", ["Municipality", "Province"], horizontal=True, key="s1_geo_level"
)

col_yr1, col_play1 = st.columns([3, 1])
with col_yr1:
    year1 = st.selectbox(
        "Year", YOUTH_YEARS, index=len(YOUTH_YEARS) - 1, key="s1_year"
    )
with col_play1:
    st.write("")  # align button with selectbox
    map_mode1 = st.radio("View", ["Selected year", "Animated trend"], key="s1_map_mode")

slot1 = st.empty()


def render_s1(yr):
    y1 = youth[youth["year"] == yr].copy()
    fl_avg   = y1["pct_geen_nl_avg"].mean()
    ref_yr   = max(min(YOUTH_YEARS), yr - 5)
    fl_delta = fl_avg - youth[youth["year"] == ref_yr]["pct_geen_nl_avg"].mean()

    if geo_level == "Province":
        prov = (
            y1.groupby("TX_PROV_DESCR_NL")
            .agg(
                pct_geen_nl_avg=("pct_geen_nl_avg", "mean"),
                pct_bo_geen_nl=("pct_bo_geen_nl", "mean"),
                pct_so_geen_nl=("pct_so_geen_nl", "mean"),
            )
            .round(1)
            .reset_index()
        )
        prov["province_en"] = prov["TX_PROV_DESCR_NL"].map(PROV_EN_MAP)
        prov_high = prov.loc[prov["pct_geen_nl_avg"].idxmax()]
        prov_low  = prov.loc[prov["pct_geen_nl_avg"].idxmin()]

        with slot1.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Flanders average",  f"{fl_avg:.1f}%")
            c2.metric("Highest province",  prov_high["province_en"], f"{prov_high['pct_geen_nl_avg']:.1f}%")
            c3.metric("Lowest province",   prov_low["province_en"],  f"{prov_low['pct_geen_nl_avg']:.1f}%")
            c4.metric(f"Trend vs {ref_yr}", f"{fl_avg:.1f}%", delta=f"{fl_delta:+.1f} pp")

            fig_prov = px.bar(
                prov.sort_values("pct_geen_nl_avg"),
                x="pct_geen_nl_avg",
                y="province_en",
                orientation="h",
                color="pct_geen_nl_avg",
                hover_data={
                    "pct_bo_geen_nl": ":.1f",
                    "pct_so_geen_nl": ":.1f",
                },
                color_continuous_scale="Blues",
                labels={
                    "pct_geen_nl_avg": "% non-Dutch",
                    "province_en": "Province",
                    "pct_bo_geen_nl":  "% primary ed.",
                    "pct_so_geen_nl":  "% secondary ed.",
                },
            )
            fig_prov.update_layout(
                margin={"r": 20, "t": 30, "l": 0, "b": 0},
                height=500,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#F7F5F2",
                coloraxis_showscale=False,
                title=dict(text=f"Province average - {yr}", font=dict(size=13)),
                xaxis=dict(ticksuffix="%"),
            )
            st.plotly_chart(fig_prov, use_container_width=True)

    else:
        y1["flanders_avg"] = round(fl_avg, 1)
        fl_high = y1.loc[y1["pct_geen_nl_avg"].idxmax()]
        fl_low  = y1.loc[y1["pct_geen_nl_avg"].idxmin()]

        with slot1.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Flanders average",    f"{fl_avg:.1f}%")
            c2.metric("Highest municipality", fl_high["TX_DESCR_NL"], f"{fl_high['pct_geen_nl_avg']:.1f}%")
            c3.metric("Lowest municipality",  fl_low["TX_DESCR_NL"],  f"{fl_low['pct_geen_nl_avg']:.1f}%")
            c4.metric(f"Trend vs {ref_yr}",  f"{fl_avg:.1f}%", delta=f"{fl_delta:+.1f} pp")

            fig = make_choropleth(
                y1, "pct_geen_nl_avg",
                f"% non-Dutch home lang. (avg primary+secondary) — {yr}",
                range_max=25,
                hover_extra={
                    "pct_bo_geen_nl": ":.1f",
                    "pct_so_geen_nl": ":.1f",
                    "flanders_avg":   ":.1f",
                },
            )
            fig.update_layout(coloraxis_colorbar=dict(title="% non-Dutch", ticksuffix="%"))
            st.plotly_chart(fig, use_container_width=True)


def render_s1_animation():
    if geo_level == "Province":
        prov_anim = (
            youth.groupby(["year", "TX_PROV_DESCR_NL"])
            .agg(
                pct_geen_nl_avg=("pct_geen_nl_avg", "mean"),
                pct_bo_geen_nl=("pct_bo_geen_nl", "mean"),
                pct_so_geen_nl=("pct_so_geen_nl", "mean"),
            )
            .round(1)
            .reset_index()
        )
        prov_anim["province_en"] = prov_anim["TX_PROV_DESCR_NL"].map(PROV_EN_MAP)
        fig_anim = px.bar(
            prov_anim.sort_values(["year", "pct_geen_nl_avg"]),
            x="pct_geen_nl_avg",
            y="province_en",
            orientation="h",
            color="pct_geen_nl_avg",
            animation_frame="year",
            hover_data={
                "pct_bo_geen_nl": ":.1f",
                "pct_so_geen_nl": ":.1f",
            },
            color_continuous_scale="Blues",
            range_x=[0, 25],
            labels={
                "pct_geen_nl_avg": "% non-Dutch",
                "province_en": "Province",
                "pct_bo_geen_nl": "% primary ed.",
                "pct_so_geen_nl": "% secondary ed.",
                "year": "Year",
            },
        )
    else:
        fig_anim = px.choropleth(
            youth,
            geojson=geojson,
            locations="CD_REFNIS",
            featureidkey="properties.NSI_CODE",
            color="pct_geen_nl_avg",
            animation_frame="year",
            hover_name="TX_DESCR_NL",
            hover_data={
                "pct_bo_geen_nl": ":.1f",
                "pct_so_geen_nl": ":.1f",
                "TX_PROV_DESCR_NL": True,
                "CD_REFNIS": False,
            },
            color_continuous_scale="Blues",
            range_color=[0, 25],
            labels={
                "pct_geen_nl_avg": "% non-Dutch",
                "pct_bo_geen_nl": "% primary ed.",
                "pct_so_geen_nl": "% secondary ed.",
                "year": "Year",
            },
        )
    fig_anim.update_geos(fitbounds="locations", visible=False)
    fig_anim.update_layout(
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
        height=530,
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        coloraxis_colorbar=dict(title="% non-Dutch", ticksuffix="%"),
    )
    st.plotly_chart(fig_anim, use_container_width=True)


if map_mode1 == "Animated trend":
    render_s1_animation()
else:
    render_s1(year1)

st.caption(
    "Share of pupils whose home language is not Dutch, averaged across primary and secondary education. "
    "High values indicate municipalities where language support needs are greatest."
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Language diversity map (home language of newborns)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Newborn home-language composition")
st.markdown(
    "This view uses Kind & Gezin home-visit registrations: the language is the language in which mother "
    "and child communicate at home. Select multiple language groups to compare them side by side instead "
    "of reading one grouped category in isolation."
)

LANG_LAYERS = {
    "Turkish / Arabic / Berber":   "pct_turkish_arabic_berber",
    "French":                      "pct_french",
    "Russian / Polish / Romanian": "pct_russian_polish_romanian",
    "Spanish / Portuguese":        "pct_spanish_portuguese",
    "English / German":            "pct_english_german",
    "Other languages":             "pct_other",
}

col_yr2, col_lang2 = st.columns([1, 2])
with col_yr2:
    year2 = st.selectbox(
        "Year", LANG_YEARS, index=len(LANG_YEARS) - 1, key="s2_year"
    )
with col_lang2:
    lang_choices = st.multiselect(
        "Language groups",
        list(LANG_LAYERS.keys()),
        default=["Turkish / Arabic / Berber", "French", "Other languages"],
        key="s2_lang_multi",
    )

l2 = lang[lang["year"] == year2].copy()
top15_lang = l2.nlargest(15, "pct_non_dutch")
if lang_choices:
    comp_long = top15_lang.melt(
        id_vars=["TX_DESCR_NL", "pct_non_dutch"],
        value_vars=[LANG_LAYERS[label] for label in lang_choices],
        var_name="language_col",
        value_name="share",
    )
    col_to_label = {col: label for label, col in LANG_LAYERS.items()}
    comp_long["Language group"] = comp_long["language_col"].map(col_to_label)
    fig_lang_comp = px.bar(
        comp_long,
        y="TX_DESCR_NL",
        x="share",
        color="Language group",
        barmode="group",
        orientation="h",
        labels={
            "TX_DESCR_NL": "Municipality",
            "share": "% of newborns",
        },
        color_discrete_sequence=["#C1392B", "#2E86AB", "#E67E22", "#27AE60", "#8E44AD", "#95A5A6"],
    )
    fig_lang_comp.update_layout(
        title=f"Selected language groups in top non-Dutch newborn municipalities - {year2}",
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin={"l": 0, "r": 10, "t": 55, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
        xaxis=dict(ticksuffix="%"),
    )
    st.plotly_chart(fig_lang_comp, use_container_width=True)
else:
    st.info("Select at least one language group.")

st.caption(
    "% of newborns for whom mother and child communicate in the selected language. "
    "Data from Kind & Gezin home-visit registrations, Flemish municipalities only."
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Non-Dutch newborn language map
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Non-Dutch newborn home language - local overview")

STACK_COLS = [
    ("pct_turkish_arabic_berber",   "Turkish / Arabic / Berber",   "#C1392B"),
    ("pct_french",                  "French",                       "#2E86AB"),
    ("pct_russian_polish_romanian", "Russian / Polish / Romanian",  "#E67E22"),
    ("pct_spanish_portuguese",      "Spanish / Portuguese",         "#27AE60"),
    ("pct_english_german",          "English / German",             "#8E44AD"),
    ("pct_other",                   "Other languages",              "#95A5A6"),
]

year3 = st.selectbox(
    "Year", LANG_YEARS, index=len(LANG_YEARS) - 1, key="s3_year"
)
l3 = lang[lang["year"] == year3].copy()
fig_non_dutch_newborns = make_choropleth(
    l3,
    "pct_non_dutch",
    f"% non-Dutch newborn home language - {year3}",
    range_max=max(25, float(l3["pct_non_dutch"].quantile(0.95))),
    hover_extra={
        "pct_turkish_arabic_berber": ":.1f",
        "pct_french": ":.1f",
        "pct_russian_polish_romanian": ":.1f",
        "pct_spanish_portuguese": ":.1f",
        "pct_english_german": ":.1f",
        "pct_other": ":.1f",
    },
    height=540,
)
fig_non_dutch_newborns.update_layout(coloraxis_colorbar=dict(title="% non-Dutch", ticksuffix="%"))
st.plotly_chart(fig_non_dutch_newborns, use_container_width=True)

st.caption(
    "The colour shows the total share of newborns with a non-Dutch home language. Hover details keep "
    "the breakdown by language group available for local interpretation without making the main story "
    "depend on one selected language category."
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Trend over time (school language)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Non-Dutch home language in schools — trend 2014–2024")

all_munis4 = sorted(youth["TX_DESCR_NL"].dropna().unique())
default_munis4 = [m for m in ["Antwerpen", "Gent", "Leuven", "Mechelen", "Genk"]
                  if m in all_munis4]

col_s4a, col_s4b = st.columns([2, 1])
with col_s4a:
    sel_munis4 = st.multiselect(
        "Compare municipalities (vs Flanders average)",
        all_munis4, default=default_munis4, key="s4_munis",
    )
with col_s4b:
    show_split = st.checkbox("Split primary vs secondary", value=False, key="s4_split")

fl_trend = (
    youth.groupby("year")[["pct_geen_nl_avg", "pct_bo_geen_nl", "pct_so_geen_nl"]]
    .mean()
    .reset_index()
)

fig4 = go.Figure()
if show_split:
    fig4.add_scatter(
        x=fl_trend["year"], y=fl_trend["pct_bo_geen_nl"],
        name="Flanders avg — primary", mode="lines",
        line=dict(color="#2E86AB", width=2.5, dash="solid"),
    )
    fig4.add_scatter(
        x=fl_trend["year"], y=fl_trend["pct_so_geen_nl"],
        name="Flanders avg — secondary", mode="lines",
        line=dict(color="#1B2A4A", width=2.5, dash="dot"),
    )
else:
    fig4.add_scatter(
        x=fl_trend["year"], y=fl_trend["pct_geen_nl_avg"],
        name="Flanders average", mode="lines",
        line=dict(color="#2E86AB", width=3, dash="solid"),
    )

MUNI_PALETTE = ["#E07B39", "#6B9E6B", "#9B59B6", "#C0392B", "#16A085", "#8E44AD"]
for i, muni in enumerate(sel_munis4 or []):
    muni_df = youth[youth["TX_DESCR_NL"] == muni].sort_values("year")
    if show_split:
        fig4.add_scatter(
            x=muni_df["year"], y=muni_df["pct_bo_geen_nl"],
            name=f"{muni} — primary", mode="lines+markers",
            line=dict(color=MUNI_PALETTE[i % len(MUNI_PALETTE)], width=1.5, dash="solid"),
            marker=dict(size=5),
        )
        fig4.add_scatter(
            x=muni_df["year"], y=muni_df["pct_so_geen_nl"],
            name=f"{muni} — secondary", mode="lines+markers",
            line=dict(color=MUNI_PALETTE[i % len(MUNI_PALETTE)], width=1.5, dash="dash"),
            marker=dict(size=5),
        )
    else:
        fig4.add_scatter(
            x=muni_df["year"], y=muni_df["pct_geen_nl_avg"],
            name=muni, mode="lines+markers",
            line=dict(color=MUNI_PALETTE[i % len(MUNI_PALETTE)], width=1.8),
            marker=dict(size=6),
        )

fig4.update_layout(
    hovermode="x unified",
    yaxis_title="% non-Dutch home language",
    xaxis_title="Year",
    yaxis=dict(ticksuffix="%", gridcolor="#E0DDD8"),
    xaxis=dict(showgrid=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
    margin={"t": 40, "b": 10},
    height=420,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#F7F5F2",
)
st.plotly_chart(fig4, use_container_width=True)
st.caption(
    "The thick line shows the Flanders-wide average. "
    "Selected municipalities are overlaid for comparison. "
    "Primary education typically shows a higher non-Dutch share than secondary, "
    "reflecting more recent arrival of younger families."
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Policy recommendation table
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Language support need - priority ranking")
st.markdown(
    "**Score methodology:** equal-weight average of three normalised dimensions (0-100 each): "
    "% non-Dutch home language in schools, % non-Dutch home language among newborns, and "
    "newcomer rate per 1,000 residents. The overall priority rank ties the language story together."
)

POLICY_YEAR = max(LANG_YEARS)

lang_p = lang[lang["year"] == POLICY_YEAR][
    ["CD_REFNIS", "TX_DESCR_NL", "TX_PROV_DESCR_NL",
     "pct_non_dutch", "pct_turkish_arabic_berber"]
].copy()

youth_p = youth[youth["year"] == POLICY_YEAR][["CD_REFNIS", "pct_geen_nl_avg"]].copy()
nw_p    = newcomers[newcomers["year"] == POLICY_YEAR][["CD_REFNIS", "nieuwkomers_per_1000"]].copy()

policy = (
    lang_p
    .merge(youth_p, on="CD_REFNIS", how="left")
    .merge(nw_p,    on="CD_REFNIS", how="left")
    .dropna(subset=["pct_geen_nl_avg"])
)

policy["score_school"] = minmax(policy["pct_geen_nl_avg"])
policy["score_newborn_home_lang"] = minmax(policy["pct_non_dutch"])
policy["score_newcomers"] = minmax(policy["nieuwkomers_per_1000"].fillna(0))
policy["support_score"] = (
    policy[["score_school", "score_newborn_home_lang", "score_newcomers"]]
    .mean(axis=1).round(1)
)
policy["priority_rank"] = policy["support_score"].rank(method="min", ascending=False).astype(int)

search_policy = st.text_input(
    "Search municipality",
    "",
    placeholder="e.g. Antwerpen, Gent, Genk",
    key="language_priority_search",
)

top20_components = policy.nlargest(20, "support_score").sort_values("support_score", ascending=True)
fig_priority = go.Figure()
for col, label, color in [
    ("score_school", "School non-Dutch home language", "#B23A48"),
    ("score_newborn_home_lang", "Newborn non-Dutch home language", "#2E86AB"),
    ("score_newcomers", "Newcomer inflow", "#E09F3E"),
]:
    fig_priority.add_bar(
        y=top20_components["TX_DESCR_NL"],
        x=top20_components[col],
        name=label,
        orientation="h",
        marker_color=color,
    )
fig_priority.update_layout(
    barmode="stack",
    height=540,
    xaxis_title="Normalised score contribution",
    yaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin={"l": 0, "r": 10, "t": 45, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#F7F5F2",
)
st.plotly_chart(fig_priority, use_container_width=True)

policy_table = (
    policy.sort_values("priority_rank")[
        ["priority_rank", "TX_DESCR_NL", "TX_PROV_DESCR_NL",
         "pct_geen_nl_avg", "pct_non_dutch", "nieuwkomers_per_1000",
         "score_school", "score_newborn_home_lang", "score_newcomers", "support_score"]
    ]
    .rename(columns={
        "priority_rank":             "Priority rank",
        "TX_DESCR_NL":               "Municipality",
        "TX_PROV_DESCR_NL":          "Province",
        "pct_geen_nl_avg":           "% non-Dutch in schools",
        "pct_non_dutch":             "% non-Dutch newborn home language",
        "nieuwkomers_per_1000":      "Newcomers / 1,000",
        "score_school":              "School dimension score",
        "score_newborn_home_lang":    "Newborn language dimension score",
        "score_newcomers":           "Newcomer dimension score",
        "support_score":             "Support score",
    })
)
if search_policy.strip():
    policy_table = policy_table[
        policy_table["Municipality"].str.contains(search_policy.strip(), case=False, na=False)
    ]

st.dataframe(
    policy_table.head(30),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Support score": st.column_config.ProgressColumn(
            "Support score",
            min_value=0,
            max_value=100,
            format="%.1f",
        )
    },
)
st.caption(
    f"Rankings based on {POLICY_YEAR} data. "
    "Score is the average of three min-max normalised indicators, "
    "each scaled 0–100. Municipalities with missing newcomer data are scored 0 on that component."
)
