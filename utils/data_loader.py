import streamlit as st
import pandas as pd
import json
import copy

DATA_DIR = "data/processed"

REGION_NL_TO_EN = {
    "Vlaams Gewest": "Flanders region",
    "Brussels Hoofdstedelijk Gewest": "Brussels-Capital region",
    "Waals Gewest": "Walloon region",
}

MERGER_MAP = {
    "12041": ["12030","12034"],
    "23106": ["23023","23024","23032"],
    "37021": ["37007","37018"],
    "37022": ["37012","37015"],
    "44083": ["44001","44011"],
    "44084": ["44012","44029"],
    "44085": ["44034","44036","44072","44080"],
    "44086": ["44048","44012"],
    "44087": ["44045","44073"],
    "44088": ["44040","44043","44049"],
    "45068": ["45041","45059"],
    "46029": ["46003","46025"],
    "46030": ["46013","46021","46024"],
    "55085": ["55022","55039"],
    "55086": ["55004","55035"],
    "57096": ["57064"],
    "57097": ["57027","57062"],
    "71071": ["71066","71070"],
    "71072": ["71002","71016","71022","71047","71053"],
    "72042": ["72018","72039"],
    "72043": ["72020","72029"],
    "73110": ["73006","73009"],
    "73111": ["73022","73066"],
    "82039": ["82003","82005"],
}

@st.cache_data
def load_muni():
    df = pd.read_parquet(f"{DATA_DIR}/muni_choropleth.parquet")
    df["region_en"] = df["TX_RGN_DESCR_NL"].map(REGION_NL_TO_EN)
    return df

@st.cache_data
def load_region():
    return pd.read_parquet(f"{DATA_DIR}/region_data.parquet")

@st.cache_data
def load_origin():
    df = pd.read_parquet(f"{DATA_DIR}/../external/origin_by_municipality.parquet")
    df["region_en"] = df["TX_RGN_DESCR_NL"].map(REGION_NL_TO_EN)
    return df

@st.cache_data
def load_flanders_youth():
    return pd.read_parquet("data/external/flanders_youth.parquet")


@st.cache_data
def load_newcomers():
    """Merge the 4 Flemish integration newcomer CSVs into a long-format DataFrame with NSI codes.
    Falls back to pre-built parquet cache if CSVs are unavailable."""
    import os
    base = "data/external"
    cache = f"{base}/flanders_newcomers.parquet"

    # Fast path: use parquet cache if CSVs are missing
    csv_files = [
        f"{base}/nieuwkomers - gemeenten.csv",
        f"{base}/nieuwkomers niet-EU - gemeenten.csv",
    ]
    if not all(os.path.exists(f) for f in csv_files):
        if os.path.exists(cache):
            return pd.read_parquet(cache)
        raise FileNotFoundError(
            "Newcomer CSV files not found in data/external/ and no parquet cache exists."
        )

    def _melt(filepath, value_name):
        df = pd.read_csv(filepath, sep=";", encoding="utf-8-sig")
        df = df.rename(columns={"gemeenten": "gemeente"})
        val_cols = [c for c in df.columns if "|" in c]
        long = df.melt(id_vars=["gemeente"], value_vars=val_cols,
                       var_name="year_col", value_name=value_name)
        long["year"] = long["year_col"].str.rsplit("|", n=1).str[-1].astype(int)
        long = long.drop(columns=["year_col"])
        if not pd.api.types.is_float_dtype(long[value_name]):
            long[value_name] = (
                long[value_name].astype(str).str.replace(",", ".", regex=False)
            )
            long[value_name] = pd.to_numeric(long[value_name], errors="coerce")
        return long

    df = (
        _melt(f"{base}/nieuwkomers - gemeenten.csv", "nieuwkomers")
        .merge(_melt(f"{base}/nieuwkomers niet-EU - gemeenten.csv", "nieuwkomers_niet_eu"),
               on=["gemeente", "year"], how="outer")
        .merge(_melt(f"{base}/nieuwkomers per 1.000 inwoners 18_ jaar - gemeenten.csv",
                     "nieuwkomers_per_1000"),
               on=["gemeente", "year"], how="outer")
        .merge(_melt(f"{base}/nieuwkomers niet-EU per 1.000 inwoners 18_ jaar niet-EU -%2.csv",
                     "nieuwkomers_niet_eu_per_1000"),
               on=["gemeente", "year"], how="outer")
    )

    # Ensure numeric dtype after outer merges
    for col in ["nieuwkomers", "nieuwkomers_niet_eu", "nieuwkomers_per_1000",
                "nieuwkomers_niet_eu_per_1000"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derive EU newcomers
    df["nieuwkomers_eu"] = df["nieuwkomers"] - df["nieuwkomers_niet_eu"]

    # Attach NSI codes from origin parquet
    origin = pd.read_parquet("data/external/origin_by_municipality.parquet")
    muni_map = (
        origin[["TX_DESCR_NL", "CD_REFNIS", "TX_PROV_DESCR_NL", "TX_RGN_DESCR_NL"]]
        .drop_duplicates("TX_DESCR_NL")
    )
    df = df.merge(muni_map, left_on="gemeente", right_on="TX_DESCR_NL", how="left")
    df = df[df["TX_RGN_DESCR_NL"] == "Vlaams Gewest"].copy()
    df["CD_REFNIS"] = df["CD_REFNIS"].astype(str)
    return df


@st.cache_data
def load_geojson():
    with open(f"{DATA_DIR}/belgium_municipalities.geojson") as f:
        geo = json.load(f)
    # Apply merger map
    geo_new = copy.deepcopy(geo)
    nsi_to_feature = {feat["properties"]["NSI_CODE"]: feat for feat in geo_new["features"]}
    for new_code, old_codes in MERGER_MAP.items():
        found = [c for c in old_codes if c in nsi_to_feature]
        if found:
            new_feat = copy.deepcopy(nsi_to_feature[found[0]])
            new_feat["properties"]["NSI_CODE"] = new_code
            geo_new["features"].append(new_feat)
    return geo_new