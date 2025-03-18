import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="GEM Cleaned 2025 — Visualization App", layout="wide")
st.title("GEM Cleaned 2025 — Visualization App")

CSV_PATH = "calibrate-power-stock/gem_cleaned_2025.csv"

@st.cache_data(show_spinner=True)
def load_data(csv_path: str) -> pd.DataFrame:
    """Load the CSV with fallback encoding and convert columns to numeric."""
    # Adjust encoding if needed (e.g., 'latin-1', 'cp1252', etc.)
    df = pd.read_csv(csv_path, encoding="latin-1")

    # Convert potential numeric columns
    for col in ["Start year", "Retired year", "installed capacity MW"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

abs_path = os.path.abspath(CSV_PATH)
if not os.path.exists(abs_path):
    st.error(f"CSV file not found at {abs_path}. Check your path.")
    st.stop()

with st.spinner("Loading CSV data..."):
    df = load_data(abs_path)

st.success("Data loaded successfully!")
st.write(f"**Rows**: {len(df)}, **Columns**: {list(df.columns)}")



# A helper function to create a multiselect with an "All" option.
def multiselect_with_all(label, options, default_all=True):
    """
    Creates a multiselect for the given 'options', plus an "All (no filter)" item.
    Returns the user’s selection as a list. If "All (no filter)" is included, we treat it as no filter.
    By default, we select "All (no filter)" so that no filter is applied initially.
    """
    ALL = "All (no filter)"
    extended = [ALL] + sorted(options)

    if default_all:
        default_sel = [ALL]
    else:
        default_sel = extended

    sel = st.sidebar.multiselect(label, extended, default=default_sel)

    if ALL in sel:
        return []
    else:
        return sel

# -------------------
# 1) CREATE SIDEBAR FILTERS
# -------------------
df_filtered = df.copy()

# Filter: Plant Type
if "Plant Type" in df_filtered.columns:
    plant_types = df_filtered["Plant Type"].dropna().unique().tolist()
    selected_plant_types = multiselect_with_all("Plant Type", plant_types)
    if selected_plant_types:
        df_filtered = df_filtered[df_filtered["Plant Type"].isin(selected_plant_types)]

# Filter: Technology
if "Technology" in df_filtered.columns:
    tech_list = df_filtered["Technology"].dropna().unique().tolist()
    selected_techs = multiselect_with_all("Technology", tech_list)
    if selected_techs:
        df_filtered = df_filtered[df_filtered["Technology"].isin(selected_techs)]

# Filter: Region
if "Region" in df_filtered.columns:
    region_list = df_filtered["Region"].dropna().unique().tolist()
    selected_regions = multiselect_with_all("Region", region_list)
    if selected_regions:
        df_filtered = df_filtered[df_filtered["Region"].isin(selected_regions)]

# Filter: Subregion
if "Subregion" in df_filtered.columns:
    subreg_list = df_filtered["Subregion"].dropna().unique().tolist()
    selected_subregs = multiselect_with_all("Subregion", subreg_list)
    if selected_subregs:
        df_filtered = df_filtered[df_filtered["Subregion"].isin(selected_subregs)]

# Filter: Country/area
if "Country/area" in df_filtered.columns:
    country_list = df_filtered["Country/area"].dropna().unique().tolist()
    selected_countries = multiselect_with_all("Country/area", country_list)
    if selected_countries:
        df_filtered = df_filtered[df_filtered["Country/area"].isin(selected_countries)]

# Filter: Status
if "Status" in df_filtered.columns:
    status_list = df_filtered["Status"].dropna().unique().tolist()
    selected_status = multiselect_with_all("Status", status_list)
    if selected_status:
        df_filtered = df_filtered[df_filtered["Status"].isin(selected_status)]

# Filter: Start Year range
min_year, max_year = 1900, 2100
if "Start year" in df_filtered.columns:
    valid_years = df_filtered["Start year"].dropna()
    if not valid_years.empty:
        min_year = int(valid_years.min())
        max_year = int(valid_years.max())

start_low, start_high = st.sidebar.slider(
    "Start year range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
    step=1
)
df_filtered = df_filtered[
    df_filtered["Start year"].notna()
    & (df_filtered["Start year"] >= start_low)
    & (df_filtered["Start year"] <= start_high)
]

st.subheader("Filtered Data Summary")
st.write(f"**Rows after filtering:** {len(df_filtered)}")

# Show a random sample if large
if len(df_filtered) > 10:
    st.dataframe(df_filtered.sample(n=10, random_state=42))
else:
    st.dataframe(df_filtered)

# -------------------
# 2) CHARTS
# -------------------

# a) Total installed capacity by Status (in GW)
if (
    "Status" in df_filtered.columns
    and "installed capacity MW" in df_filtered.columns
    and len(df_filtered) > 0
):
    st.subheader("Total Installed Capacity by Status (GW)")
    cap_by_status = (
        df_filtered
        .groupby("Status", as_index=False)["installed capacity MW"]
        .sum()
        .rename(columns={"installed capacity MW": "TotalCapacityMW"})
    )
    # Convert to GW
    cap_by_status["TotalCapacityGW"] = cap_by_status["TotalCapacityMW"] / 1000.0

    chart_status = (
        alt.Chart(cap_by_status)
        .mark_bar()
        .encode(
            x=alt.X("Status:N", sort="-y"),
            y=alt.Y("TotalCapacityGW:Q", title="Installed Capacity (GW)"),
            tooltip=["Status", "TotalCapacityGW"]
        )
        .properties(width=600, height=400)
    )
    st.altair_chart(chart_status, use_container_width=True)

# b) Newly added / Cumulative capacity by Start year (in GW)
if (
    "Start year" in df_filtered.columns
    and "installed capacity MW" in df_filtered.columns
    and len(df_filtered) > 0
):
    st.subheader("Newly Added & Cumulative Capacity by Start Year (GW)")
    df_year = (
        df_filtered.dropna(subset=["Start year", "installed capacity MW"])
        .groupby("Start year", as_index=False)["installed capacity MW"]
        .sum()
        .rename(columns={"Start year": "Year", "installed capacity MW": "NewCapMW"})
    )
    df_year.sort_values("Year", inplace=True)

    # Convert to GW
    df_year["NewCapGW"] = df_year["NewCapMW"] / 1000.0
    df_year["CumulativeCapGW"] = df_year["NewCapGW"].cumsum()

    # Bar: newly added capacity in GW
    chart_new = (
        alt.Chart(df_year)
        .mark_bar()
        .encode(
            x=alt.X("Year:O", title="Start Year"),
            y=alt.Y("NewCapGW:Q", title="Newly Added Capacity (GW)"),
            tooltip=["Year", "NewCapGW"]
        )
        .properties(width=600, height=400)
    )
    st.write("**Newly Added Capacity by Year (GW)**")
    st.altair_chart(chart_new, use_container_width=True)

    # Line: cumulative capacity in GW
    chart_cum = (
        alt.Chart(df_year)
        .mark_line(point=True)
        .encode(
            x=alt.X("Year:O", title="Start Year"),
            y=alt.Y("CumulativeCapGW:Q", title="Cumulative Capacity (GW)"),
            tooltip=["Year", "CumulativeCapGW"]
        )
        .properties(width=600, height=400)
    )
    st.write("**Cumulative Installed Capacity by Year (GW)**")
    st.altair_chart(chart_cum, use_container_width=True)

