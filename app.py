import streamlit as st

st.set_page_config(
    page_title="Belgian Demographics 1992–2025",
    layout="wide",
    page_icon="🇧🇪",
)

st.markdown("""
<style>
h1 { font-size: 2rem !important; font-weight: 700; }
hr { border-color: #E2DED8 !important; margin: 1.25rem 0; }
</style>
""", unsafe_allow_html=True)

st.title("🇧🇪 Belgian Demographics 1992–2025")
st.markdown(
    "Explore how Belgium's population has shifted over three decades — nationally, regionally, "
    "and at the municipality level. Data: **StatBel** · CC BY 4.0"
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Belgium Overview")
    st.markdown(
        "National snapshot with an interactive choropleth, key metrics, and the long-run trend "
        "in non-Belgian population share since 1992."
    )

with col2:
    st.markdown("### Origin & Composition")
    st.markdown(
        "How Belgium's population breaks down by origin group (Belgian background, neighbouring "
        "countries, EU27, non-EU27), with age and gender cuts."
    )

with col3:
    st.markdown("### Flanders Policy Insights")
    st.markdown(
        "Deep-dive into Flanders: language integration pressure, youth and school indicators, "
        "and newcomer flows at municipality level."
    )

st.divider()
st.caption("Use the sidebar to navigate between pages.")
