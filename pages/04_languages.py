import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.data_loader import load_flanders_youth, load_newcomers

st.markdown("""
<style>
h1 { font-size: 2rem !important; font-weight: 700; }
hr { border-color: #E2DED8 !important; margin: 1.25rem 0; }
div[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E2DED8;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

st.title("Language Support Needs")
st.caption(
    "Non-Dutch home language in Flemish schools, municipality-level language support priority, "
    "and local trend comparison. Sources: provincies.incijfers.be, Agentschap Integratie & Inburgering, StatBel"
)

youth = load_flanders_youth()
newcomers = load_newcomers()
YEARS = sorted(youth["year"].unique())


def minmax(s):
    lo, hi = s.min(), s.max()
    return ((s - lo) / (hi - lo) * 100).round(1) if hi > lo else s * 0


language_frames = []
for yr in YEARS:
    y_yr = youth[youth["year"] == yr].copy()
    n_yr = newcomers[newcomers["year"] == yr][["CD_REFNIS", "nieuwkomers_per_1000"]].copy()
    frame = y_yr.merge(n_yr, on="CD_REFNIS", how="left")
    language_frames.append(frame)

lang_all = pd.concat(language_frames, ignore_index=True)
lang_all["primary_component"] = (minmax(lang_all["pct_bo_geen_nl"]).fillna(0) * 0.40).round(1)
lang_all["secondary_component"] = (minmax(lang_all["pct_so_geen_nl"]).fillna(0) * 0.40).round(1)
lang_all["newcomer_component"] = (minmax(lang_all["nieuwkomers_per_1000"].fillna(0)) * 0.20).round(1)
lang_all["language_support_score"] = (
    lang_all["primary_component"]
    + lang_all["secondary_component"]
    + lang_all["newcomer_component"]
).round(1)

lang_2014 = lang_all[lang_all["year"] == 2014][
    ["CD_REFNIS", "language_support_score", "pct_geen_nl_avg"]
].rename(columns={
    "language_support_score": "score_2014",
    "pct_geen_nl_avg": "home_language_2014",
})
lang_2024 = lang_all[lang_all["year"] == 2024].merge(lang_2014, on="CD_REFNIS", how="left")
lang_2024["score_change_2014_2024"] = (
    lang_2024["language_support_score"] - lang_2024["score_2014"]
).round(1)
lang_2024["home_language_change_2014_2024"] = (
    lang_2024["pct_geen_nl_avg"] - lang_2024["home_language_2014"]
).round(1)
lang_2024["priority_score"] = (
    lang_2024["language_support_score"].rank(pct=True)
    + lang_2024["score_change_2014_2024"].rank(pct=True)
).round(3)
lang_2024["priority_rank"] = lang_2024["priority_score"].rank(method="min", ascending=False).astype(int)

province_year = (
    lang_all.groupby(["year", "TX_PROV_DESCR_NL"], as_index=False)
    .agg(
        language_support_score=("language_support_score", "mean"),
        pct_bo_geen_nl=("pct_bo_geen_nl", "mean"),
        pct_so_geen_nl=("pct_so_geen_nl", "mean"),
        newcomers_per_1000=("nieuwkomers_per_1000", "mean"),
    )
)
province_2014 = province_year[province_year["year"] == 2014][
    ["TX_PROV_DESCR_NL", "language_support_score"]
].rename(columns={"language_support_score": "score_2014"})
province_2024 = province_year[province_year["year"] == 2024].merge(
    province_2014, on="TX_PROV_DESCR_NL", how="left"
)
province_2024["score_change"] = (
    province_2024["language_support_score"] - province_2024["score_2014"]
).round(1)

top_province = province_2024.sort_values("language_support_score", ascending=False).iloc[0]
fastest_province = province_2024.sort_values("score_change", ascending=False).iloc[0]
top_muni = lang_2024.sort_values("language_support_score", ascending=False).iloc[0]
fastest_muni = lang_2024.sort_values("score_change_2014_2024", ascending=False).iloc[0]

st.subheader("Language support pressure in Flanders, 2014-2024")
st.markdown(
    "This page follows the same three-step structure as the education view. It first shows the province-level "
    "picture, then turns the score into a municipality priority ranking, and finally lets users compare local "
    "trends within a selected province."
)
st.info(
    "Score definition: 40% normalised non-Dutch home-language share in primary education, 40% normalised "
    "non-Dutch home-language share in secondary education, and 20% normalised newcomers per 1,000 residents. "
    "The priority rank combines the 2024 score level with growth since 2014."
)

k1, k2, k3 = st.columns(3)
k1.metric("Highest province in 2024", top_province["TX_PROV_DESCR_NL"], f"{top_province['language_support_score']:.1f}/100")
k2.metric("Fastest rising province", fastest_province["TX_PROV_DESCR_NL"], f"+{fastest_province['score_change']:.1f}")
k3.metric("Highest municipality in 2024", top_muni["TX_DESCR_NL"], f"{top_muni['language_support_score']:.1f}/100")

st.markdown(
    f"In 2024, **{top_province['TX_PROV_DESCR_NL']}** has the highest average language-support score. "
    f"The strongest increase since 2014 is in **{fastest_province['TX_PROV_DESCR_NL']}**. At municipality "
    f"level, **{top_muni['TX_DESCR_NL']}** has the highest current score, while "
    f"**{fastest_muni['TX_DESCR_NL']}** rose fastest over the full period."
)

st.divider()
st.subheader("1. Province picture: where are language support needs highest?")
st.markdown(
    "Use the play button to move from 2014 to 2024. The chart stays at province level so the trend is "
    "easy to read without labels or map text competing for space."
)

fig_province = px.bar(
    province_year.sort_values(["year", "language_support_score"]),
    x="language_support_score",
    y="TX_PROV_DESCR_NL",
    orientation="h",
    color="language_support_score",
    animation_frame="year",
    range_x=[0, max(100, float(province_year["language_support_score"].max()) * 1.05)],
    color_continuous_scale="YlOrRd",
    text="language_support_score",
    labels={
        "language_support_score": "Language support score",
        "TX_PROV_DESCR_NL": "Province",
        "year": "Year",
    },
)
fig_province.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
fig_province.update_layout(
    height=430,
    coloraxis_showscale=False,
    margin={"l": 0, "r": 45, "t": 20, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#F7F5F2",
    xaxis=dict(showgrid=True, gridcolor="#E0DDD8"),
    yaxis=dict(title=""),
)
st.plotly_chart(fig_province, width="stretch")

st.markdown(
    "High scores point to structural language-support capacity needs. Fast-rising scores are early-warning "
    "signals for municipalities and schools where coordination may need to increase soon."
)

st.divider()
st.subheader("2. Municipality priority ranking: what drives the score?")
st.markdown(
    "Use the year filter to inspect the highest-ranking municipalities and the dimensions behind their score. "
    "The stacked bars keep the ranking readable while still showing whether the pressure comes mostly from "
    "primary education, secondary education, or newcomer inflow."
)

selected_year = st.select_slider("Year", options=YEARS, value=2024, key="language_priority_year")
lang_year = lang_all[lang_all["year"] == selected_year].copy()
lang_year["priority_rank"] = lang_year["language_support_score"].rank(method="min", ascending=False).astype(int)
top20 = lang_year.nlargest(20, "language_support_score").sort_values("language_support_score", ascending=True)

fig_components = go.Figure()
for col, label, color in [
    ("primary_component", "Primary education", "#B23A48"),
    ("secondary_component", "Secondary education", "#2E86AB"),
    ("newcomer_component", "Newcomer inflow", "#E09F3E"),
]:
    fig_components.add_bar(
        y=top20["TX_DESCR_NL"],
        x=top20[col],
        name=label,
        orientation="h",
        marker_color=color,
    )
fig_components.update_layout(
    barmode="stack",
    height=560,
    xaxis_title="Language support score contribution",
    yaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
    margin={"l": 0, "r": 10, "t": 55, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#F7F5F2",
    xaxis=dict(showgrid=True, gridcolor="#E0DDD8"),
)
st.plotly_chart(fig_components, width="stretch")

search_muni = st.text_input(
    "Search municipality",
    "",
    placeholder="e.g. Antwerpen, Gent, Genk",
    key="language_priority_search",
)
ranking_table = lang_year.sort_values("priority_rank")[
    [
        "priority_rank",
        "TX_DESCR_NL",
        "TX_PROV_DESCR_NL",
        "language_support_score",
        "pct_bo_geen_nl",
        "pct_so_geen_nl",
        "nieuwkomers_per_1000",
    ]
].rename(columns={
    "priority_rank": "Priority rank",
    "TX_DESCR_NL": "Municipality",
    "TX_PROV_DESCR_NL": "Province",
    "language_support_score": "Overall score",
    "pct_bo_geen_nl": "Primary non-Dutch home language (%)",
    "pct_so_geen_nl": "Secondary non-Dutch home language (%)",
    "nieuwkomers_per_1000": "Newcomers / 1,000",
})
if search_muni.strip():
    ranking_table = ranking_table[
        ranking_table["Municipality"].str.contains(search_muni.strip(), case=False, na=False)
    ]
st.dataframe(ranking_table.head(30), width="stretch", hide_index=True)

st.divider()
st.subheader("3. Local support planning: which municipalities need capacity first?")
st.markdown(
    "Choose a province, then show all municipalities in that province or select specific municipalities. "
    "For the all-municipality view the legend is hidden to avoid overlap; use the specific selection when "
    "you want labelled comparison lines."
)

province_options = province_2024.sort_values("language_support_score", ascending=False)["TX_PROV_DESCR_NL"].tolist()
selected_province = st.selectbox("Province", province_options, key="language_province")
province_munis = (
    lang_2024[lang_2024["TX_PROV_DESCR_NL"] == selected_province]
    .sort_values("language_support_score", ascending=False)
)
selection_mode = st.radio(
    "Municipality selection",
    ["All municipalities in province", "Select specific municipalities"],
    horizontal=True,
    key="language_selection_mode",
)
if selection_mode == "All municipalities in province":
    selected_munis = province_munis["TX_DESCR_NL"].tolist()
else:
    default_munis = province_munis.head(8)["TX_DESCR_NL"].tolist()
    selected_munis = st.multiselect(
        "Municipalities to compare",
        province_munis["TX_DESCR_NL"].tolist(),
        default=default_munis,
        key="language_selected_munis",
    )

if selected_munis:
    trend = lang_all[lang_all["TX_DESCR_NL"].isin(selected_munis)].copy()
    fig_trend = px.line(
        trend,
        x="year",
        y="language_support_score",
        color="TX_DESCR_NL",
        markers=True,
        labels={
            "year": "Year",
            "language_support_score": "Language support score",
            "TX_DESCR_NL": "Municipality",
        },
    )
    fig_trend.update_layout(
        height=470,
        hovermode="x unified",
        showlegend=selection_mode != "All municipalities in province",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        margin={"l": 0, "r": 10, "t": 55, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F5F2",
        yaxis=dict(showgrid=True, gridcolor="#E0DDD8"),
        xaxis=dict(dtick=1),
    )
    if selection_mode == "All municipalities in province":
        fig_trend.update_traces(line=dict(width=1.4), marker=dict(size=4), opacity=0.55)
    st.plotly_chart(fig_trend, width="stretch")

    selected_summary = lang_2024[lang_2024["TX_DESCR_NL"].isin(selected_munis)].sort_values(
        "score_change_2014_2024", ascending=False
    )
    fastest_selected = selected_summary.iloc[0]
    highest_selected = selected_summary.sort_values("language_support_score", ascending=False).iloc[0]
    st.markdown(
        f"For **{selected_province}**, **{highest_selected['TX_DESCR_NL']}** has the highest 2024 language-support "
        f"score among the selected municipalities. **{fastest_selected['TX_DESCR_NL']}** rose the most between "
        "2014 and 2024, so it is the clearest early-capacity signal."
    )
else:
    st.info("Select at least one municipality.")
