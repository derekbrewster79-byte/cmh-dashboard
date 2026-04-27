import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import os
import glob

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="Columbus (CMH) Airport Intelligence Dashboard",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Constants
# ============================================================
PEER_AIRPORTS         = ["CMH", "IND", "CVG", "CLE", "PIT", "DAY"]
ASPIRATIONAL_AIRPORTS = ["AUS", "BNA", "RDU"]
ALL_AIRPORTS          = PEER_AIRPORTS + ASPIRATIONAL_AIRPORTS
LEAKAGE_AIRPORTS      = ["CMH", "DAY", "CVG", "CLE"]

AIRPORT_NAMES = {
    "CMH": "Columbus (CMH)", "IND": "Indianapolis (IND)", "CVG": "Cincinnati (CVG)",
    "CLE": "Cleveland (CLE)", "PIT": "Pittsburgh (PIT)",  "DAY": "Dayton (DAY)",
    "AUS": "Austin (AUS)",   "BNA": "Nashville (BNA)",    "RDU": "Raleigh-Durham (RDU)",
}

PEER_COLORS = {
    "CMH": "#002F6C", "IND": "#0B76DA", "CVG": "#248F81",
    "CLE": "#A053AC", "PIT": "#C6397B", "DAY": "#86C5FA",
}
ASPIRATIONAL_COLORS = {
    "CMH": "#002F6C", "AUS": "#C6397B", "BNA": "#248F81", "RDU": "#A053AC",
}
ALL_COLORS = {**PEER_COLORS, "AUS": "#C6397B", "BNA": "#248F81", "RDU": "#A053AC"}

TEXT_COLOR  = "#0F171F"
NAVY        = "#002F6C"
TEAL        = "#248F81"
LIGHT_BLUE  = "#BDE1FD"
MED_BLUE    = "#0B76DA"
BLUSH       = "#FFCCCF"

# Use pre-filtered deploy data when present (Streamlit Cloud), else raw data (local)
BTS_DIR    = "data/deploy" if os.path.isdir("data/deploy") and any(
    f.endswith(".csv") for f in os.listdir("data/deploy")
) else "data/bts"
OUTPUT_DIR = "output"

CHART_COLORS = ["#002F6C","#0B76DA","#248F81","#A053AC","#C6397B","#86C5FA","#FFCCCF","#BDE1FD"]

MSA_CODE = "18140"

# ============================================================
# Styling
# ============================================================
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap');

    /* Apply Open Sans globally */
    html, body, [class*="css"] {
        font-family: 'Open Sans', sans-serif !important;
    }

    /* Main content area */
    .main .block-container {
        background-color: #ffffff;
        padding-top: 1.5rem;
        max-width: 1400px;
    }

    /* Headings */
    h1, h2, h3, h4 {
        font-family: 'Open Sans', sans-serif !important;
    }
    h1 { color: #002F6C !important; font-weight: 700 !important; font-size: 1.75rem !important; }
    h2 { color: #002F6C !important; font-weight: 600 !important; }
    h3 { color: #0F171F !important; font-weight: 600 !important; font-size: 1rem !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 2px solid #e8edf2;
        background-color: #ffffff;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Open Sans', sans-serif !important;
        font-weight: 600;
        font-size: 0.85rem;
        color: #0F171F !important;
        background-color: #f8f9fa !important;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        border: 1px solid #e8edf2;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #002F6C !important;
        color: #ffffff !important;
        border-color: #002F6C !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #ffffff;
        padding-top: 1rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
    }
    [data-testid="stSidebar"] * {
        color: #0F171F !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #002F6C !important;
        font-weight: 700 !important;
        font-family: 'Open Sans', sans-serif !important;
    }
    [data-testid="stMetricLabel"] {
        color: #555555 !important;
        font-size: 0.8rem !important;
        font-family: 'Open Sans', sans-serif !important;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'Open Sans', sans-serif !important;
    }

    /* Radio buttons and selectors */
    .stRadio label, .stSelectbox label, .stSlider label {
        color: #0F171F !important;
        font-family: 'Open Sans', sans-serif !important;
        font-weight: 600 !important;
    }

    /* Captions and small text */
    .stCaption, small {
        color: #666666 !important;
        font-family: 'Open Sans', sans-serif !important;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #e8edf2;
        border-radius: 6px;
    }

    /* Divider */
    hr { border-color: #e8edf2 !important; }

    /* Custom insight callout box */
    .insight-box {
        background: #f8f9fa;
        border-left: 4px solid #002F6C;
        border-radius: 0 6px 6px 0;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
        color: #0F171F;
    }

    /* Warning / info boxes */
    .stAlert {
        font-family: 'Open Sans', sans-serif !important;
    }
</style>
""", unsafe_allow_html=True)



# ============================================================
# Column sets — read only what we need from large national CSVs
# ============================================================
MARKET_COLS   = {"YEAR","MONTH","UNIQUE_CARRIER","UNIQUE_CARRIER_NAME","CARRIER","CARRIER_NAME",
                 "ORIGIN","ORIGIN_CITY_NAME","DEST","DEST_CITY_NAME","PASSENGERS","FREIGHT","DISTANCE","CLASS"}
SEGMENT_EXTRA = {"SEATS","DEPARTURES_SCHEDULED","DEPARTURES_PERFORMED","AIRCRAFT_TYPE","AIRCRAFT_GROUP","AIR_TIME"}
SEGMENT_COLS  = MARKET_COLS | SEGMENT_EXTRA
NUMERIC_COLS  = ["PASSENGERS","SEATS","DEPARTURES_PERFORMED","DEPARTURES_SCHEDULED",
                 "FREIGHT","DISTANCE","AIR_TIME","YEAR","MONTH"]


# ============================================================
# Data Loaders
# ============================================================
@st.cache_data(show_spinner="Loading T-100 flight data…")
def load_bts_data():
    market_frames, segment_frames = [], []
    files = [f for f in glob.glob(os.path.join(BTS_DIR, "*.csv"))
             if "ontime" not in os.path.basename(f).lower()]
    if not files:
        return pd.DataFrame(), pd.DataFrame()

    for f in files:
        try:
            header   = pd.read_csv(f, nrows=0, encoding="latin-1")
            all_cols = {c.strip().upper(): c.strip() for c in header.columns}
            is_seg   = "DEPARTURES_PERFORMED" in all_cols and "SEATS" in all_cols
            want     = SEGMENT_COLS if is_seg else MARKET_COLS
            usecols  = [orig for norm, orig in all_cols.items() if norm in want]

            df = pd.read_csv(f, usecols=usecols, encoding="latin-1", low_memory=False)
            df.columns = df.columns.str.strip().str.upper()
            if "ORIGIN" in df.columns:
                df = df[df["ORIGIN"].isin(ALL_AIRPORTS)].copy()
            for col in NUMERIC_COLS:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            (segment_frames if is_seg else market_frames).append(df)
        except Exception as e:
            st.warning(f"Could not read {os.path.basename(f)}: {e}")

    market  = pd.concat(market_frames,  ignore_index=True) if market_frames  else pd.DataFrame()
    segment = pd.concat(segment_frames, ignore_index=True) if segment_frames else pd.DataFrame()
    return market, segment


@st.cache_data(show_spinner="Loading international market data…")
def load_intl_data():
    path = os.path.join(BTS_DIR, "intl_market_summary.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.str.strip().str.upper()
    for col in ["PASSENGERS", "YEAR", "MONTH", "DISTANCE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner="Loading gateway connectivity data…")
def load_gateway_data():
    """Departure frequency from peer airports to major US international gateway hubs."""
    GATEWAYS = ["JFK", "EWR", "LAX", "MIA", "IAD", "ORD", "ATL", "SFO",
                "DFW", "BOS", "IAH", "SEA", "DTW"]
    files = sorted(glob.glob(os.path.join(BTS_DIR, "T_T100D_SEGMENT_US_CARRIER_ONLY_*.csv")))
    if not files:
        return pd.DataFrame()
    rows = []
    for f in files:
        try:
            needed = {"YEAR", "ORIGIN", "DEST", "DEPARTURES_PERFORMED", "PASSENGERS"}
            df = pd.read_csv(
                f, low_memory=False,
                usecols=lambda c: c.strip().upper() in needed,
            )
            df.columns = df.columns.str.strip().str.upper()
            for col in ["DEPARTURES_PERFORMED", "PASSENGERS"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            year = int(df["YEAR"].mode()[0])
            sub  = df[df["ORIGIN"].isin(ALL_AIRPORTS) & df["DEST"].isin(GATEWAYS)]
            grp  = (
                sub.groupby(["ORIGIN", "DEST"])
                .agg(Departures=("DEPARTURES_PERFORMED", "sum"),
                     Passengers=("PASSENGERS", "sum"))
                .reset_index()
            )
            grp["Year"] = year
            rows.append(grp)
        except Exception:
            pass
    if not rows:
        return pd.DataFrame()
    result = pd.concat(rows, ignore_index=True)
    result["Departures"] = pd.to_numeric(result["Departures"], errors="coerce").fillna(0)
    result["Passengers"] = pd.to_numeric(result["Passengers"], errors="coerce").fillna(0)
    return result


@st.cache_data(show_spinner="Loading DB1B gateway connectivity data…")
def load_db1b_data():
    path = os.path.join(BTS_DIR, "db1b_gateway_connectivity.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    for col in ["Year", "Passengers"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner="Loading on-time performance data…")
def load_ontime_data():
    path = os.path.join(BTS_DIR, "ontime_summary.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip().str.upper()
        return df
    return pd.DataFrame()


@st.cache_data(show_spinner="Loading MSA demographics…")
def load_msa_data():
    annual = income = age = pd.DataFrame()
    p = os.path.join(OUTPUT_DIR, "columbus_msa_annual_acs_bls.csv")
    if os.path.exists(p):
        annual = pd.read_csv(p).dropna(subset=["total_population"])
    p2 = os.path.join(OUTPUT_DIR, "columbus_msa_income_distribution.csv")
    if os.path.exists(p2):
        income = pd.read_csv(p2)
    p3 = os.path.join(OUTPUT_DIR, "columbus_msa_age_distribution.csv")
    if os.path.exists(p3):
        age = pd.read_csv(p3)
    return annual, income, age


@st.cache_data(ttl=86400, show_spinner="Fetching employment data from Census…")
def fetch_employment_by_sector():
    """ACS C24030 — employment by industry, male + female combined, Columbus MSA 2023."""
    try:
        m_vars = [f"C24030_{str(i).zfill(3)}E" for i in range(3, 16)]
        f_vars = [f"C24030_{str(i).zfill(3)}E" for i in range(17, 30)]
        all_v  = m_vars + f_vars
        url    = "https://api.census.gov/data/2023/acs/acs1"
        params = {"get": ",".join(all_v),
                  "for": f"metropolitan statistical area/micropolitan statistical area:{MSA_CODE}"}
        r   = requests.get(url, params=params, timeout=20)
        data = r.json()
        row = {k: int(v) for k, v in zip(data[0], data[1]) if v and v.lstrip("-").isdigit()}

        labels = ["Agriculture & Mining","Construction","Manufacturing","Wholesale Trade",
                  "Retail Trade","Transportation & Warehousing","Information",
                  "Finance & Insurance","Professional & Business Services",
                  "Education & Health Care","Arts, Entertainment & Food",
                  "Other Services","Public Administration"]
        result = []
        for i, label in enumerate(labels):
            mc = f"C24030_{str(i+3).zfill(3)}E"
            fc = f"C24030_{str(i+17).zfill(3)}E"
            total = row.get(mc, 0) + row.get(fc, 0)
            result.append({"Sector": label, "Employed": total})
        df = pd.DataFrame(result)
        df = df[df["Employed"] > 5000].sort_values("Employed")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner="Fetching foreign-born population data…")
def fetch_foreign_born_regions():
    """ACS B05006 — place of birth for foreign-born Columbus MSA residents, by world region."""
    # Variable groups → world regions that map to airline route markets
    region_vars = {
        "B05006_003E": "Northern Europe",
        "B05006_010E": "Western Europe",
        "B05006_017E": "Southern Europe",
        "B05006_021E": "Eastern Europe",
        "B05006_048E": "East Asia",
        "B05006_053E": "South & Central Asia",
        "B05006_058E": "Southeast Asia",
        "B05006_091E": "Africa",
        "B05006_124E": "Caribbean",
        "B05006_131E": "Central America",
        "B05006_149E": "South America",
        "B05006_160E": "Canada",
    }
    try:
        url    = "https://api.census.gov/data/2023/acs/acs1"
        params = {
            "get": ",".join(region_vars.keys()),
            "for": f"metropolitan statistical area/micropolitan statistical area:{MSA_CODE}",
        }
        r    = requests.get(url, params=params, timeout=20)
        data = r.json()
        row  = {k: int(v) if v and v.lstrip("-").isdigit() else 0
                for k, v in zip(data[0], data[1])}
        rows = [{"Region": label, "Foreign-Born": row.get(var, 0)}
                for var, label in region_vars.items()]
        df = pd.DataFrame(rows)
        df = df[df["Foreign-Born"] > 0].sort_values("Foreign-Born", ascending=True)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner="Fetching peer MSA demographics…")
def fetch_peer_msa_demographics():
    """ACS 2023 1-year: income, education, age for peer airport MSAs."""
    PEER_MSAS = {
        "18140": "Columbus (CMH)",
        "26900": "Indianapolis (IND)",
        "17140": "Cincinnati (CVG)",
        "38300": "Pittsburgh (PIT)",
        "12420": "Austin (AUS)",
        "34980": "Nashville (BNA)",
        "39580": "Raleigh-Durham (RDU)",
    }
    vars_str = ",".join([
        "B19013_001E",  # median HH income
        "B01002_001E",  # median age
        "B15003_001E",  # adults 25+ (education denominator)
        "B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E",  # bachelor's+
        "B19001_001E",  # total households
        "B19001_014E", "B19001_015E", "B19001_016E", "B19001_017E",  # $100K+
    ])
    url     = "https://api.census.gov/data/2023/acs/acs1"
    results = []
    for msa_code, label in PEER_MSAS.items():
        try:
            r    = requests.get(url, params={
                "get": vars_str,
                "for": f"metropolitan statistical area/micropolitan statistical area:{msa_code}",
            }, timeout=20)
            data = r.json()
            row  = dict(zip(data[0], data[1]))
            def _i(k): return int(row.get(k, 0) or 0)
            total_25    = max(_i("B15003_001E"), 1)
            bach_plus   = sum(_i(f"B15003_0{n:02d}E") for n in [22, 23, 24, 25])
            total_hh    = max(_i("B19001_001E"), 1)
            hh_100k     = sum(_i(f"B19001_0{n:02d}E") for n in [14, 15, 16, 17])
            hh_150k     = sum(_i(f"B19001_0{n:02d}E") for n in [16, 17])
            results.append({
                "MSA":             label,
                "Median_HH_Income":  _i("B19013_001E"),
                "Median_Age":        float(row.get("B01002_001E", 0) or 0),
                "Bachelors_Pct":     round(bach_plus / total_25 * 100, 1),
                "HH_100k_Plus_Pct":  round(hh_100k  / total_hh * 100, 1),
                "HH_150k_Plus_Pct":  round(hh_150k  / total_hh * 100, 1),
            })
        except Exception:
            pass
    return pd.DataFrame(results)


# ============================================================
# Load all data
# ============================================================
market_df, segment_df = load_bts_data()
ontime_df             = load_ontime_data()
intl_df               = load_intl_data()
gateway_df            = load_gateway_data()
db1b_df               = load_db1b_data()
msa_annual, msa_income, msa_age = load_msa_data()
data_loaded = not market_df.empty

@st.cache_data(show_spinner="Loading hub connection data…")
def load_hub_onward(year=2024, top_hubs=4, top_onward=4):
    """Load onward connections from CMH's top hub airports for the Sankey diagram."""
    # Use pre-computed files if available (Streamlit Cloud deploy data is airport-filtered
    # and doesn't contain hub airport rows needed for onward connections)
    pre_hubs   = os.path.join(BTS_DIR, "sankey_cmh_hubs.csv")
    pre_onward = os.path.join(BTS_DIR, "sankey_hub_onward.csv")
    if os.path.exists(pre_hubs) and os.path.exists(pre_onward):
        cmh_hubs   = pd.read_csv(pre_hubs)
        hub_onward = pd.read_csv(pre_onward)
        cmh_hubs["cmh_pax"]   = pd.to_numeric(cmh_hubs["cmh_pax"],   errors="coerce")
        hub_onward["pax"]     = pd.to_numeric(hub_onward["pax"],      errors="coerce")
        return cmh_hubs, hub_onward

    fname = os.path.join(BTS_DIR, f"T_T100D_MARKET_US_CARRIER_ONLY_{year}.csv")
    if not os.path.exists(fname):
        fname = sorted(glob.glob(os.path.join(BTS_DIR, "T_T100D_MARKET_US_CARRIER_ONLY_*.csv")))[-1]
    df = pd.read_csv(fname, usecols=["ORIGIN","DEST","PASSENGERS"], low_memory=False)
    cmh_out = (df[df["ORIGIN"]=="CMH"].groupby("DEST")["PASSENGERS"]
               .sum().sort_values(ascending=False).head(top_hubs))
    hubs = cmh_out.index.tolist()
    onward_rows = []
    for hub in hubs:
        top = (df[(df["ORIGIN"]==hub) & (~df["DEST"].isin(["CMH"]+hubs))]
               .groupby("DEST")["PASSENGERS"].sum()
               .sort_values(ascending=False).head(top_onward))
        for dest, pax in top.items():
            onward_rows.append({"hub": hub, "dest": dest, "pax": pax})
    return cmh_out.reset_index().rename(columns={"DEST":"hub","PASSENGERS":"cmh_pax"}), pd.DataFrame(onward_rows)


# ============================================================
# Helpers
# ============================================================
def fy(df, yr, col="YEAR"):
    return df[(df[col] >= yr[0]) & (df[col] <= yr[1])]

def fa(df, airports, col="ORIGIN"):
    return df[df[col].isin(airports)]

def name_map(cmap):
    return {AIRPORT_NAMES.get(k, k): v for k, v in cmap.items()}

def insight(text, sentiment="positive"):
    if sentiment == "risk":
        border, bg, icon = "#C6397B", "#FEF2F5", "&#9888;&#xFE0F;"
    elif sentiment == "neutral":
        border, bg, icon = "#94a3b8", "#F8F9FA", "&#128202;"
    else:
        border, bg, icon = TEAL, "#F0FAF8", "&#128161;"
    st.markdown(
        f"<div style='background:{bg}; border-left:4px solid {border}; border-radius:0 8px 8px 0; "
        f"padding:10px 16px; margin:6px 0 14px 0;'>"
        f"<span style='font-size:13px; color:{TEXT_COLOR}; font-style:italic;'>{icon} {text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

def exec_summary(text):
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(0,47,108,0.04),rgba(36,143,129,0.10)); "
        f"border-radius:10px; padding:14px 20px; margin:0 0 22px 0; "
        f"border:1px solid rgba(36,143,129,0.28);'>"
        f"<span style='font-size:14px; font-weight:600; color:{NAVY}; font-family:Open Sans,sans-serif;'>"
        f"{text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

def covid_band(fig):
    """Add a light COVID-19 shaded band over 2020–2021 on numeric-year charts."""
    fig.add_vrect(
        x0=2019.5, x1=2021.5,
        fillcolor="#FFCCCF", opacity=0.22, layer="below", line_width=0,
        annotation_text="COVID-19", annotation_position="top left",
        annotation_font=dict(size=9, color="#C6397B", family="Open Sans"),
    )
    return fig

def layout(fig, title, height=420, legend=True):
    fig.update_layout(
        title=dict(text=title, font=dict(family="Open Sans", size=15, color=TEXT_COLOR)),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Open Sans", color=TEXT_COLOR, size=11),
        height=height,
        margin=dict(t=60, b=48, l=60, r=110, autoexpand=True),
        showlegend=legend,
        legend=dict(bgcolor="white", bordercolor="#e8edf2", borderwidth=1, font=dict(size=10)),
        xaxis=dict(showgrid=True, gridcolor="#f0f2f5", linecolor="#e8edf2",
                   tickfont=dict(size=10), automargin=True),
        yaxis=dict(showgrid=True, gridcolor="#f0f2f5", linecolor="#e8edf2",
                   tickfont=dict(size=10), automargin=True),
    )
    for trace in fig.data:
        if hasattr(trace, "cliponaxis"):
            trace.update(cliponaxis=False)
    return fig

def gauge_fig(value, title, suffix="%", max_val=100, threshold=85):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"family": "Open Sans", "size": 26, "color": NAVY}},
        title={"text": title, "font": {"family": "Open Sans", "size": 12, "color": TEXT_COLOR}},
        domain={"x": [0, 1], "y": [0.12, 1.0]},
        gauge={
            "axis": {"range": [60, max_val], "tickfont": {"family": "Open Sans", "size": 8},
                     "tickwidth": 1, "tickcolor": "#CBD5E0"},
            "bar":  {"color": NAVY, "thickness": 0.28},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [60, 75],          "color": "#fce8ea"},
                {"range": [75, threshold],   "color": LIGHT_BLUE},
                {"range": [threshold, max_val], "color": "#d6efe9"},
            ],
            "threshold": {"line": {"color": TEAL, "width": 3}, "thickness": 0.75, "value": threshold},
        },
    ))
    fig.update_layout(paper_bgcolor="white", height=260,
                      margin=dict(t=20, b=40, l=30, r=30),
                      font=dict(family="Open Sans"))
    return fig


# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    # Company logo — place your logo file at assets/logos/company_logo.png
    _company_logo = "assets/logos/company_logo.png"
    if os.path.exists(_company_logo):
        st.image(_company_logo, use_container_width=True)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"## ✈ CMH Dashboard")
    st.caption("John Glenn Columbus International Airport")
    st.markdown("---")
    st.markdown("### Filters")

    avail_years = sorted(market_df["YEAR"].dropna().unique().astype(int)) if data_loaded else list(range(2019, 2026))
    year_range  = st.slider("Year Range", min_value=min(avail_years), max_value=max(avail_years),
                            value=(min(avail_years), max(avail_years)))

    view = st.radio("Airport Set", ["Peer Airports", "Aspirational Airports", "All Airports"])
    if view == "Peer Airports":
        display_airports, color_map = PEER_AIRPORTS, PEER_COLORS
        st.caption("CMH · IND · CVG · CLE · PIT · DAY")
    elif view == "Aspirational Airports":
        display_airports, color_map = ["CMH"] + ASPIRATIONAL_AIRPORTS, ASPIRATIONAL_COLORS
        st.caption("CMH · AUS · BNA · RDU")
    else:
        display_airports, color_map = ALL_AIRPORTS, ALL_COLORS
        st.caption("CMH · IND · CVG · CLE · PIT · DAY · AUS · BNA · RDU")

    st.markdown("---")
    st.markdown("**Data Sources**")
    st.caption("BTS T-100 Domestic Market & Segment")
    st.caption("BTS On-Time Performance (auto-downloaded)")
    st.caption("U.S. Census ACS 1-Year / FRED")

    if data_loaded:
        latest_data_yr = int(market_df["YEAR"].max())
        st.markdown("---")
        st.caption(f"Data through: **{latest_data_yr}**")
    else:
        st.warning("No T-100 data found. Add CSVs to `data/bts/`.")

# Global city name lookup (keyed by airport code → first city word)
dest_city = (
    market_df[["DEST","DEST_CITY_NAME"]].drop_duplicates()
    .set_index("DEST")["DEST_CITY_NAME"]
    .str.split(",").str[0].to_dict()
) if data_loaded and not market_df.empty else {}


# ============================================================
# Header
# ============================================================
def kpi_card(fa_icon, label, value, delta, delta_color=TEAL, border_color=NAVY):
    return (
        f"<div style='background:white; border-left:4px solid {border_color}; border-radius:8px; "
        f"padding:16px 20px; box-shadow:0 1px 5px rgba(0,0,0,0.07); height:100%; box-sizing:border-box;'>"
        f"<div style='margin-bottom:10px;'>"
        f"<i class='{fa_icon}' style='font-size:26px; color:{border_color};'></i>"
        f"</div>"
        f"<div style='font-family:Open Sans,sans-serif; font-size:10px; color:#6b7280; "
        f"text-transform:uppercase; letter-spacing:0.07em; margin-bottom:4px;'>{label}</div>"
        f"<div style='font-family:Open Sans,sans-serif; font-size:28px; font-weight:700; "
        f"color:{NAVY}; line-height:1.1;'>{value}</div>"
        f"<div style='font-family:Open Sans,sans-serif; font-size:11px; color:{delta_color}; "
        f"margin-top:6px;'>{delta}</div>"
        f"</div>"
    )

if data_loaded:
    latest_yr  = int(market_df["YEAR"].max())
    prev_yr    = latest_yr - 1
    cmh_latest = market_df[(market_df["ORIGIN"]=="CMH")&(market_df["YEAR"]==latest_yr)]["PASSENGERS"].sum()
    cmh_prev   = market_df[(market_df["ORIGIN"]=="CMH")&(market_df["YEAR"]==prev_yr)]["PASSENGERS"].sum()
    yoy        = (cmh_latest - cmh_prev) / cmh_prev * 100 if cmh_prev > 0 else 0
    cmh_dests_now  = market_df[(market_df["ORIGIN"]=="CMH")&(market_df["YEAR"]==latest_yr)]["DEST"].nunique()
    cmh_dests_prev = market_df[(market_df["ORIGIN"]=="CMH")&(market_df["YEAR"]==prev_yr)]["DEST"].nunique()
    dest_delta = cmh_dests_now - cmh_dests_prev

    h1, h_cards = st.columns([3, 3])
    with h1:
        st.markdown("## John Glenn Columbus International")
        st.caption("Airport Intelligence Dashboard · Competitive & Market Analysis")
    with h_cards:
        yoy_color   = TEAL if yoy >= 0 else "#C6397B"
        yoy_sign    = "+" if yoy >= 0 else ""
        yoy_arrow   = "▲" if yoy >= 0 else "▼"
        dest_sign   = f"+{dest_delta}" if dest_delta >= 0 else str(dest_delta)
        dest_color  = TEAL if dest_delta >= 0 else "#C6397B"
        pax_delta   = f"{yoy_arrow} {abs(yoy):.1f}% vs {prev_yr}"
        yoy_delta   = f"vs {prev_yr} ({cmh_prev/1e6:.2f}M)"
        dest_delta_s = f"{dest_sign} vs {prev_yr}"
        card1 = kpi_card("fa-solid fa-person-walking-luggage", "Annual Passengers",
                          f"{cmh_latest/1e6:.2f}M", pax_delta,
                          delta_color=yoy_color, border_color=NAVY)
        card2 = kpi_card("fa-solid fa-plane", "YoY Growth",
                          f"{yoy_sign}{yoy:.1f}%", yoy_delta,
                          delta_color="#6b7280", border_color=TEAL)
        card3 = kpi_card("fa-solid fa-map-location-dot", "Nonstop Destinations",
                          str(cmh_dests_now), dest_delta_s,
                          delta_color=dest_color, border_color=MED_BLUE)
        cards_html = (
            "<div style='display:flex; gap:12px; align-items:stretch; height:100%;'>"
            f"<div style='flex:1;'>{card1}</div>"
            f"<div style='flex:1;'>{card2}</div>"
            f"<div style='flex:1;'>{card3}</div>"
            "</div>"
        )
        st.markdown(cards_html, unsafe_allow_html=True)
else:
    st.markdown("## John Glenn Columbus International")
    st.caption("Airport Intelligence Dashboard · Competitive & Market Analysis")

st.markdown("---")


# ============================================================
# Tabs
# ============================================================
tab_overview, tab_msa, tab_competitive, tab_market, tab_ops, tab_intl, tab_internal_1, tab_internal_2 = st.tabs([
    "✈  Columbus Overview",
    "🏙  Columbus MSA",
    "📊  Competitive Analysis",
    "🎯  Market Opportunity",
    "⚙️  Operational Insights",
    "🌍  International Opportunity",
    # ── Internal tabs: rename and populate at work ──
    "📋  Tab 7",   # rename e.g. "📋  Stakeholder View"
    "📈  Tab 8",   # rename e.g. "📈  Financial Model"
])


# ══════════════════════════════════════════════════════════════
# TAB 1 · CMH OVERVIEW
# ══════════════════════════════════════════════════════════════
with tab_overview:
    if not data_loaded:
        st.info("Add BTS T-100 CSV files to `data/bts/` to populate this section.")
    else:
        cmh_annual = (market_df[market_df["ORIGIN"]=="CMH"]
                      .groupby("YEAR")["PASSENGERS"].sum().reset_index())
        _ov_yr   = int(cmh_annual["YEAR"].max())
        _ov_pax  = cmh_annual[cmh_annual["YEAR"]==_ov_yr]["PASSENGERS"].sum()
        _ov_prev = cmh_annual[cmh_annual["YEAR"]==_ov_yr-1]["PASSENGERS"].sum()
        _ov_yoy  = (_ov_pax - _ov_prev) / _ov_prev * 100 if _ov_prev > 0 else 0
        _ov_dests = market_df[(market_df["ORIGIN"]=="CMH")&(market_df["YEAR"]==_ov_yr)]["DEST"].nunique()
        _ov_sign  = "up" if _ov_yoy >= 0 else "down"
        _ov_base  = cmh_annual[cmh_annual["YEAR"]==2019]["PASSENGERS"].sum()
        _ov_vs_base = (_ov_pax - _ov_base) / _ov_base * 100 if _ov_base > 0 else 0
        _ov_recovered = _ov_pax >= _ov_base

        # ── Executive Summary Card ───────────────────────────────
        _bullet_css = "margin:0; padding:0; list-style:none;"
        _li_css     = "padding: 5px 0; font-size:13px; color:#1f2937; line-height:1.5;"
        _icon_good  = f"<span style='color:{TEAL}; font-weight:700; margin-right:6px;'>✓</span>"
        _icon_opp   = f"<span style='color:#d97706; font-weight:700; margin-right:6px;'>→</span>"

        _yoy_str    = f"{'▲' if _ov_yoy >= 0 else '▼'} {abs(_ov_yoy):.1f}% YoY"
        _base_str   = (f"{'▲' if _ov_vs_base >= 0 else '▼'} {abs(_ov_vs_base):.1f}% vs. 2019 baseline")
        _recovery   = "Fully recovered past 2019 baseline" if _ov_recovered else f"Approaching 2019 baseline ({_ov_vs_base:.1f}%)"

        st.markdown(
            f"<div style='background:linear-gradient(135deg,rgba(0,47,108,0.04),rgba(36,143,129,0.08)); "
            f"border-radius:12px; padding:20px 24px; margin:0 0 24px 0; "
            f"border:1px solid rgba(36,143,129,0.28);'>"

            # Header
            f"<div style='font-size:16px; font-weight:700; color:{NAVY}; "
            f"font-family:Open Sans,sans-serif; margin-bottom:14px; "
            f"padding-bottom:10px; border-bottom:1px solid rgba(0,47,108,0.12);'>"
            f"John Glenn Columbus International (CMH) — Executive Summary"
            f"</div>"

            # Two columns via inline table
            f"<table style='width:100%; border-collapse:collapse; font-family:Open Sans,sans-serif;'><tr>"

            # Left — Strengths
            f"<td style='width:50%; vertical-align:top; padding-right:20px; "
            f"border-right:1px solid rgba(0,47,108,0.10);'>"
            f"<div style='font-size:11px; font-weight:700; text-transform:uppercase; "
            f"letter-spacing:.07em; color:{TEAL}; margin-bottom:8px;'>Current Health</div>"
            f"<ul style='{_bullet_css}'>"
            f"<li style='{_li_css}'>{_icon_good}<b>{_ov_pax/1e6:.2f}M passengers</b> in {_ov_yr} &nbsp;·&nbsp; {_yoy_str} &nbsp;·&nbsp; {_base_str}</li>"
            f"<li style='{_li_css}'>{_icon_good}{_recovery} — sustained positive momentum post-COVID</li>"
            f"<li style='{_li_css}'>{_icon_good}<b>{_ov_dests} nonstop destinations</b>, 55+ total including LCK — a record high for the Columbus market</li>"
            f"<li style='{_li_css}'>{_icon_good}<b>Air Canada Toronto (YYZ)</b> launched May 2025 — CMH's first regular international scheduled service, carrying 44,994 passengers in year one</li>"
            f"<li style='{_li_css}'>{_icon_good}Strong carrier diversity: Southwest (31%), American, Delta, United, and 7 additional airlines maintaining competitive fares</li>"
            f"</ul></td>"

            # Right — Opportunities
            f"<td style='width:50%; vertical-align:top; padding-left:20px;'>"
            f"<div style='font-size:11px; font-weight:700; text-transform:uppercase; "
            f"letter-spacing:.07em; color:#d97706; margin-bottom:8px;'>Strategic Opportunities</div>"
            f"<ul style='{_bullet_css}'>"
            f"<li style='{_li_css}'>{_icon_opp}<b>Air Canada Montréal (YUL) launching May 1, 2026</b> — first-ever CMH–YUL nonstop; YUL is a US preclearance hub connecting CMH to Air Canada's European network</li>"
            f"<li style='{_li_css}'>{_icon_opp}<b>CMH Next terminal expansion</b> underway — positions the airport to handle higher volumes and attract new airline partners</li>"
            f"<li style='{_li_css}'>{_icon_opp}<b>International connectivity gap</b> vs. aspirational peers (AUS: 12 routes, BNA/RDU: 5) — open runway for additional Mexico, Caribbean, and transatlantic routes as demand matures</li>"
            f"<li style='{_li_css}'>{_icon_opp}<b>No airline club lounges</b> (United Club, Delta Sky Club, Admirals Club) — a clear ask to CMH's top carriers to deepen commitment and improve business traveler experience</li>"
            f"<li style='{_li_css}'>{_icon_opp}Growing Columbus tech and professional services economy is generating latent business travel demand that larger aircraft and new routes can unlock</li>"
            f"</ul></td>"

            f"</tr></table></div>",
            unsafe_allow_html=True,
        )

        # ── 1. Passenger Volume Trend ───────────────────────────
        st.markdown("### Passenger Volume Trend — Columbus (CMH)")
        cmh_annual["YoY_pct"] = cmh_annual["PASSENGERS"].pct_change() * 100

        bar_colors = []
        for _, row in cmh_annual.iterrows():
            yr    = int(row["YEAR"])
            yoy_v = row["YoY_pct"]
            if yr == 2020:
                bar_colors.append("#C6397B")
            elif yr == 2021:
                bar_colors.append("#FFCCCF")
            elif not pd.isna(yoy_v) and yoy_v < 0:
                bar_colors.append(LIGHT_BLUE)
            else:
                bar_colors.append(NAVY)

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=cmh_annual["YEAR"],
            y=cmh_annual["PASSENGERS"] / 1e6,
            marker_color=bar_colors,
            marker_line_width=0,
            text=[f"{v/1e6:.2f}M" for v in cmh_annual["PASSENGERS"]],
            textposition="outside",
            textfont=dict(family="Open Sans", size=10, color=TEXT_COLOR),
            name="Passengers",
            hovertemplate="<b>%{x}</b><br>%{y:.2f}M passengers<extra></extra>",
            cliponaxis=False,
        ))

        # 2019 baseline
        base_pax = cmh_annual[cmh_annual["YEAR"]==2019]["PASSENGERS"].sum() / 1e6
        if base_pax > 0:
            fig_trend.add_hline(y=base_pax, line_dash="dot", line_color="#e2e8f0", line_width=1.5,
                                annotation_text="2019 baseline",
                                annotation_font=dict(size=9, color="#9ca3af"),
                                annotation_position="top right")

        fig_trend.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="Open Sans", color=TEXT_COLOR, size=11),
            height=360,
            margin=dict(t=40, b=48, l=60, r=40),
            bargap=0.28,
            showlegend=False,
            xaxis=dict(tickmode="linear", dtick=1, tickformat="d",
                       showgrid=True, gridcolor="#f0f2f5"),
            yaxis=dict(title="Passengers (millions)",
                       range=[0, cmh_annual["PASSENGERS"].max()/1e6 * 1.22],
                       showgrid=True, gridcolor="#f0f2f5"),
        )
        covid_band(fig_trend)
        st.plotly_chart(fig_trend, use_container_width=True)
        if len(cmh_annual) >= 2:
            latest_trend_yr  = int(cmh_annual["YEAR"].max())
            latest_trend_pax = cmh_annual[cmh_annual["YEAR"]==latest_trend_yr]["PASSENGERS"].sum()
            prev_trend_pax   = cmh_annual[cmh_annual["YEAR"]==latest_trend_yr-1]["PASSENGERS"].sum()
            peak_yr          = int(cmh_annual.loc[cmh_annual["PASSENGERS"].idxmax(), "YEAR"])
            trend_chg        = (latest_trend_pax - prev_trend_pax) / prev_trend_pax * 100 if prev_trend_pax > 0 else 0
            trend_dir        = "up" if trend_chg > 0 else "down"
            insight(f"Columbus (CMH) carried <b>{latest_trend_pax/1e6:.2f}M passengers</b> in {latest_trend_yr}, "
                    f"{trend_dir} <b>{abs(trend_chg):.1f}%</b> from {latest_trend_yr-1}"
                    f"{' — a new all-time record' if latest_trend_yr == peak_yr else f', approaching its {peak_yr} peak'}.")

        # ── 1b. Waterfall — Year-over-Year Passenger Delta ─────
        st.markdown("### Annual Passenger Change — Columbus (CMH)")
        st.caption("Each bar shows the net gain or loss vs. the prior year. Pink = decline, teal = growth, navy = base year.")
        cmh_wf = (market_df[market_df["ORIGIN"]=="CMH"]
                  .groupby("YEAR")["PASSENGERS"].sum().reset_index()
                  .sort_values("YEAR"))
        if len(cmh_wf) >= 2:
            wf_years   = cmh_wf["YEAR"].astype(int).tolist()
            wf_pax     = cmh_wf["PASSENGERS"].tolist()
            wf_deltas  = [wf_pax[0]] + [wf_pax[i] - wf_pax[i-1] for i in range(1, len(wf_pax))]
            wf_measure = ["absolute"] + ["relative"] * (len(wf_pax) - 1)
            wf_text    = [f"{wf_deltas[0]/1e6:.2f}M"] + [
                f"+{d/1e3:.0f}K" if d >= 0 else f"{d/1e3:.0f}K" for d in wf_deltas[1:]
            ]
            fig_wf = go.Figure(go.Waterfall(
                orientation="v",
                measure=wf_measure,
                x=[str(y) for y in wf_years],
                y=[d/1e6 for d in wf_deltas],
                connector=dict(line=dict(color="#e8edf2", width=1.5, dash="dot")),
                increasing=dict(marker=dict(color=TEAL)),
                decreasing=dict(marker=dict(color="#C6397B")),
                totals=dict(marker=dict(color=NAVY)),
                text=wf_text,
                textposition="outside",
                textfont=dict(family="Open Sans", size=10, color=TEXT_COLOR),
                hovertemplate="<b>%{x}</b><br>Change: %{y:+.2f}M passengers<extra></extra>",
            ))
            fig_wf = layout(fig_wf, "Columbus (CMH) Annual Passenger Change vs. Prior Year", height=360, legend=False)
            fig_wf.update_layout(yaxis_title="Passengers (millions)", xaxis_title="Year",
                                 yaxis=dict(tickformat=".1f", ticksuffix="M"))
            st.plotly_chart(fig_wf, use_container_width=True)
            worst_yr  = wf_years[wf_deltas[1:].index(min(wf_deltas[1:])) + 1]
            best_yr   = wf_years[wf_deltas[1:].index(max(wf_deltas[1:])) + 1]
            best_val  = max(wf_deltas[1:])
            worst_val = min(wf_deltas[1:])
            insight(f"Columbus's biggest single-year drop was <b>{worst_val/1e6:.2f}M passengers</b> in <b>{worst_yr}</b> (COVID-19); "
                    f"the strongest recovery was <b>+{best_val/1e3:.0f}K passengers</b> in <b>{best_yr}</b>.", sentiment="neutral")

        # ── 4. Airline Market Share + On-Time (2 col) ───────────
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### Airline Market Share — Columbus (CMH)")
            mkt_yr = st.selectbox("Year", sorted(market_df["YEAR"].unique(), reverse=True), key="mkt_yr")
            carrier_col = "UNIQUE_CARRIER_NAME" if "UNIQUE_CARRIER_NAME" in market_df.columns else "CARRIER_NAME"
            share = (market_df[(market_df["ORIGIN"]=="CMH")&(market_df["YEAR"]==mkt_yr)]
                     .groupby(carrier_col)["PASSENGERS"].sum().reset_index()
                     .sort_values("PASSENGERS", ascending=False))
            if len(share) > 7:
                top   = share.head(7).copy()
                other = pd.DataFrame([{carrier_col: "Other", "PASSENGERS": share.iloc[7:]["PASSENGERS"].sum()}])
                share = pd.concat([top, other], ignore_index=True)
            fig_donut = go.Figure(go.Pie(
                labels=share[carrier_col], values=share["PASSENGERS"],
                hole=0.52, textinfo="percent",
                textfont=dict(family="Open Sans", size=10),
                marker=dict(colors=CHART_COLORS),
            ))
            fig_donut.update_layout(
                paper_bgcolor="white", height=360,
                margin=dict(t=20, b=20, l=20, r=20),
                font=dict(family="Open Sans"),
                legend=dict(font=dict(size=9), bgcolor="white"),
                annotations=[dict(text="Columbus", x=0.5, y=0.5, font_size=13,
                                  font_family="Open Sans", font_color=NAVY, showarrow=False)],
            )
            st.plotly_chart(fig_donut, use_container_width=True)
            if not share.empty:
                top_carrier = share.iloc[0]
                top_pct = top_carrier["PASSENGERS"] / share["PASSENGERS"].sum() * 100
                n_carriers = (len(share[share["PASSENGERS"]>0])-1
                              if "Other" in share[carrier_col].values else len(share))
                insight(f"<b>{top_carrier[carrier_col]}</b> leads Columbus (CMH) with <b>{top_pct:.0f}%</b> of passengers "
                        f"in {mkt_yr}, with {n_carriers} airlines serving the airport.")

        with col_b:
            st.markdown("### On-Time Performance — Columbus (CMH)")
            if ontime_df.empty:
                st.info("On-time data not found.")
            else:
                ot_year    = st.selectbox("Year", sorted(ontime_df["YEAR"].unique(), reverse=True), key="ot_yr")
                cmh_ot_row = ontime_df[(ontime_df["AIRPORT"]=="CMH")&(ontime_df["YEAR"]==ot_year)]
                if not cmh_ot_row.empty:
                    r = cmh_ot_row.iloc[0]
                    g1, g2, g3 = st.columns(3)
                    with g1:
                        st.plotly_chart(gauge_fig(r["DEP_ONTIME_PCT"], "Departures"), use_container_width=True)
                    with g2:
                        st.plotly_chart(gauge_fig(r["ARR_ONTIME_PCT"], "Arrivals"), use_container_width=True)
                    with g3:
                        st.plotly_chart(gauge_fig(r["COMBINED_ONTIME_PCT"], "Combined"), use_container_width=True)
                    ot_all = ontime_df[ontime_df["AIRPORT"].isin(display_airports)].copy()
                    fig_ot = go.Figure()
                    for ap in display_airports:
                        ap_ot = ot_all[ot_all["AIRPORT"]==ap].sort_values("YEAR")
                        if ap_ot.empty:
                            continue
                        is_cmh = ap == "CMH"
                        fig_ot.add_trace(go.Scatter(
                            x=ap_ot["YEAR"], y=ap_ot["COMBINED_ONTIME_PCT"],
                            mode="lines+markers",
                            name=AIRPORT_NAMES.get(ap, ap),
                            line=dict(color=color_map.get(ap, "#aaa"),
                                      width=3.5 if is_cmh else 1.8),
                            marker=dict(size=9 if is_cmh else 6,
                                        line=dict(color="white", width=1.5 if is_cmh else 1)),
                            hovertemplate=f"<b>{AIRPORT_NAMES.get(ap, ap)}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
                        ))
                    fig_ot = layout(fig_ot, "Combined On-Time % — All Airports", height=360)
                    fig_ot.update_layout(yaxis_title="On-Time %", xaxis_title="Year",
                                         yaxis_ticksuffix="%",
                                         xaxis=dict(tickmode="linear", dtick=1, tickformat="d"),
                                         hovermode="x unified")
                    st.plotly_chart(fig_ot, use_container_width=True)
                    peer_ot  = ontime_df[(ontime_df["AIRPORT"].isin(display_airports))&(ontime_df["YEAR"]==ot_year)]
                    cmh_rank = peer_ot.sort_values("COMBINED_ONTIME_PCT", ascending=False)["AIRPORT"].tolist()
                    rank_pos = cmh_rank.index("CMH") + 1 if "CMH" in cmh_rank else None
                    if rank_pos:
                        insight(f"Columbus (CMH)'s combined on-time rate of <b>{r['COMBINED_ONTIME_PCT']:.1f}%</b> "
                                f"in {ot_year} ranked <b>#{rank_pos} of {len(cmh_rank)}</b> among peer airports.")

        # ── 4b. Carrier Share Over Time ────────────────────────
        st.markdown("### Airline Passenger Trend by Carrier — Columbus (CMH)")
        st.caption("Stacked area shows how each airline's contribution to Columbus passenger volume has shifted over time.")
        car_col = "UNIQUE_CARRIER_NAME" if "UNIQUE_CARRIER_NAME" in market_df.columns else "CARRIER_NAME"
        car_time = (market_df[market_df["ORIGIN"]=="CMH"]
                    .groupby([car_col, "YEAR"])["PASSENGERS"].sum().reset_index())
        top_cars = car_time.groupby(car_col)["PASSENGERS"].sum().nlargest(6).index
        car_time = car_time[car_time[car_col].isin(top_cars)].copy()
        car_time = car_time.rename(columns={car_col: "Carrier"})
        if not car_time.empty:
            fig_car = px.area(car_time, x="YEAR", y="PASSENGERS", color="Carrier",
                              color_discrete_sequence=CHART_COLORS,
                              groupnorm=None)
            fig_car = layout(fig_car, "Columbus (CMH) Passenger Volume by Airline (top 6 carriers)", height=360)
            fig_car.update_layout(xaxis_title="Year", yaxis_title="Passengers",
                                  xaxis=dict(tickmode="linear", dtick=1, tickformat="d"),
                                  hovermode="x unified")
            covid_band(fig_car)
            st.plotly_chart(fig_car, use_container_width=True)
            latest_car_yr = int(car_time["YEAR"].max())
            top_carrier_row = (car_time[car_time["YEAR"]==latest_car_yr]
                               .sort_values("PASSENGERS", ascending=False).iloc[0])
            total_latest = car_time[car_time["YEAR"]==latest_car_yr]["PASSENGERS"].sum()
            top_share = top_carrier_row["PASSENGERS"] / total_latest * 100
            insight(f"<b>{top_carrier_row['Carrier']}</b> is Columbus's dominant carrier in {latest_car_yr} "
                    f"with <b>{top_share:.0f}%</b> of the top-6 carrier passenger volume — "
                    f"watch this chart for shifts in airline commitment to the Columbus market.")

        # ── 5. Nonstop Frequency ────────────────────────────────
        if not segment_df.empty:
            st.markdown("### Top Routes by Daily Nonstop Frequency — Columbus (CMH)")
            freq_yr  = int(year_range[1])
            cmh_freq = (segment_df[(segment_df["ORIGIN"]=="CMH")&(segment_df["YEAR"]==freq_yr)]
                        .groupby("DEST")["DEPARTURES_PERFORMED"].sum().reset_index())
            cmh_freq["Daily"] = (cmh_freq["DEPARTURES_PERFORMED"] / 365).round(1)
            cmh_freq = cmh_freq.sort_values("Daily", ascending=False).head(10)
            fig_freq = go.Figure(go.Bar(
                x=cmh_freq["Daily"], y=cmh_freq["DEST"],
                orientation="h", marker_color=TEAL,
                text=cmh_freq["Daily"], textposition="outside",
                textfont=dict(family="Open Sans", size=10),
            ))
            fig_freq = layout(fig_freq, f"Avg Daily Nonstop Departures from Columbus (CMH) — {freq_yr}",
                              height=340, legend=False)
            fig_freq.update_layout(xaxis_title="Daily Nonstop Departures", yaxis_title="",
                                   margin=dict(r=80))
            st.plotly_chart(fig_freq, use_container_width=True)
            top_freq_dest = cmh_freq.iloc[0]
            freq_city = dest_city.get(top_freq_dest['DEST'], top_freq_dest['DEST'])
            insight(f"<b>{freq_city} ({top_freq_dest['DEST']})</b> is Columbus's most frequent nonstop with "
                    f"~<b>{top_freq_dest['Daily']:.1f} flights/day</b> in {freq_yr} — "
                    f"{int(top_freq_dest['Daily'] * 365):,} total departures.")


        # ── 3. Route Map ────────────────────────────────────────
        st.markdown("### Columbus (CMH) Route Network — Passenger Volume Map")

        AIRPORT_COORDS = {
            # Ohio & immediate peers
            "CMH": (39.998, -82.892), "DAY": (39.902, -84.219), "CVG": (39.049, -84.668),
            "CLE": (41.412, -81.850), "TOL": (41.587, -83.808), "CAK": (40.916, -81.442),
            "IND": (39.717, -86.295), "PIT": (40.491, -80.233),
            # Aspirational
            "AUS": (30.198, -97.666), "BNA": (36.126, -86.677), "RDU": (35.878, -78.787),
            # Major hubs
            "ATL": (33.641, -84.428), "ORD": (41.974, -87.907), "DFW": (32.897, -97.038),
            "DEN": (39.856,-104.674), "LAX": (33.943,-118.408), "SFO": (37.619,-122.375),
            "JFK": (40.641, -73.778), "LGA": (40.777, -73.874), "EWR": (40.690, -74.175),
            "IAH": (29.990, -95.337), "IAD": (38.953, -77.457), "DCA": (38.852, -77.038),
            "PHX": (33.437,-112.008), "SEA": (47.450,-122.309), "MCO": (28.429, -81.309),
            "MIA": (25.796, -80.287), "FLL": (26.073, -80.153), "TPA": (27.976, -82.533),
            "MSP": (44.882, -93.222), "DTW": (42.216, -83.355), "BOS": (42.366, -71.010),
            "PHL": (39.872, -75.241), "BWI": (39.175, -76.668), "CLT": (35.214, -80.947),
            "LAS": (36.084,-115.154), "MDW": (41.787, -87.752), "SLC": (40.788,-111.978),
            "PDX": (45.589,-122.593), "STL": (38.749, -90.370), "MCI": (39.298, -94.714),
            "MSY": (29.993, -90.258), "SAT": (29.534, -98.470), "RSW": (26.536, -81.755),
            "DAL": (32.847, -96.852), "SAN": (32.734,-117.190), "OMA": (41.303, -95.894),
            "MKE": (42.947, -87.897), "SMF": (38.695,-121.591), "OKC": (35.393, -97.601),
            # Northeast / Mid-Atlantic
            "ABE": (40.652, -75.441), "ACY": (39.458, -74.577), "ALB": (42.748, -73.802),
            "BDL": (41.939, -72.683), "BGR": (44.807, -68.828), "BTV": (44.472, -73.153),
            "BUF": (42.941, -78.732), "CKB": (39.297, -80.228), "ERI": (42.083, -80.174),
            "FRG": (40.729, -73.414), "HPN": (41.067, -73.708), "ISP": (40.795, -73.100),
            "ITH": (42.491, -76.458), "MDT": (40.194, -76.763), "MHT": (42.933, -71.436),
            "ORF": (36.898, -76.013), "PHF": (37.132, -76.493), "PKB": (39.345, -81.439),
            "PVD": (41.724, -71.428), "PWM": (43.646, -70.309), "RIC": (37.505, -77.320),
            "ROC": (43.119, -77.672), "SYR": (43.111, -76.106),
            # Southeast
            "AGS": (33.370, -81.965), "BHM": (33.563, -86.754), "BTR": (30.533, -91.150),
            "CAE": (33.939, -81.120), "CHA": (35.035, -85.204), "CHS": (32.899, -80.041),
            "CSG": (32.516, -84.939), "DAB": (29.180, -81.058), "EYW": (24.556, -81.760),
            "FAY": (34.991, -78.880), "FLO": (34.185, -79.724), "GNV": (29.690, -82.272),
            "GPT": (30.407, -89.070), "GSO": (36.098, -79.937), "GSP": (34.896, -82.219),
            "HHH": (32.224, -80.698), "HSV": (34.637, -86.775), "ILM": (34.271, -77.903),
            "JAX": (30.494, -81.688), "JAN": (32.311, -90.076), "LFT": (30.205, -91.988),
            "LIT": (34.729, -92.224), "MCN": (32.693, -83.649), "MEM": (35.042, -89.977),
            "MGM": (32.301, -86.394), "MLU": (32.511, -92.038), "MOB": (30.691, -88.243),
            "MYR": (33.680, -78.928), "OAJ": (34.829, -77.612), "PNS": (30.473, -87.187),
            "ROA": (37.326, -79.975), "SDF": (38.174, -85.736), "SHV": (32.447, -93.826),
            "SJU": (18.439, -66.002), "TLH": (30.397, -84.350), "TRI": (36.475, -82.407),
            "TYS": (35.813, -83.994), "VLD": (30.782, -83.277), "VPS": (30.483, -86.525),
            # Midwest / Great Plains
            "ATW": (44.258, -88.519), "AZO": (42.235, -85.552), "CID": (41.884, -91.711),
            "CMI": (40.040, -88.278), "DBQ": (42.402, -90.710), "DLH": (46.842, -92.194),
            "DSM": (41.534, -93.663), "EVV": (38.037, -87.532), "FAR": (46.921, -96.816),
            "FNT": (42.965, -83.744), "FWA": (40.979, -85.195), "GFK": (47.949, -97.176),
            "GRB": (44.485, -88.130), "GRR": (42.881, -85.523), "ICT": (37.650, -97.433),
            "JLN": (37.152, -94.498), "LEX": (38.037, -84.606), "LNK": (40.851, -96.759),
            "MBS": (43.533, -84.080), "MKG": (43.170, -86.238), "MLI": (41.449, -90.508),
            "MOT": (48.259,-101.280), "MQT": (46.354, -87.595), "MSN": (43.140, -89.338),
            "OWB": (37.740, -87.167), "PAH": (37.060, -88.773), "PIA": (40.664, -89.693),
            "RFD": (42.195, -89.097), "RST": (43.908, -92.500), "SBN": (41.709, -86.317),
            "SGF": (37.246, -93.389), "SPI": (39.844, -89.678), "TVC": (44.741, -85.582),
            "TUL": (36.198, -95.888),
            # Mountain West
            "ABQ": (35.040,-106.609), "BIL": (45.808,-108.543), "BIS": (46.773,-100.747),
            "COS": (38.806,-104.701), "CPR": (42.908,-106.465), "DRO": (37.152,-107.754),
            "EGE": (39.642,-106.918), "ELP": (31.807,-106.378), "FOE": (38.951, -95.664),
            "FSD": (43.582, -96.742), "GJT": (39.122,-108.527), "GTF": (47.482,-111.371),
            "HLN": (46.607,-111.983), "IDA": (43.515,-112.070), "MTJ": (38.510,-107.894),
            "RAP": (44.045,-103.057), "RNO": (39.499,-119.768), "TUS": (32.116,-110.941),
            "YUM": (32.657,-114.606),
            # Texas (smaller markets)
            "ABI": (32.411, -99.682), "AMA": (35.219,-101.706), "CRP": (27.770, -97.501),
            "HRL": (26.229, -97.654), "LBB": (33.664,-101.823), "LRD": (27.544, -99.461),
            "MAF": (31.943,-102.202), "MFE": (26.176, -98.239), "SPS": (33.989, -98.492),
            "TYR": (32.354, -95.402),
            # Pacific Coast / West
            "BUR": (34.201,-118.359), "FAT": (36.776,-119.718), "GEG": (47.620,-117.534),
            "LGB": (33.818,-118.152), "MFR": (42.374,-122.874), "MRY": (36.587,-121.843),
            "OAK": (37.721,-122.221), "ONT": (34.056,-117.601), "PSC": (46.265,-119.119),
            "PSP": (33.830,-116.506), "RDD": (40.509,-122.294), "SBA": (34.426,-119.840),
            "SJC": (37.363,-121.929), "SNA": (33.676,-117.868), "YKM": (46.568,-120.544),
            # Hawaii
            "HNL": (21.319,-157.922), "OGG": (20.899,-156.431), "KOA": (19.739,-156.046),
        }

        if not market_df.empty:
            map_yr = int(year_range[1])
            cmh_routes = (
                market_df[(market_df["ORIGIN"] == "CMH") & (market_df["YEAR"] == map_yr)]
                .groupby(["DEST", "DEST_CITY_NAME"])["PASSENGERS"]
                .sum()
                .reset_index()
                .sort_values("PASSENGERS", ascending=False)
                .head(10)
            )
            cmh_routes = cmh_routes[cmh_routes["DEST"].isin(AIRPORT_COORDS)]

            max_pax = cmh_routes["PASSENGERS"].max()
            origin_lat, origin_lon = AIRPORT_COORDS["CMH"]

            fig_map = go.Figure()

            for _, row in cmh_routes.iterrows():
                dest = row["DEST"]
                if dest not in AIRPORT_COORDS:
                    continue
                dest_lat, dest_lon = AIRPORT_COORDS[dest]
                pax = row["PASSENGERS"]
                weight = pax / max_pax
                lw = 1.0 + weight * 5.5
                opacity = 0.25 + weight * 0.65

                fig_map.add_trace(go.Scattergeo(
                    lon=[origin_lon, dest_lon],
                    lat=[origin_lat, dest_lat],
                    mode="lines",
                    line=dict(width=lw, color=MED_BLUE),
                    opacity=opacity,
                    hoverinfo="skip",
                    showlegend=False,
                ))

            dest_lats = [AIRPORT_COORDS[r["DEST"]][0] for _, r in cmh_routes.iterrows() if r["DEST"] in AIRPORT_COORDS]
            dest_lons = [AIRPORT_COORDS[r["DEST"]][1] for _, r in cmh_routes.iterrows() if r["DEST"] in AIRPORT_COORDS]
            dest_sizes = [6 + (r["PASSENGERS"] / max_pax) * 22 for _, r in cmh_routes.iterrows() if r["DEST"] in AIRPORT_COORDS]
            dest_labels = [
                f"<b>{r['DEST']}</b><br>{r['DEST_CITY_NAME']}<br>{r['PASSENGERS']:,.0f} passengers"
                for _, r in cmh_routes.iterrows() if r["DEST"] in AIRPORT_COORDS
            ]

            fig_map.add_trace(go.Scattergeo(
                lon=dest_lons, lat=dest_lats,
                mode="markers+text",
                marker=dict(
                    size=dest_sizes,
                    color=MED_BLUE,
                    opacity=0.85,
                    line=dict(color="white", width=1),
                ),
                text=[r["DEST"] for _, r in cmh_routes.iterrows() if r["DEST"] in AIRPORT_COORDS],
                textposition="top center",
                textfont=dict(family="Open Sans", size=9, color=TEXT_COLOR),
                hovertext=dest_labels,
                hoverinfo="text",
                showlegend=False,
            ))

            # CMH origin dot
            fig_map.add_trace(go.Scattergeo(
                lon=[origin_lon], lat=[origin_lat],
                mode="markers+text",
                marker=dict(size=18, color=NAVY, symbol="star", line=dict(color="white", width=1.5)),
                text=["CMH"],
                textposition="bottom center",
                textfont=dict(family="Open Sans", size=11, color=NAVY, weight=700),
                hovertext=["Columbus (CMH) — Origin"],
                hoverinfo="text",
                showlegend=False,
            ))

            fig_map.update_layout(
                geo=dict(
                    scope="usa",
                    projection_type="albers usa",
                    showland=True, landcolor="#F8F9FA",
                    showlakes=True, lakecolor="#DDEEFF",
                    showcoastlines=True, coastlinecolor="#CBD5E0",
                    showsubunits=True, subunitcolor="#CBD5E0",
                    bgcolor="white",
                ),
                paper_bgcolor="white",
                font=dict(family="Open Sans", color=TEXT_COLOR, size=11),
                margin=dict(t=10, b=10, l=0, r=0),
                height=480,
            )
            if not cmh_routes.empty:
                top_route     = cmh_routes.iloc[0]
                top_city      = top_route["DEST_CITY_NAME"].split(",")[0]
                top_pax_share = top_route["PASSENGERS"] / cmh_routes["PASSENGERS"].sum() * 100
                insight(f"<b>{top_city} ({top_route['DEST']})</b> is Columbus's busiest route in {map_yr} with "
                        f"<b>{top_route['PASSENGERS']:,.0f} passengers</b> — {top_pax_share:.0f}% of the top-10 route volume.")
            map_col, list_col = st.columns([3, 1])
            with map_col:
                st.caption(f"Top 10 routes by passengers departing Columbus (CMH) in {map_yr}. Dot size and line weight scale with volume.")
                st.plotly_chart(fig_map, use_container_width=True)
            with list_col:
                st.markdown(f"**Top 5 Routes ({map_yr})**")
                for rank, (_, r) in enumerate(cmh_routes.head(5).iterrows(), 1):
                    city = r["DEST_CITY_NAME"].split(",")[0]
                    pax  = r["PASSENGERS"]
                    st.markdown(
                        f"<div style='padding:8px 0; border-bottom:1px solid #f0f2f5;'>"
                        f"<span style='font-size:11px; color:#6b7280;'>#{rank}</span><br>"
                        f"<span style='font-weight:600; color:{NAVY}; font-size:13px;'>{r['DEST']} · {city}</span><br>"
                        f"<span style='font-size:12px; color:{TEXT_COLOR};'>{pax:,.0f} pax</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        # ── 2. Sankey: CMH → Hub → Onward ──────────────────────
        st.markdown("### Connecting Hub Flow — Where CMH Passengers Go Through Major Hubs")
        st.caption(
            "This diagram shows only **connecting traffic**: passengers who fly CMH → hub → onward destination. "
            "Direct nonstop routes from CMH (including LGA, BOS, DCA, and others) are **not shown here** — "
            "see the Market Opportunity tab for CMH's direct route network."
        )
        if data_loaded:
            sankey_yr = int(market_df["YEAR"].max())
            cmh_hubs, hub_onward = load_hub_onward(year=sankey_yr)
            if not cmh_hubs.empty and not hub_onward.empty:
                all_nodes = ["CMH"] + cmh_hubs["hub"].tolist() + hub_onward["dest"].unique().tolist()
                node_idx  = {n: i for i, n in enumerate(all_nodes)}
                sources, targets, values, link_colors = [], [], [], []
                hub_palette = [MED_BLUE, TEAL, "#A053AC", "#C6397B"]
                for i, row in cmh_hubs.iterrows():
                    sources.append(node_idx["CMH"])
                    targets.append(node_idx[row["hub"]])
                    values.append(row["cmh_pax"])
                    link_colors.append("rgba(11,118,218,0.35)")
                for i, row in hub_onward.iterrows():
                    hi  = cmh_hubs["hub"].tolist().index(row["hub"])
                    col = hub_palette[hi % len(hub_palette)]
                    r2, g2, b2 = int(col[1:3],16), int(col[3:5],16), int(col[5:7],16)
                    sources.append(node_idx[row["hub"]])
                    targets.append(node_idx[row["dest"]])
                    values.append(row["pax"])
                    link_colors.append(f"rgba({r2},{g2},{b2},0.28)")
                node_colors = (
                    [NAVY] +
                    [hub_palette[i % len(hub_palette)] for i in range(len(cmh_hubs))] +
                    ["#86C5FA"] * len(hub_onward["dest"].unique())
                )
                fig_sankey = go.Figure(go.Sankey(
                    arrangement="snap",
                    node=dict(pad=18, thickness=22, label=all_nodes, color=node_colors,
                              line=dict(color="white", width=0.5)),
                    link=dict(source=sources, target=targets, value=values, color=link_colors),
                ))
                fig_sankey.update_layout(
                    paper_bgcolor="white",
                    font=dict(family="Open Sans", size=11, color=TEXT_COLOR),
                    height=480, margin=dict(t=20, b=20, l=20, r=20),
                )
                st.plotly_chart(fig_sankey, use_container_width=True)
                top_hub  = cmh_hubs.iloc[0]
                hub_city = dest_city.get(top_hub['hub'], top_hub['hub'])
                insight(
                    f"<b>{hub_city} ({top_hub['hub']})</b> is Columbus's largest connecting hub, routing "
                    f"<b>{top_hub['cmh_pax']:,.0f} passengers</b> in {sankey_yr}. "
                    f"Note: destinations shown on the right (including LGA) appear here as popular hub "
                    f"onward connections — CMH also operates <b>direct nonstop service</b> to LGA, BOS, and DCA "
                    f"independent of this hub flow.",
                    sentiment="neutral",
                )

# ══════════════════════════════════════════════════════════════
# TAB 2 · COLUMBUS MSA
# ══════════════════════════════════════════════════════════════
with tab_msa:
    if msa_annual.empty:
        st.info("Run `columbus_msa.py` to generate MSA data in `output/`.")
    else:
        if len(msa_annual) >= 2:
            _msa_pop  = msa_annual.iloc[-1]["total_population"]
            _msa_yr   = int(msa_annual.iloc[-1]["year"])
            _msa_inc  = msa_annual.iloc[-1].get("median_household_income", 0)
            exec_summary(
                f"The Columbus metro reached {_msa_pop/1e6:.2f}M residents in {_msa_yr} "
                f"with a median household income of ${_msa_inc:,.0f} — "
                f"a demographic foundation that directly drives aviation demand growth at Columbus (CMH)."
            )
        col_m1, col_m2 = st.columns(2)

        # ── Population & Income Trends ──────────────────────────
        with col_m1:
            st.markdown("### Population Growth")
            fig_pop = go.Figure()
            fig_pop.add_trace(go.Scatter(
                x=msa_annual["year"], y=msa_annual["total_population"]/1e6,
                mode="lines+markers+text",
                line=dict(color=NAVY, width=3), marker=dict(size=8),
                text=(msa_annual["total_population"]/1e6).round(2).astype(str)+"M",
                textposition="top center", textfont=dict(size=9),
                fill="tozeroy", fillcolor="rgba(0,47,108,0.07)",
                name="Population",
            ))
            pop_min = msa_annual["total_population"].min() / 1e6
            pop_max = msa_annual["total_population"].max() / 1e6
            pop_pad = (pop_max - pop_min) * 0.5
            fig_pop = layout(fig_pop, "Columbus MSA Total Population", height=280, legend=False)
            fig_pop.update_layout(xaxis_title="Year", yaxis_title="Population (millions)",
                                  xaxis=dict(tickmode="linear"),
                                  yaxis=dict(range=[pop_min - pop_pad, pop_max + pop_pad]),
                                  margin=dict(t=52, b=36, l=60, r=90))
            st.plotly_chart(fig_pop, use_container_width=True)
            if len(msa_annual) >= 2:
                pop_latest    = msa_annual.iloc[-1]
                pop_prev      = msa_annual.iloc[-2]
                pop_yoy       = (pop_latest["total_population"] - pop_prev["total_population"]) / pop_prev["total_population"] * 100
                pop_total_chg = (msa_annual.iloc[-1]["total_population"] - msa_annual.iloc[0]["total_population"]) / msa_annual.iloc[0]["total_population"] * 100
                insight(f"The Columbus metro grew to <b>{pop_latest['total_population']/1e6:.2f}M residents</b> in {int(pop_latest['year'])}, "
                        f"up <b>{pop_yoy:.1f}%</b> year-over-year and <b>{pop_total_chg:.1f}%</b> since {int(msa_annual.iloc[0]['year'])} — "
                        f"one of the fastest-growing metros in the Midwest.")

            st.markdown("### Household Income")
            fig_inc = go.Figure()
            fig_inc.add_trace(go.Scatter(
                x=msa_annual["year"], y=msa_annual["median_household_income"],
                mode="lines+markers", line=dict(color=TEAL, width=2.5), marker=dict(size=7),
                name="Median HH Income",
            ))
            if "per_capita_income" in msa_annual.columns:
                fig_inc.add_trace(go.Scatter(
                    x=msa_annual["year"], y=msa_annual["per_capita_income"],
                    mode="lines+markers", line=dict(color=MED_BLUE, width=2.5, dash="dash"),
                    marker=dict(size=7), name="Per Capita Income",
                ))
            fig_inc = layout(fig_inc, "Columbus MSA Income Trends", height=280)
            fig_inc.update_layout(xaxis_title="Year", yaxis_title="USD",
                                  yaxis_tickprefix="$", xaxis=dict(tickmode="linear"))
            st.plotly_chart(fig_inc, use_container_width=True)
            if "median_household_income" in msa_annual.columns and len(msa_annual) >= 2:
                inc_latest = msa_annual.iloc[-1]["median_household_income"]
                inc_first  = msa_annual.iloc[0]["median_household_income"]
                inc_chg    = (inc_latest - inc_first) / inc_first * 100
                insight(f"Columbus median household income reached <b>${inc_latest:,.0f}</b> in {int(msa_annual.iloc[-1]['year'])}, "
                        f"a <b>{inc_chg:.1f}%</b> increase since {int(msa_annual.iloc[0]['year'])} — "
                        f"rising purchasing power that directly fuels air travel demand.")

            if "unemployment_rate" in msa_annual.columns:
                st.markdown("### Unemployment Rate")
                fig_unemp = go.Figure(go.Bar(
                    x=msa_annual["year"], y=msa_annual["unemployment_rate"],
                    marker_color=[NAVY if y < 2020 else "#C6397B" if y == 2020 else TEAL
                                  for y in msa_annual["year"]],
                    text=msa_annual["unemployment_rate"].round(1).astype(str)+"%",
                    textposition="outside", textfont=dict(size=10),
                ))
                fig_unemp = layout(fig_unemp, "Columbus MSA Unemployment Rate (%)", height=250, legend=False)
                fig_unemp.update_layout(xaxis_title="Year", yaxis_title="%",
                                        xaxis=dict(tickmode="linear"),
                                        yaxis=dict(range=[0, msa_annual["unemployment_rate"].max() * 1.25]))
                st.plotly_chart(fig_unemp, use_container_width=True)
                unemp_latest = msa_annual.iloc[-1]["unemployment_rate"]
                unemp_covid  = msa_annual[msa_annual["year"]==2020]["unemployment_rate"]
                covid_val    = unemp_covid.iloc[0] if not unemp_covid.empty else None
                if covid_val:
                    insight(f"Columbus unemployment dropped to <b>{unemp_latest:.1f}%</b> in {int(msa_annual.iloc[-1]['year'])} — "
                            f"a sharp recovery from the <b>{covid_val:.1f}%</b> peak during the 2020 pandemic, "
                            f"reflecting a resilient regional labor market that supports strong consumer spending.")
                else:
                    insight(f"Columbus unemployment stands at <b>{unemp_latest:.1f}%</b> in {int(msa_annual.iloc[-1]['year'])}, "
                            f"reflecting a tight labor market that supports strong consumer spending on travel.")

        with col_m2:
            # ── Age Distribution ────────────────────────────────
            if not msa_age.empty:
                st.markdown("### Population by Generation")
                latest_age = msa_age[msa_age["year"]==msa_age["year"].max()].copy()
                gen_order  = ["Silent+ (80+)","Baby Boomers (61-79)","Gen X (45-60)",
                              "Millennials (29-44)","Gen Z (15-28)","Gen Alpha (0-14)"]
                latest_age["age_group"] = pd.Categorical(latest_age["age_group"],
                                                          categories=gen_order, ordered=True)
                latest_age = latest_age.sort_values("age_group")
                gen_colors = [LIGHT_BLUE, MED_BLUE, TEAL, "#248F81", "#002F6C", "#0F171F"]
                fig_age = go.Figure(go.Bar(
                    x=latest_age["population"], y=latest_age["age_group"],
                    orientation="h",
                    marker_color=gen_colors,
                    text=(latest_age["population"]/1e3).round(0).astype(int).astype(str)+"K",
                    textposition="outside", textfont=dict(size=10),
                ))
                fig_age = layout(fig_age, f"Columbus MSA Population by Generation ({msa_age['year'].max()})",
                                 height=300, legend=False)
                fig_age.update_layout(xaxis_title="Population", yaxis_title="",
                                      margin=dict(t=52, b=36, l=40, r=90),
                                      xaxis=dict(range=[0, latest_age["population"].max() * 1.18]))
                st.plotly_chart(fig_age, use_container_width=True)
                largest_gen    = latest_age.loc[latest_age["population"].idxmax()]
                millennial_row = latest_age[latest_age["age_group"].astype(str).str.startswith("Millennials")]
                millennial_pct = (millennial_row.iloc[0]["population"] / latest_age["population"].sum() * 100) if not millennial_row.empty else 0
                insight(f"<b>{largest_gen['age_group']}</b> is the largest generational cohort in the Columbus metro. "
                        f"Millennials represent <b>{millennial_pct:.0f}%</b> of the population — "
                        f"the prime travel-spending demographic and a key driver of aviation demand.")

            # ── Income Distribution ─────────────────────────────
            if not msa_income.empty:
                st.markdown("### Household Income Distribution")
                latest_inc = msa_income[msa_income["year"]==msa_income["year"].max()].copy()
                bracket_colors = [TEAL, MED_BLUE, "#86C5FA", LIGHT_BLUE, NAVY, "#0F171F"]
                fig_idist = go.Figure(go.Pie(
                    labels=latest_inc["income_bracket"],
                    values=latest_inc["pct_households"],
                    hole=0.48,
                    textinfo="percent",
                    textfont=dict(family="Open Sans", size=10),
                    marker=dict(colors=bracket_colors),
                ))
                fig_idist.update_layout(
                    paper_bgcolor="white", height=320,
                    margin=dict(t=20, b=10, l=10, r=10),
                    font=dict(family="Open Sans"),
                    title=dict(text=f"Income Distribution ({msa_income['year'].max()})",
                               font=dict(size=14, color=TEXT_COLOR, family="Open Sans")),
                    legend=dict(font=dict(size=9), bgcolor="white"),
                )
                st.plotly_chart(fig_idist, use_container_width=True)
                over_75k = latest_inc[latest_inc["income_bracket"].str.contains(r"\$75|\$100|\$150|\$200", regex=True, na=False)]["pct_households"].sum()
                insight(f"Approximately <b>{over_75k:.0f}%</b> of Columbus households earn <b>$75,000 or more</b> annually — "
                        f"a growing upper-middle-income segment that strongly correlates with higher air travel frequency.")

            # ── Employment by Sector ────────────────────────────
            st.markdown("### Employment by Industry Sector (2023)")
            emp_df = fetch_employment_by_sector()
            if not emp_df.empty:
                fig_emp = go.Figure(go.Bar(
                    x=emp_df["Employed"], y=emp_df["Sector"],
                    orientation="h",
                    marker_color=[TEAL if i == len(emp_df)-1 else NAVY
                                  for i in range(len(emp_df))],
                    text=(emp_df["Employed"]/1e3).round(0).astype(int).astype(str)+"K",
                    textposition="outside", textfont=dict(size=10),
                ))
                fig_emp = layout(fig_emp, "Columbus MSA Civilian Employed Population by Industry",
                                 height=380, legend=False)
                fig_emp.update_layout(xaxis_title="Employed Workers", yaxis_title="",
                                      xaxis=dict(showgrid=True,
                                                 range=[0, emp_df["Employed"].max() * 1.22]))
                st.plotly_chart(fig_emp, use_container_width=True)
                top_sector = emp_df.loc[emp_df["Employed"].idxmax()]
                insight(f"<b>{top_sector['Sector']}</b> is the Columbus metro's largest employment sector with "
                        f"<b>{top_sector['Employed']:,.0f} workers</b> — a diversified economic base spanning healthcare, "
                        f"education, and professional services that generates substantial business travel demand.")
            else:
                st.caption("Employment by sector data unavailable (Census API timeout).")

        # ── MSA vs CMH Passenger Growth ─────────────────────────
        st.markdown("---")
        st.markdown("### Columbus MSA Growth vs CMH Passenger Traffic")
        st.caption(
            "Validates the core narrative: Columbus (CMH) passenger growth is outpacing Columbus metro "
            "population and income growth — signaling structural demand beyond organic MSA growth."
        )
        if not data_loaded or market_df.empty:
            st.info("Add BTS T-100 data (`data/bts/`) to see the correlation chart.")
        else:
            cmh_corr = (market_df[market_df["ORIGIN"]=="CMH"]
                        .groupby("YEAR")["PASSENGERS"].sum().reset_index()
                        .rename(columns={"YEAR":"year","PASSENGERS":"passengers"}))
            keep_cols = [c for c in ["year","total_population","median_household_income","per_capita_income"]
                         if c in msa_annual.columns]
            combined  = cmh_corr.merge(msa_annual[keep_cols], on="year", how="inner")
            if combined.empty:
                st.warning("No overlapping years between BTS and MSA data.")
            else:
                base = int(combined["year"].min())
                b    = combined[combined["year"]==base].iloc[0]
                combined["Columbus (CMH) Passengers"]  = combined["passengers"] / b["passengers"] * 100
                if "total_population" in combined.columns:
                    combined["MSA Population"] = combined["total_population"] / b["total_population"] * 100
                if "median_household_income" in combined.columns:
                    combined["Median HH Income"] = combined["median_household_income"] / b["median_household_income"] * 100
                if "per_capita_income" in combined.columns:
                    combined["Per Capita Income"] = combined["per_capita_income"] / b["per_capita_income"] * 100
                fig10 = go.Figure()
                series_cfg = [
                    ("Columbus (CMH) Passengers",   NAVY,     "solid",   3, 8),
                    ("MSA Population",   TEAL,     "dash",    2, 6),
                    ("Median HH Income", "#C6397B", "dot",    2, 6),
                    ("Per Capita Income", MED_BLUE, "dashdot", 2, 6),
                ]
                for name, color, dash, width, msize in series_cfg:
                    if name in combined.columns:
                        fig10.add_trace(go.Scatter(
                            x=combined["year"], y=combined[name], name=name,
                            mode="lines+markers",
                            line=dict(color=color, width=width, dash=dash),
                            marker=dict(size=msize, color=color),
                        ))
                fig10.add_hline(y=100, line_dash="dot", line_color="#ccc", line_width=1,
                                annotation_text=f"Base year ({base} = 100)",
                                annotation_font=dict(size=10, color="#888"))
                fig10 = layout(fig10, f"Growth Index: Columbus (CMH) vs Columbus MSA Indicators ({base} = 100)", height=460)
                fig10.update_layout(yaxis_title="Index (Base = 100)", xaxis_title="Year",
                                    xaxis=dict(tickmode="linear"))
                st.plotly_chart(fig10, use_container_width=True)
                last    = combined[combined["year"]==combined["year"].max()].iloc[0]
                pax_idx = last["Columbus (CMH) Passengers"]
                pop_idx = last.get("MSA Population", 100)
                gap     = pax_idx - pop_idx
                direction = "outpacing" if gap > 0 else "trailing"
                insight(f"As of {int(last['year'])}, the Columbus (CMH) passenger index stands at <b>{pax_idx:.1f}</b> vs "
                        f"the Columbus MSA population index of <b>{pop_idx:.1f}</b> (base {base} = 100) — "
                        f"airport traffic is <b>{direction} population growth</b> by <b>{abs(gap):.1f} index points</b>, "
                        f"suggesting Columbus is capturing {'more than its fair share of' if gap > 0 else 'less than expected'} regional demand.",
                        sentiment="positive" if gap > 0 else "risk")

        # ── Traveler Demographic Profile ─────────────────────────
        st.markdown("---")
        st.markdown("### Traveler Demographic Profile — Columbus vs. Peer Markets")
        st.caption(
            "Household income, educational attainment, and generational mix are the strongest predictors "
            "of air travel frequency and premium cabin spend. These benchmarks show where Columbus stands "
            "today and where the growth runway lies."
        )

        peer_demo = fetch_peer_msa_demographics()

        col_pd1, col_pd2 = st.columns(2)

        with col_pd1:
            # ── Median HH Income peer comparison ────────────────
            if not peer_demo.empty:
                st.markdown("#### Median Household Income vs. Peers")
                _pd_inc = peer_demo[peer_demo["Median_HH_Income"] > 0].sort_values("Median_HH_Income", ascending=True)
                _asp_set = {"Austin (AUS)", "Raleigh-Durham (RDU)"}
                fig_inc_peer = go.Figure(go.Bar(
                    x=_pd_inc["Median_HH_Income"],
                    y=_pd_inc["MSA"],
                    orientation="h",
                    marker_color=[
                        TEAL  if "CMH" in m else
                        NAVY  if m in _asp_set else
                        MED_BLUE
                        for m in _pd_inc["MSA"]
                    ],
                    text=["$" + f"{v:,.0f}" for v in _pd_inc["Median_HH_Income"]],
                    textposition="outside", textfont=dict(size=10),
                ))
                fig_inc_peer = layout(fig_inc_peer, "Median Household Income — Peer MSAs (ACS 2023)", legend=False)
                fig_inc_peer.update_layout(
                    xaxis=dict(title="Median Household Income", tickprefix="$", tickformat=",",
                               range=[0, _pd_inc["Median_HH_Income"].max() * 1.25]),
                    yaxis_title="",
                )
                if "Columbus (CMH)" in _pd_inc["MSA"].values:
                    _ci = _pd_inc["MSA"].tolist().index("Columbus (CMH)")
                    _cv = _pd_inc.loc[_pd_inc["MSA"] == "Columbus (CMH)", "Median_HH_Income"].iloc[0]
                    fig_inc_peer.add_shape(type="rect", x0=0, x1=_cv,
                        y0=_ci - 0.48, y1=_ci + 0.48,
                        line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_inc_peer, use_container_width=True)

            # ── Bachelor's+ attainment peer comparison ───────────
            if not peer_demo.empty:
                st.markdown("#### Educational Attainment vs. Peers")
                _pd_edu = peer_demo[peer_demo["Bachelors_Pct"] > 0].sort_values("Bachelors_Pct", ascending=True)
                fig_edu = go.Figure(go.Bar(
                    x=_pd_edu["Bachelors_Pct"],
                    y=_pd_edu["MSA"],
                    orientation="h",
                    marker_color=[
                        TEAL if "CMH" in m else
                        NAVY if m in _asp_set else
                        MED_BLUE
                        for m in _pd_edu["MSA"]
                    ],
                    text=[f"{v:.1f}%" for v in _pd_edu["Bachelors_Pct"]],
                    textposition="outside", textfont=dict(size=10),
                ))
                fig_edu = layout(fig_edu, "Bachelor's Degree or Higher — Adults 25+ (ACS 2023)", legend=False)
                fig_edu.update_layout(
                    xaxis=dict(title="% of Adults 25+ with Bachelor's+", ticksuffix="%",
                               range=[0, _pd_edu["Bachelors_Pct"].max() * 1.25]),
                    yaxis_title="",
                )
                if "Columbus (CMH)" in _pd_edu["MSA"].values:
                    _ei = _pd_edu["MSA"].tolist().index("Columbus (CMH)")
                    _ev = _pd_edu.loc[_pd_edu["MSA"] == "Columbus (CMH)", "Bachelors_Pct"].iloc[0]
                    fig_edu.add_shape(type="rect", x0=0, x1=_ev,
                        y0=_ei - 0.48, y1=_ei + 0.48,
                        line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_edu, use_container_width=True)

            if not peer_demo.empty and "Columbus (CMH)" in peer_demo["MSA"].values:
                _cr  = peer_demo[peer_demo["MSA"] == "Columbus (CMH)"].iloc[0]
                _asp = peer_demo[peer_demo["MSA"].isin(["Austin (AUS)", "Raleigh-Durham (RDU)", "Nashville (BNA)"])]
                _inc_gap = _asp["Median_HH_Income"].mean() - _cr["Median_HH_Income"]
                _edu_gap = _asp["Bachelors_Pct"].mean()    - _cr["Bachelors_Pct"]
                insight(
                    f"Columbus's median household income of <b>${_cr['Median_HH_Income']:,.0f}</b> trails "
                    f"aspirational peers (AUS/BNA/RDU) by an average of <b>${_inc_gap:,.0f}</b>, "
                    f"and its bachelor's+ attainment of <b>{_cr['Bachelors_Pct']:.1f}%</b> lags by "
                    f"<b>{_edu_gap:.1f} percentage points</b>. "
                    f"As Columbus continues attracting technology and professional employers, "
                    f"closing these gaps will directly expand its high-frequency traveler base.",
                    sentiment="neutral"
                )

        with col_pd2:
            # ── Generational mix with travel propensity ──────────
            if not msa_age.empty:
                st.markdown("#### Generational Mix & Travel Propensity")
                st.caption("Bar = Columbus population. ✈ score = air travel propensity index (0–100, based on US travel frequency research).")
                _PROPENSITY = {
                    "Gen Alpha (0-14)":     15,
                    "Gen Z (15-28)":        72,
                    "Millennials (29-44)":  88,
                    "Gen X (45-60)":        80,
                    "Baby Boomers (61-79)": 68,
                    "Silent+ (80+)":        32,
                }
                _gen_order  = ["Silent+ (80+)", "Baby Boomers (61-79)", "Gen X (45-60)",
                               "Millennials (29-44)", "Gen Z (15-28)", "Gen Alpha (0-14)"]
                _gen_colors = [LIGHT_BLUE, MED_BLUE, TEAL, "#248F81", NAVY, "#0F171F"]
                _age_yr     = msa_age["year"].max()
                _ag         = msa_age[msa_age["year"] == _age_yr].copy()
                _ag["age_group"] = pd.Categorical(_ag["age_group"], categories=_gen_order, ordered=True)
                _ag = _ag.sort_values("age_group")

                fig_gen = go.Figure(go.Bar(
                    x=_ag["population"],
                    y=_ag["age_group"].astype(str),
                    orientation="h",
                    marker_color=_gen_colors,
                    text=(_ag["population"] / 1e3).round(0).astype(int).astype(str) + "K",
                    textposition="inside",
                    textfont=dict(size=10, color="white"),
                    hovertemplate="<b>%{y}</b><br>Population: %{x:,.0f}<extra></extra>",
                    showlegend=False,
                ))
                _pop_max = _ag["population"].max()
                for _, _gr in _ag.iterrows():
                    _gen  = str(_gr["age_group"])
                    _prop = _PROPENSITY.get(_gen, 50)
                    _pcol = TEAL if _prop >= 75 else ("#C6397B" if _prop < 40 else MED_BLUE)
                    fig_gen.add_annotation(
                        x=_pop_max * 1.27, y=_gen,
                        text=f"✈ {_prop}",
                        showarrow=False,
                        font=dict(size=11, color=_pcol, family="Open Sans"),
                        xanchor="right",
                    )
                fig_gen = layout(fig_gen, f"Columbus MSA — Generation × Travel Propensity ({int(_age_yr)})",
                                 height=320, legend=False)
                fig_gen.update_layout(
                    xaxis=dict(title="Population", range=[0, _pop_max * 1.32]),
                    yaxis_title="",
                    margin=dict(r=10),
                )
                st.plotly_chart(fig_gen, use_container_width=True)

                _mil = _ag[_ag["age_group"].astype(str).str.startswith("Millennials")]
                _gz  = _ag[_ag["age_group"].astype(str).str.startswith("Gen Z")]
                _mil_n = int(_mil["population"].iloc[0]) if not _mil.empty else 0
                _gz_n  = int(_gz["population"].iloc[0])  if not _gz.empty  else 0
                insight(
                    f"<b>Millennials ({_mil_n:,})</b> are Columbus's largest cohort and the nation's "
                    f"highest-frequency air travelers (propensity score: 88/100). "
                    f"Combined with <b>Gen Z ({_gz_n:,})</b>, these two cohorts represent "
                    f"<b>{(_mil_n + _gz_n) / _ag['population'].sum() * 100:.0f}% of the metro population</b> "
                    f"— and their travel volume will only grow as incomes rise.",
                    sentiment="positive"
                )

            # ── Premium cabin addressable market ─────────────────
            if not msa_income.empty and not peer_demo.empty:
                st.markdown("#### Premium Travel Addressable Market")
                _inc_yr  = msa_income["year"].max()
                _inc_lat = msa_income[msa_income["year"] == _inc_yr].copy()
                _prem_hh = _inc_lat[_inc_lat["income_bracket"].isin(["$100K–$149K", "$150K+"])]["households"].sum()
                _prem_pct= _inc_lat[_inc_lat["income_bracket"].isin(["$100K–$149K", "$150K+"])]["pct_households"].sum()
                _150k_hh = _inc_lat[_inc_lat["income_bracket"] == "$150K+"]["households"].sum()

                _tam_df = pd.DataFrame([
                    {"Segment": "$150K+  (Affluent)",       "HH": _150k_hh},
                    {"Segment": "$100K–$149K (Upper-mid)",  "HH": _inc_lat[_inc_lat["income_bracket"] == "$100K–$149K"]["households"].sum()},
                    {"Segment": "Under $100K",              "HH": _inc_lat[~_inc_lat["income_bracket"].isin(["$100K–$149K","$150K+"])]["households"].sum()},
                ])
                fig_tam = go.Figure(go.Pie(
                    labels=_tam_df["Segment"], values=_tam_df["HH"],
                    hole=0.52, textinfo="percent",
                    textfont=dict(size=11, family="Open Sans"),
                    marker=dict(colors=[NAVY, MED_BLUE, LIGHT_BLUE]),
                    sort=False,
                    hovertemplate="<b>%{label}</b><br>%{value:,.0f} households (%{percent})<extra></extra>",
                ))
                fig_tam.update_layout(
                    paper_bgcolor="white", height=280,
                    margin=dict(t=30, b=10, l=10, r=10),
                    font=dict(family="Open Sans"),
                    title=dict(text=f"Household Income Tiers — Premium TAM ({int(_inc_yr)})",
                               font=dict(size=13, color=TEXT_COLOR, family="Open Sans")),
                    legend=dict(font=dict(size=9), bgcolor="white"),
                )
                st.plotly_chart(fig_tam, use_container_width=True)

                _cmh_150 = peer_demo.loc[peer_demo["MSA"] == "Columbus (CMH)", "HH_150k_Plus_Pct"].iloc[0] if "Columbus (CMH)" in peer_demo["MSA"].values else 0
                _asp_150 = peer_demo.loc[peer_demo["MSA"].isin(["Austin (AUS)", "Raleigh-Durham (RDU)"]), "HH_150k_Plus_Pct"].mean() if not peer_demo.empty else 0
                insight(
                    f"<b>{_prem_pct:.0f}% of Columbus households — {_prem_hh:,.0f} in total — earn $100K or more</b>, "
                    f"representing the core premium cabin addressable market. "
                    f"The <b>{_150k_hh:,.0f} households earning $150K+</b> ({_cmh_150:.0f}% of total) "
                    f"are the highest-propensity first-class and business-class buyers. "
                    f"Aspirational peers Austin and Raleigh-Durham average <b>{_asp_150:.0f}%</b> at that income tier, "
                    f"signalling meaningful upside as Columbus's professional class expands.",
                    sentiment="positive"
                )


# ══════════════════════════════════════════════════════════════
# TAB 3 · COMPETITIVE ANALYSIS
# ══════════════════════════════════════════════════════════════
with tab_competitive:
    if not data_loaded:
        st.info("Add BTS T-100 Market CSV files to `data/bts/`.")
    else:
        filt_mkt = fy(fa(market_df, display_airports), year_range)
        _ct_yr   = int(year_range[1])
        _ct_all  = (filt_mkt[filt_mkt["YEAR"]==_ct_yr]
                    .groupby("ORIGIN")["PASSENGERS"].sum().sort_values(ascending=False))
        _ct_cmh  = _ct_all.get("CMH", 0)
        _ct_rank = list(_ct_all.index).index("CMH") + 1 if "CMH" in _ct_all.index else "—"
        exec_summary(
            f"In {_ct_yr}, Columbus (CMH) ranked #{_ct_rank} of {len(_ct_all)} airports in this peer group "
            f"with {_ct_cmh/1e6:.2f}M passengers. "
            f"The charts below benchmark Columbus (CMH) on total volume, growth rate, recovery trajectory, and route footprint."
        )

        # ── 1. Total Traffic ────────────────────────────────────
        st.markdown("### Total Passengers by Airport")
        latest = int(year_range[1])
        traffic = (filt_mkt[filt_mkt["YEAR"]==latest]
                   .groupby("ORIGIN")["PASSENGERS"].sum().reset_index()
                   .sort_values("PASSENGERS", ascending=True))
        traffic["Label"] = traffic["ORIGIN"].map(AIRPORT_NAMES).fillna(traffic["ORIGIN"])
        traffic["Color"] = traffic["ORIGIN"].map(color_map)
        fig1 = go.Figure(go.Bar(
            x=traffic["PASSENGERS"]/1e6, y=traffic["Label"], orientation="h",
            marker_color=traffic["Color"].tolist(),
            text=(traffic["PASSENGERS"]/1e6).round(2).astype(str)+"M",
            textposition="outside", textfont=dict(size=11),
        ))
        fig1 = layout(fig1, f"Total Enplaned Passengers — {latest}", legend=False)
        fig1.update_layout(xaxis_title="Passengers (millions)", yaxis_title="")
        # Highlight CMH bar with a teal border
        if "CMH" in traffic["ORIGIN"].values:
            cmh_label   = AIRPORT_NAMES["CMH"]
            cmh_bar_idx = traffic["Label"].tolist().index(cmh_label)
            cmh_val     = traffic[traffic["ORIGIN"] == "CMH"]["PASSENGERS"].iloc[0] / 1e6
            fig1.add_shape(type="rect",
                x0=-0.05, x1=cmh_val,
                y0=cmh_bar_idx - 0.48, y1=cmh_bar_idx + 0.48,
                line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)
        if not traffic.empty:
            cmh_row  = traffic[traffic["ORIGIN"]=="CMH"]
            if not cmh_row.empty:
                cmh_pax  = cmh_row.iloc[0]["PASSENGERS"]
                top_peer = traffic[traffic["ORIGIN"]!="CMH"].iloc[-1]
                gap_pct  = (top_peer["PASSENGERS"] - cmh_pax) / cmh_pax * 100
                leader   = top_peer["Label"]
                insight(f"In {latest}, <b>{leader}</b> leads the peer group with <b>{top_peer['PASSENGERS']/1e6:.2f}M passengers</b> — "
                        f"<b>{abs(gap_pct):.0f}%</b> {'more' if gap_pct > 0 else 'fewer'} than Columbus (CMH)'s <b>{cmh_pax/1e6:.2f}M</b>.",
                        sentiment="neutral")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            # ── 2. YoY Growth Heatmap ───────────────────────────
            st.markdown("### Year-over-Year Growth %")
            rows = []
            for ap in display_airports:
                ap_d = filt_mkt[filt_mkt["ORIGIN"]==ap]
                for yr in range(year_range[0]+1, year_range[1]+1):
                    curr = ap_d[ap_d["YEAR"]==yr]["PASSENGERS"].sum()
                    prev = ap_d[ap_d["YEAR"]==yr-1]["PASSENGERS"].sum()
                    if prev > 0:
                        rows.append({"Airport": AIRPORT_NAMES.get(ap, ap),
                                     "Code": ap, "Year": yr,
                                     "YoY %": round((curr-prev)/prev*100, 1)})
            if rows:
                yoy_df   = pd.DataFrame(rows)
                yoy_df   = yoy_df[~yoy_df["Year"].isin([2020, 2021])]
                yoy_pivot = yoy_df.pivot(index="Airport", columns="Year", values="YoY %")

                # Order rows: CMH on top, then peers sorted by latest year
                latest_col = yoy_pivot.columns.max()
                order = [AIRPORT_NAMES["CMH"]] + [
                    a for a in yoy_pivot[latest_col].drop(AIRPORT_NAMES["CMH"]).sort_values(ascending=False).index
                ]
                yoy_pivot = yoy_pivot.reindex([o for o in order if o in yoy_pivot.index])

                fig2 = go.Figure(go.Heatmap(
                    z=yoy_pivot.values,
                    x=[str(c) for c in yoy_pivot.columns],
                    y=yoy_pivot.index.tolist(),
                    colorscale=[
                        [0.0,  "#C6397B"],   # deep negative — magenta
                        [0.35, "#FFCCCF"],   # mild negative — blush
                        [0.5,  "#FFFFFF"],   # zero — white
                        [0.65, "#BDE1FD"],   # mild positive — light blue
                        [1.0,  "#002F6C"],   # strong positive — navy
                    ],
                    zmid=0,
                    text=yoy_pivot.values,
                    texttemplate="%{text:.1f}%",
                    textfont=dict(family="Open Sans", size=11, color="#0F171F"),
                    showscale=True,
                    colorbar=dict(title="YoY %", ticksuffix="%",
                                  tickfont=dict(family="Open Sans", size=9)),
                ))
                # Highlight CMH row with a border
                cmh_row_idx = list(yoy_pivot.index).index(AIRPORT_NAMES["CMH"])
                fig2.add_shape(type="rect",
                    x0=-0.5, x1=len(yoy_pivot.columns)-0.5,
                    y0=cmh_row_idx - 0.5, y1=cmh_row_idx + 0.5,
                    line=dict(color=NAVY, width=2), fillcolor="rgba(0,0,0,0)")

                fig2 = layout(fig2, "YoY Passenger Growth — Airport Comparison (%)", height=340, legend=False)
                fig2.update_layout(
                    xaxis=dict(type="category", side="bottom", tickfont=dict(size=11)),
                    yaxis_title="",
                    xaxis_title="",
                )
                st.plotly_chart(fig2, use_container_width=True)
                # YoY heatmap insight
                cmh_yoy_latest = yoy_df[(yoy_df["Code"]=="CMH")&(yoy_df["Year"]==latest_col)]
                all_yoy_latest = yoy_df[yoy_df["Year"]==latest_col].sort_values("YoY %", ascending=False)
                if not cmh_yoy_latest.empty and not all_yoy_latest.empty:
                    cmh_val   = cmh_yoy_latest.iloc[0]["YoY %"]
                    cmh_rank  = all_yoy_latest["Code"].tolist().index("CMH") + 1
                    direction = "grew" if cmh_val >= 0 else "declined"
                    insight(f"Columbus (CMH) {direction} <b>{cmh_val:+.1f}%</b> in {latest_col}, "
                            f"ranking <b>#{cmh_rank} of {len(all_yoy_latest)}</b> peer airports by YoY growth.",
                            sentiment="positive" if cmh_val >= 0 else "risk")

        with col_c2:
            # ── 3. Top Routes ───────────────────────────────────
            st.markdown("### Top Routes Comparison")
            peer_sel = st.selectbox("Compare Columbus (CMH) with:",
                                    [a for a in display_airports if a != "CMH"],
                                    format_func=lambda x: AIRPORT_NAMES.get(x, x),
                                    key="route_peer")
            r1, r2 = st.columns(2)
            for col_obj, ap, color in [(r1, "CMH", NAVY), (r2, peer_sel, color_map.get(peer_sel, TEAL))]:
                routes = (filt_mkt[filt_mkt["ORIGIN"]==ap]
                          .groupby("DEST")["PASSENGERS"].sum().reset_index()
                          .sort_values("PASSENGERS", ascending=False).head(10))
                with col_obj:
                    st.markdown(f"**{AIRPORT_NAMES.get(ap, ap)}**")
                    fig_r = go.Figure(go.Bar(
                        x=routes["PASSENGERS"]/1e3, y=routes["DEST"],
                        orientation="h", marker_color=color,
                        text=(routes["PASSENGERS"]/1e3).round(0).astype(int).astype(str)+"K",
                        textposition="outside", textfont=dict(size=9),
                    ))
                    fig_r = layout(fig_r, "", height=320, legend=False)
                    fig_r.update_layout(margin=dict(t=10,b=20,l=30,r=40),
                                        xaxis_title="Pax (thousands)")
                    st.plotly_chart(fig_r, use_container_width=True)

        st.markdown("---")

        # ── 4. Radar — Multi-Dimensional Airport Comparison ────
        st.markdown("### Multi-Dimensional Airport Comparison")
        st.caption("Radar scores each airport across 4 dimensions (0–100 scale). Larger area = stronger overall performance.")
        radar_yr = int(year_range[1])
        radar_rows = {}
        for ap in display_airports:
            ap_d    = filt_mkt[(filt_mkt["ORIGIN"]==ap)&(filt_mkt["YEAR"]==radar_yr)]
            pax     = ap_d["PASSENGERS"].sum()
            dests   = ap_d["DEST"].nunique()
            prev_d  = filt_mkt[(filt_mkt["ORIGIN"]==ap)&(filt_mkt["YEAR"]==radar_yr-1)]
            prev_p  = prev_d["PASSENGERS"].sum()
            yoy_r   = (pax - prev_p) / prev_p * 100 if prev_p > 0 else 0
            ot_row  = ontime_df[(ontime_df["AIRPORT"]==ap)&(ontime_df["YEAR"]==radar_yr)] if not ontime_df.empty else pd.DataFrame()
            ontime  = ot_row.iloc[0]["COMBINED_ONTIME_PCT"] if not ot_row.empty else None
            base_p  = market_df[(market_df["ORIGIN"]==ap)&(market_df["YEAR"]==2019)]["PASSENGERS"].sum()
            rec_idx = pax / base_p * 100 if base_p > 0 else None
            radar_rows[ap] = {"pax": pax, "dests": dests, "yoy": yoy_r,
                               "ontime": ontime, "recovery": rec_idx}
        # Normalise each dimension to 0–100 across airports
        def _norm(vals):
            mn, mx = min(v for v in vals if v is not None), max(v for v in vals if v is not None)
            if mx == mn:
                return [50 if v is not None else 0 for v in vals]
            return [round((v - mn) / (mx - mn) * 100, 1) if v is not None else 0 for v in vals]
        aps_ord     = [a for a in display_airports if a in radar_rows]
        categories  = ["Passengers", "Destinations", "YoY Growth", "On-Time %", "Recovery"]
        raw_matrix  = {
            "Passengers": [radar_rows[a]["pax"] for a in aps_ord],
            "Destinations":[radar_rows[a]["dests"] for a in aps_ord],
            "YoY Growth":  [radar_rows[a]["yoy"]  for a in aps_ord],
            "On-Time %":   [radar_rows[a]["ontime"] for a in aps_ord],
            "Recovery":    [radar_rows[a]["recovery"] for a in aps_ord],
        }
        def _hex_rgba(hex_color, alpha):
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"

        norm_matrix = {cat: _norm(vals) for cat, vals in raw_matrix.items()}
        if aps_ord:
            fig_radar = go.Figure()
            for i, ap in enumerate(aps_ord):
                scores = [norm_matrix[c][i] for c in categories]
                scores.append(scores[0])
                cats_closed = categories + [categories[0]]
                is_cmh   = ap == "CMH"
                ap_color = color_map.get(ap, "#aaa")
                fig_radar.add_trace(go.Scatterpolar(
                    r=scores, theta=cats_closed,
                    fill="toself",
                    fillcolor=_hex_rgba(ap_color, 0.30 if is_cmh else 0.12),
                    line=dict(color=ap_color, width=2.5 if is_cmh else 1.5),
                    name=AIRPORT_NAMES.get(ap, ap),
                    hovertemplate="<b>" + AIRPORT_NAMES.get(ap, ap) + "</b><br>%{theta}: %{r:.0f}/100<extra></extra>",
                ))
            fig_radar = layout(fig_radar, f"Airport Performance Radar — {radar_yr} (normalised 0–100)", height=480)
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9),
                                    gridcolor="#e8edf2"),
                    angularaxis=dict(tickfont=dict(size=11, family="Open Sans", color=TEXT_COLOR)),
                    bgcolor="white",
                ),
                paper_bgcolor="white",
                margin=dict(t=60, b=60, l=60, r=60),
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            cmh_scores = [norm_matrix[c][aps_ord.index("CMH")] for c in categories] if "CMH" in aps_ord else []
            if cmh_scores:
                best_dim  = categories[cmh_scores.index(max(cmh_scores))]
                worst_dim = categories[cmh_scores.index(min(cmh_scores))]
                insight(f"Columbus (CMH)'s strongest competitive dimension is <b>{best_dim}</b> (normalised score: "
                        f"<b>{max(cmh_scores):.0f}/100</b>); the biggest relative gap vs. peers is <b>{worst_dim}</b> "
                        f"— the clearest area for airport investment and airline recruitment focus.", sentiment="neutral")

        st.markdown("---")

        # ── 7a. Lounge Comparison ────────────────────────────────────
        st.markdown("### Passenger Lounge Access")
        st.caption(
            "Airline clubs (United Club, Delta Sky Club, Admirals Club) are the primary premium amenity "
            "for business travelers. Pay/independent lounges (Escape Lounge, The Club) are open to any passenger "
            "for a day pass or credit card access. Source: airport websites, lounge operator sites, 2025–2026."
        )

        # Verified lounge data per airport (2025–2026)
        # Sources: ind.com, cvgairport.com, clevelandairport.com, flypittsburgh.com,
        #          upgradedpoints.com, sleepinginairports.net, loungereview.com
        _LOUNGE_DATA = {
            "CMH": {"airline": 0, "pay": 1,
                    "clubs": [],
                    "pay_names": ["Escape Lounge"]},
            "IND": {"airline": 3, "pay": 0,
                    "clubs": ["Delta Sky Club", "United Club", "Admirals Club"],
                    "pay_names": []},
            "CVG": {"airline": 1, "pay": 2,
                    "clubs": ["Delta Sky Club"],
                    "pay_names": ["Escape Lounge", "The Club CVG"]},
            "CLE": {"airline": 1, "pay": 1,
                    "clubs": ["United Club"],
                    "pay_names": ["The Club CLE"]},
            "PIT": {"airline": 1, "pay": 1,
                    "clubs": ["Admirals Club"],
                    "pay_names": ["The Club PIT"]},
            "DAY": {"airline": 0, "pay": 0,
                    "clubs": [],
                    "pay_names": ["Business Travelers Center (free, limited hrs)"]},
            "AUS": {"airline": 3, "pay": 0,
                    "clubs": ["Admirals Club", "United Club", "Delta Sky Club"],
                    "pay_names": []},
            "BNA": {"airline": 2, "pay": 0,
                    "clubs": ["Delta Sky Club", "Admirals Club"],
                    "pay_names": ["Minute Suites"]},
            "RDU": {"airline": 3, "pay": 0,
                    "clubs": ["Admirals Club", "Delta Sky Club", "United Club"],
                    "pay_names": []},
        }

        _lg_rows = [
            {
                "Code":  ap,
                "Label": AIRPORT_NAMES.get(ap, ap),
                "Airline Clubs": _LOUNGE_DATA[ap]["airline"],
                "Pay Lounges":   _LOUNGE_DATA[ap]["pay"],
                "Total":         _LOUNGE_DATA[ap]["airline"] + _LOUNGE_DATA[ap]["pay"],
                "Club Names":    ", ".join(_LOUNGE_DATA[ap]["clubs"]) or "None",
                "Pay Names":     ", ".join(_LOUNGE_DATA[ap]["pay_names"]) or "None",
            }
            for ap in display_airports if ap in _LOUNGE_DATA
        ]
        _lg_df = (pd.DataFrame(_lg_rows)
                  .sort_values(["Airline Clubs", "Pay Lounges"], ascending=True)
                  .reset_index(drop=True))

        _lcol1, _lcol2 = st.columns([3, 2])
        with _lcol1:
            fig_lg = go.Figure()
            fig_lg.add_trace(go.Bar(
                name="Airline Clubs (UA/DL/AA)",
                x=_lg_df["Airline Clubs"],
                y=_lg_df["Label"],
                orientation="h",
                marker_color=NAVY,
                customdata=_lg_df[["Club Names"]].values,
                hovertemplate="<b>%{y}</b><br>Airline clubs: %{x}<br>%{customdata[0]}<extra></extra>",
            ))
            fig_lg.add_trace(go.Bar(
                name="Pay / Independent Lounges",
                x=_lg_df["Pay Lounges"],
                y=_lg_df["Label"],
                orientation="h",
                marker_color=TEAL,
                customdata=_lg_df[["Pay Names"]].values,
                hovertemplate="<b>%{y}</b><br>Pay lounges: %{x}<br>%{customdata[0]}<extra></extra>",
            ))
            if "CMH" in _lg_df["Code"].values:
                _cmh_lg_i = _lg_df["Code"].tolist().index("CMH")
                _cmh_lg_v = _lg_df.iloc[_cmh_lg_i]["Total"]
                fig_lg.add_shape(
                    type="rect",
                    x0=-0.1, x1=max(_cmh_lg_v, 0.5) + 0.2,
                    y0=_cmh_lg_i - 0.48, y1=_cmh_lg_i + 0.48,
                    line=dict(color=TEAL, width=2.5),
                    fillcolor="rgba(0,0,0,0)",
                )
            fig_lg = layout(fig_lg, "Passenger Lounges by Airport & Type", height=360, legend=True)
            fig_lg.update_layout(
                barmode="stack",
                xaxis=dict(title="Number of Lounges", tickmode="linear", dtick=1, range=[0, 5]),
                yaxis_title="",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
            )
            st.plotly_chart(fig_lg, use_container_width=True)

        with _lcol2:
            # Summary table
            st.markdown("#### Lounge Breakdown")
            for _, row in _lg_df.sort_values("Total", ascending=False).iterrows():
                _is_cmh = row["Code"] == "CMH"
                _border = f"border-left: 4px solid {TEAL};" if _is_cmh else f"border-left: 4px solid {NAVY};"
                _bg     = "#f0fafa" if _is_cmh else "#f8f9fa"
                _clubs  = row["Club Names"] if row["Club Names"] != "None" else "<em style='color:#9ca3af'>No airline clubs</em>"
                _pay    = row["Pay Names"] if row["Pay Names"] != "None" else ""
                st.markdown(
                    f"<div style='padding:8px 10px; margin-bottom:6px; border-radius:6px; {_border} background:{_bg};'>"
                    f"<span style='font-weight:700; font-size:13px; color:{NAVY};'>{row['Label']}</span>"
                    f"<span style='float:right; font-size:12px; color:#6b7280;'>{int(row['Total'])} lounge{'s' if row['Total']!=1 else ''}</span>"
                    f"<br><span style='font-size:11px; color:#374151;'>{_clubs}</span>"
                    + (f"<br><span style='font-size:11px; color:{TEAL};'>{_pay}</span>" if _pay else "")
                    + f"</div>",
                    unsafe_allow_html=True,
                )

        _cmh_lg_total    = _LOUNGE_DATA.get("CMH", {}).get("airline", 0)
        _peers_with_club = sum(1 for ap in display_airports
                               if ap != "CMH" and ap in _LOUNGE_DATA and _LOUNGE_DATA[ap]["airline"] > 0)
        _asp_lg = {a: _LOUNGE_DATA.get(a, {}).get("airline", 0) for a in ["AUS", "BNA", "RDU"] if a in display_airports}
        _asp_club_str = "; ".join(
            f"{AIRPORT_NAMES.get(a,a)} ({v} club{'s' if v!=1 else ''})"
            for a, v in _asp_lg.items()
        ) if _asp_lg else "aspirational peers"
        insight(
            f"Columbus (CMH) has <b>no airline club lounges</b> — the only airport in the peer set "
            f"(along with Dayton) without a United Club, Delta Sky Club, or Admirals Club. "
            f"The sole lounge is the third-party <b>Escape Lounge</b>, accessible via day pass or travel credit cards. "
            f"All {_peers_with_club} other peer airports offer at least one airline club: {_asp_club_str}. "
            f"For business travelers flying United or American — CMH's top two carriers — "
            f"the absence of a club lounge is a meaningful friction point and competitive disadvantage.",
            sentiment="risk",
        )

        st.markdown("---")

        # ── 7. Aircraft Gauge & Load Factor ─────────────────────────
        st.markdown("### Aircraft Gauge & Load Factor")
        st.caption(
            "Average seats per departure reveals how much large-gauge mainline metal airlines commit to each market. "
            "Load factor shows how full those aircraft are flying."
        )

        if not segment_df.empty:
            _seg_ct = fy(fa(segment_df, display_airports), year_range)
            _seg_ct = _seg_ct[_seg_ct["SEATS"] > 0].copy()

            _gauge_rows = []
            for (_ap, _yr), grp in _seg_ct.groupby(["ORIGIN", "YEAR"]):
                total_seats = grp["SEATS"].sum()
                total_deps  = grp["DEPARTURES_PERFORMED"].sum()
                total_pax   = grp["PASSENGERS"].sum()
                if total_deps > 0 and total_seats > 0:
                    _gauge_rows.append({
                        "ORIGIN":      _ap,
                        "YEAR":        _yr,
                        "AvgSeats":    total_seats / total_deps,
                        "LoadFactor":  total_pax   / total_seats * 100,
                    })
            gauge_lf_df = pd.DataFrame(_gauge_rows)

            _gauge_yr   = int(year_range[1])
            gauge_now   = gauge_lf_df[gauge_lf_df["YEAR"] == _gauge_yr].copy()
            gauge_now["Label"] = gauge_now["ORIGIN"].map(AIRPORT_NAMES).fillna(gauge_now["ORIGIN"])
            gauge_now   = gauge_now.sort_values("AvgSeats", ascending=True)

            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("#### Avg Seats per Departure")
                st.caption("Higher = airlines deploying larger mainline aircraft. Lower = more regional jets.")
                fig_gauge = go.Figure(go.Bar(
                    x=gauge_now["AvgSeats"],
                    y=gauge_now["Label"],
                    orientation="h",
                    marker_color=[color_map.get(o, "#aaa") for o in gauge_now["ORIGIN"]],
                    text=gauge_now["AvgSeats"].round(0).astype(int).astype(str) + " seats",
                    textposition="outside",
                    textfont=dict(size=11),
                ))
                fig_gauge = layout(fig_gauge, f"Avg Seats per Departure — {_gauge_yr}", legend=False)
                fig_gauge.update_layout(xaxis_title="Avg Seats / Departure", yaxis_title="",
                                        xaxis=dict(range=[0, gauge_now["AvgSeats"].max() * 1.2]))
                if "CMH" in gauge_now["ORIGIN"].values:
                    _cmh_lbl = AIRPORT_NAMES["CMH"]
                    _cmh_gi  = gauge_now["Label"].tolist().index(_cmh_lbl)
                    _cmh_gv  = gauge_now.loc[gauge_now["ORIGIN"] == "CMH", "AvgSeats"].iloc[0]
                    fig_gauge.add_shape(type="rect",
                        x0=-1, x1=_cmh_gv,
                        y0=_cmh_gi - 0.48, y1=_cmh_gi + 0.48,
                        line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_gauge, use_container_width=True)

                if "CMH" in gauge_now["ORIGIN"].values:
                    _cmh_g   = gauge_now.loc[gauge_now["ORIGIN"] == "CMH", "AvgSeats"].iloc[0]
                    _peers_g = gauge_now[gauge_now["ORIGIN"] != "CMH"]
                    _top_g   = _peers_g.loc[_peers_g["AvgSeats"].idxmax()]
                    _gap_g   = (_top_g["AvgSeats"] - _cmh_g) / _cmh_g * 100
                    insight(
                        f"Columbus (CMH) averages <b>{_cmh_g:.0f} seats per departure</b> in {_gauge_yr} — "
                        f"<b>{_gap_g:.0f}% smaller</b> aircraft than {_top_g['Label']} ({_top_g['AvgSeats']:.0f} seats). "
                        f"Smaller gauge reflects a higher share of regional jets; as demand grows, "
                        f"airlines will upsize to mainline aircraft, multiplying capacity without adding frequencies.",
                        sentiment="neutral"
                    )

            with col_g2:
                st.markdown("#### Seat Load Factor Over Time")
                st.caption("Percentage of available seats filled. High load factor = strong demand signal for airlines. 2020–2021 excluded (COVID outliers).")
                fig_lf = go.Figure()
                for _ap in display_airports:
                    _ap_lf = (gauge_lf_df[(gauge_lf_df["ORIGIN"] == _ap) &
                              (~gauge_lf_df["YEAR"].isin([2020, 2021]))]
                              .sort_values("YEAR"))
                    if _ap_lf.empty:
                        continue
                    _is_cmh = _ap == "CMH"
                    fig_lf.add_trace(go.Scatter(
                        x=_ap_lf["YEAR"], y=_ap_lf["LoadFactor"],
                        mode="lines+markers",
                        name=AIRPORT_NAMES.get(_ap, _ap),
                        line=dict(color=color_map.get(_ap, "#aaa"),
                                  width=3.5 if _is_cmh else 1.8),
                        marker=dict(size=9 if _is_cmh else 6,
                                    line=dict(color="white", width=1.5 if _is_cmh else 1)),
                        hovertemplate=f"<b>{AIRPORT_NAMES.get(_ap, _ap)}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
                    ))
                fig_lf = layout(fig_lf, "Seat Load Factor % — All Airports", height=370)
                fig_lf.update_layout(
                    yaxis=dict(title="Load Factor %", ticksuffix="%"),
                    xaxis=dict(title="Year", tickmode="linear", dtick=1, tickformat="d"),
                    hovermode="x unified",
                )
                st.plotly_chart(fig_lf, use_container_width=True)

                if "CMH" in gauge_now["ORIGIN"].values:
                    _cmh_lf  = gauge_now.loc[gauge_now["ORIGIN"] == "CMH", "LoadFactor"].iloc[0]
                    _lf_rank = (gauge_now.sort_values("LoadFactor", ascending=False)
                                ["ORIGIN"].tolist().index("CMH") + 1)
                    # Compare seats vs passengers growth to explain LF direction
                    _lf_prev = gauge_lf_df[(gauge_lf_df["ORIGIN"] == "CMH") &
                                           (gauge_lf_df["YEAR"] == _gauge_yr - 1)]
                    _lf_prev_val = _lf_prev.iloc[0]["LoadFactor"] if not _lf_prev.empty else None
                    _lf_sent = "positive" if _cmh_lf >= 79 else "neutral"
                    if _lf_prev_val and _cmh_lf < _lf_prev_val - 2:
                        insight(
                            f"Columbus (CMH) load factor dipped to <b>{_cmh_lf:.1f}%</b> in {_gauge_yr} "
                            f"(from {_lf_prev_val:.1f}% in {_gauge_yr - 1}), ranking <b>#{_lf_rank} of {len(gauge_now)}</b>. "
                            f"This reflects a capacity-ahead-of-demand dynamic: airlines added departures faster than "
                            f"passenger volume grew, temporarily compressing load factor. "
                            f"Airlines probing a market with extra capacity typically signals confidence in future demand — "
                            f"load factor tends to recover as passengers catch up to the new supply.",
                            sentiment="neutral"
                        )
                    else:
                        insight(
                            f"Columbus (CMH) flies at <b>{_cmh_lf:.1f}% load factor</b> in {_gauge_yr}, "
                            f"ranking <b>#{_lf_rank} of {len(gauge_now)}</b> in the peer group. "
                            f"Load factors above 78% signal sustained airline confidence in the market "
                            f"and support the case for adding frequencies and upgauging aircraft.",
                            sentiment=_lf_sent
                        )
        else:
            st.info("Add BTS T-100 Segment CSV files to `data/bts/` to enable gauge and load factor analysis.")

        st.markdown("---")

        # ── Airport Passenger Ranking Over Time (bump chart) ────
        st.markdown("### Airport Passenger Ranking Over Time")
        st.caption("Rank 1 = most passengers. Tracks how each airport's relative standing has shifted year over year.")
        rank_rows = []
        for yr in range(int(year_range[0]), int(year_range[1])+1):
            yr_pax = (filt_mkt[filt_mkt["YEAR"]==yr]
                      .groupby("ORIGIN")["PASSENGERS"].sum()
                      .sort_values(ascending=False))
            for rank, ap in enumerate(yr_pax.index, 1):
                rank_rows.append({"Year": yr, "Code": ap,
                                  "Airport": AIRPORT_NAMES.get(ap, ap), "Rank": rank})
        if rank_rows:
            rank_df  = pd.DataFrame(rank_rows)
            fig_bump = go.Figure()
            for ap in display_airports:
                ap_name = AIRPORT_NAMES.get(ap, ap)
                ap_rank = rank_df[rank_df["Code"]==ap].sort_values("Year")
                if ap_rank.empty:
                    continue
                is_cmh = ap == "CMH"
                fig_bump.add_trace(go.Scatter(
                    x=ap_rank["Year"], y=ap_rank["Rank"],
                    mode="lines+markers+text",
                    name=ap_name,
                    line=dict(color=color_map.get(ap, "#aaa"),
                              width=3.5 if is_cmh else 1.8),
                    marker=dict(size=10 if is_cmh else 7,
                                line=dict(color="white", width=1.5 if is_cmh else 1)),
                    text=[None]*(len(ap_rank)-1) + [ap_rank["Rank"].iloc[-1]],
                    textposition="middle right",
                    textfont=dict(size=10, color=color_map.get(ap, "#aaa"),
                                  family="Open Sans"),
                    hovertemplate=f"<b>{ap_name}</b><br>%{{x}}: Rank #%{{y}}<extra></extra>",
                ))
            fig_bump = layout(fig_bump, "Peer Airport Ranking by Total Passengers (Rank 1 = Highest)", height=400)
            fig_bump.update_layout(
                yaxis=dict(autorange="reversed", tickmode="linear", dtick=1,
                           title="Rank", tickprefix="#"),
                xaxis=dict(tickmode="linear", dtick=1, tickformat="d", title="Year"),
                margin=dict(r=130), hovermode="x unified",
            )
            st.plotly_chart(fig_bump, use_container_width=True)
            cmh_latest_rank = rank_df[(rank_df["Code"]=="CMH")&(rank_df["Year"]==rank_df["Year"].max())]
            cmh_first_rank  = rank_df[(rank_df["Code"]=="CMH")&(rank_df["Year"]==rank_df["Year"].min())]
            if not cmh_latest_rank.empty and not cmh_first_rank.empty:
                r_now  = int(cmh_latest_rank.iloc[0]["Rank"])
                r_then = int(cmh_first_rank.iloc[0]["Rank"])
                moved  = r_then - r_now
                yr_now  = int(rank_df["Year"].max())
                yr_then = int(rank_df["Year"].min())
                sent   = "positive" if moved >= 0 else "risk"
                insight(f"Columbus (CMH) ranked <b>#{r_now}</b> in {yr_now}, "
                        f"{'up' if moved > 0 else 'down' if moved < 0 else 'unchanged'} "
                        f"{abs(moved) if moved != 0 else ''} spot{'s' if abs(moved) > 1 else ''} "
                        f"from #{r_then} in {yr_then}.", sentiment=sent)

        st.markdown("---")

        # ── COVID Recovery Index ─────────────────────────────────
        st.markdown("### COVID-19 Recovery Index — Passengers vs. 2019 Baseline")
        st.caption("All airports indexed to 2019 = 100. Shows which airports have fully recovered and which are still trailing their pre-pandemic peak.")
        base_yr = 2019
        rec_rows = []
        for ap in display_airports:
            ap_d = market_df[market_df["ORIGIN"]==ap].groupby("YEAR")["PASSENGERS"].sum()
            base = ap_d.get(base_yr, None)
            if base and base > 0:
                for yr, pax in ap_d.items():
                    if int(yr) >= base_yr:
                        rec_rows.append({"Airport": AIRPORT_NAMES.get(ap, ap), "Code": ap,
                                         "Year": int(yr), "Index": round(pax / base * 100, 1)})
        if rec_rows:
            rec_df = pd.DataFrame(rec_rows)
            fig_rec = go.Figure()
            fig_rec.add_hline(y=100, line_dash="dot", line_color="#94a3b8", line_width=1.5,
                              annotation_text="2019 baseline (100)", annotation_position="top right",
                              annotation_font=dict(size=9, color="#94a3b8"))
            for ap in display_airports:
                ap_name = AIRPORT_NAMES.get(ap, ap)
                ap_rec  = rec_df[rec_df["Code"]==ap].sort_values("Year")
                if ap_rec.empty:
                    continue
                is_cmh = ap == "CMH"
                fig_rec.add_trace(go.Scatter(
                    x=ap_rec["Year"], y=ap_rec["Index"],
                    mode="lines+markers",
                    name=ap_name,
                    line=dict(color=color_map.get(ap, "#aaa"),
                              width=3.5 if is_cmh else 1.8),
                    marker=dict(size=9 if is_cmh else 6),
                    hovertemplate=f"<b>{ap_name}</b><br>%{{x}}: %{{y:.1f}} (2019=100)<extra></extra>",
                ))
            fig_rec = layout(fig_rec, "Passenger Recovery Index vs. 2019 Baseline (2019 = 100)", height=400)
            fig_rec.update_layout(xaxis_title="Year", yaxis_title="Index (2019 = 100)",
                                  xaxis=dict(tickmode="linear", dtick=1, tickformat="d"),
                                  hovermode="x unified")
            st.plotly_chart(fig_rec, use_container_width=True)
            latest_rec = rec_df[rec_df["Year"]==rec_df["Year"].max()]
            cmh_rec    = latest_rec[latest_rec["Code"]=="CMH"]
            if not cmh_rec.empty:
                cmh_idx  = cmh_rec.iloc[0]["Index"]
                above    = latest_rec[latest_rec["Index"] > cmh_idx]
                rec_yr   = rec_df["Year"].max()
                sentiment_rec = "positive" if cmh_idx >= 100 else "risk"
                insight(f"Columbus (CMH) stands at <b>{cmh_idx:.1f}</b> on the recovery index in {rec_yr} "
                        f"({'above' if cmh_idx >= 100 else 'below'} its 2019 passenger baseline). "
                        f"{'All' if above.empty else str(len(above))} peer airport{'s' if len(above) != 1 else ''} "
                        f"{'have recovered further.' if not above.empty else 'Columbus leads the peer group in recovery.'}",
                        sentiment=sentiment_rec)


# ══════════════════════════════════════════════════════════════
# TAB 4 · OPERATIONAL INSIGHTS
# ══════════════════════════════════════════════════════════════
with tab_ops:
    if segment_df.empty:
        st.info("Add BTS T-100 Segment CSV files to `data/bts/`.")
    else:
        filt_seg = fy(fa(segment_df, display_airports), year_range)
        _ops_cmh = filt_seg[(filt_seg["ORIGIN"]=="CMH")&(filt_seg["YEAR"]==int(year_range[1]))]
        if not _ops_cmh.empty:
            _ops_lf = (_ops_cmh["PASSENGERS"].sum() / _ops_cmh["SEATS"].sum() * 100
                       if _ops_cmh["SEATS"].sum() > 0 else 0)
            _ops_sz = (_ops_cmh["SEATS"].sum() / _ops_cmh["DEPARTURES_PERFORMED"].sum()
                       if _ops_cmh["DEPARTURES_PERFORMED"].sum() > 0 else 0)
            exec_summary(
                f"Columbus (CMH) operated at a {_ops_lf:.0f}% load factor with an average aircraft size of "
                f"{_ops_sz:.0f} seats per departure in {int(year_range[1])} — "
                f"scroll down to see route-level volume, seasonal patterns, on-time trends, and network expansion."
            )

        FULL_MONTHS = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
                       7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}

        # ── 1. Animated Bubble Chart ────────────────────────────
        st.markdown("### Passenger Volume vs Growth — Animated by Year")
        st.caption("Bubble size = number of unique destinations. Press Play to animate. Excludes 2019–2021 COVID years.")
        bubble_rows = []
        for ap in display_airports:
            ap_d = filt_mkt[filt_mkt["ORIGIN"] == ap]
            for yr in sorted(ap_d["YEAR"].unique()):
                if yr in (2019, 2020, 2021):
                    continue
                yr_d  = ap_d[ap_d["YEAR"] == yr]
                pax   = yr_d["PASSENGERS"].sum()
                ndest = yr_d["DEST"].nunique()
                prev  = ap_d[ap_d["YEAR"] == yr - 1]["PASSENGERS"].sum() if yr - 1 in ap_d["YEAR"].values else None
                yoy   = round((pax - prev) / prev * 100, 1) if prev and prev > 0 else 0
                bubble_rows.append({
                    "Airport": AIRPORT_NAMES.get(ap, ap),
                    "Code": ap,
                    "Year": str(yr),
                    "Passengers (M)": round(pax / 1e6, 3),
                    "YoY Growth %": yoy,
                    "Destinations": ndest,
                })
        if bubble_rows:
            bdf    = pd.DataFrame(bubble_rows)
            x_min  = bdf["Passengers (M)"].min() * 0.85
            x_max  = bdf["Passengers (M)"].max() * 1.08
            y_abs  = max(abs(bdf["YoY Growth %"].min()), abs(bdf["YoY Growth %"].max()))
            y_pad  = y_abs * 1.15 or 5
            fig_bubble = px.scatter(
                bdf, x="Passengers (M)", y="YoY Growth %",
                size="Destinations", color="Airport",
                animation_frame="Year", text="Code",
                size_max=60,
                range_x=[x_min, x_max], range_y=[-y_pad, y_pad],
                color_discrete_map={AIRPORT_NAMES.get(k, k): v for k, v in ALL_COLORS.items()},
                hover_name="Airport",
                hover_data={"Passengers (M)":":.2f","YoY Growth %":":.1f",
                            "Destinations":True,"Code":False,"Year":False},
            )
            fig_bubble.update_traces(textposition="top center",
                                     textfont=dict(size=10, family="Open Sans", color=TEXT_COLOR))
            fig_bubble.add_hline(y=0, line_dash="dot", line_color="#CBD5E0", line_width=1.5)
            fig_bubble = layout(fig_bubble, "Passenger Volume vs YoY Growth — Peer & Aspirational Airports", height=520)
            fig_bubble.update_layout(xaxis_title="Total Passengers (millions)",
                                     yaxis_title="YoY Passenger Growth %", yaxis_ticksuffix="%",
                                     margin=dict(t=60, b=110, l=60, r=110))
            st.plotly_chart(fig_bubble, use_container_width=True)
            latest_b  = bdf[bdf["Year"] == bdf["Year"].max()]
            cmh_b     = latest_b[latest_b["Code"] == "CMH"]
            if not cmh_b.empty:
                cmh_b_row = cmh_b.iloc[0]
                faster    = latest_b[latest_b["YoY Growth %"] > cmh_b_row["YoY Growth %"]]
                insight(f"In {bdf['Year'].max()}, <b>Columbus (CMH)</b> grew <b>{cmh_b_row['YoY Growth %']:+.1f}%</b> with "
                        f"<b>{cmh_b_row['Passengers (M)']:.2f}M passengers</b> across <b>{int(cmh_b_row['Destinations'])} destinations</b> — "
                        f"{'leading the peer group' if faster.empty else f'{len(faster)} peer airport(s) grew faster'}.")

        # ── 2. Route Volume Heatmap ─────────────────────────────
        st.markdown("### CMH Route Volume by Year")
        st.caption("Top 25 routes by total passengers. Color intensity = passenger volume — reveals which routes are growing, fading, or new.")
        if not market_df.empty:
            cmh_all = market_df[market_df["ORIGIN"] == "CMH"]
            top25   = (cmh_all.groupby("DEST")["PASSENGERS"].sum()
                       .sort_values(ascending=False).head(25).index.tolist())
            rv      = (cmh_all[cmh_all["DEST"].isin(top25)]
                       .groupby(["DEST","YEAR"])["PASSENGERS"].sum().reset_index())
            rv_pivot = rv.pivot(index="DEST", columns="YEAR", values="PASSENGERS").fillna(0)
            rv_pivot = rv_pivot.loc[rv_pivot.sum(axis=1).sort_values(ascending=True).index]
            text_vals = (rv_pivot / 1000).round(0).astype(int).astype(str) + "K"
            fig_rv = go.Figure(go.Heatmap(
                z=rv_pivot.values / 1e3,
                x=[str(c) for c in rv_pivot.columns],
                y=rv_pivot.index.tolist(),
                colorscale=[[0,"#F0F4F8"],[0.3,LIGHT_BLUE],[0.65,MED_BLUE],[1.0,NAVY]],
                text=text_vals.values, texttemplate="%{text}",
                textfont=dict(family="Open Sans", size=9, color="#0F171F"),
                showscale=True,
                colorbar=dict(title="Pax (K)", tickfont=dict(family="Open Sans", size=9)),
                hovertemplate="<b>%{y}</b> → %{x}<br>%{text} passengers<extra></extra>",
            ))
            fig_rv = layout(fig_rv, "Columbus (CMH) Passenger Volume by Route & Year (thousands)", height=560, legend=False)
            fig_rv.update_layout(xaxis=dict(type="category", side="bottom", title="Year"),
                                 yaxis=dict(title="", tickfont=dict(size=10)),
                                 margin=dict(t=60, b=60, l=80, r=120))
            st.plotly_chart(fig_rv, use_container_width=True)
            top_route_rv  = rv_pivot.sum(axis=1).idxmax()
            top_route_pax = rv_pivot.sum(axis=1).max()
            years_rv = sorted(rv_pivot.columns)
            if len(years_rv) >= 2:
                growth_rv   = ((rv_pivot[years_rv[-1]] - rv_pivot[years_rv[-2]]) /
                               rv_pivot[years_rv[-2]].replace(0, float("nan")) * 100).dropna()
                fastest_rv  = growth_rv.idxmax()
                fastest_pct = growth_rv.max()
                top_city    = dest_city.get(top_route_rv, top_route_rv)
                fast_city   = dest_city.get(fastest_rv, fastest_rv)
                insight(f"<b>{top_city} ({top_route_rv})</b> is Columbus (CMH)'s highest-volume route with "
                        f"<b>{top_route_pax/1e6:.2f}M passengers</b> since {years_rv[0]}. "
                        f"<b>{fast_city} ({fastest_rv})</b> is the fastest-growing top-25 route, "
                        f"up <b>{fastest_pct:.0f}%</b> in {years_rv[-1]}.", sentiment="positive")

        # ── 3. New/Discontinued Route Map ──────────────────────
        st.markdown("### New Route Additions — CMH Network Expansion")
        if year_range[1] > year_range[0] and not market_df.empty:
            cy, py  = int(year_range[1]), int(year_range[1]) - 1
            cmh_mkt = market_df[market_df["ORIGIN"] == "CMH"]
            new_r   = sorted(set(cmh_mkt[cmh_mkt["YEAR"]==cy]["DEST"].unique()) -
                             set(cmh_mkt[cmh_mkt["YEAR"]==py]["DEST"].unique()))
            drop_r  = sorted(set(cmh_mkt[cmh_mkt["YEAR"]==py]["DEST"].unique()) -
                             set(cmh_mkt[cmh_mkt["YEAR"]==cy]["DEST"].unique()))
            st.caption(f"{py}→{cy}: **{len(new_r)} new destinations** (teal) · **{len(drop_r)} discontinued** (pink)")
            origin_lat, origin_lon = AIRPORT_COORDS["CMH"]
            fig_nr = go.Figure()
            for dest_list, color in [(new_r, TEAL), (drop_r, "#C6397B")]:
                for dest in dest_list:
                    if dest not in AIRPORT_COORDS:
                        continue
                    dlat, dlon = AIRPORT_COORDS[dest]
                    fig_nr.add_trace(go.Scattergeo(
                        lon=[origin_lon, dlon], lat=[origin_lat, dlat],
                        mode="lines", line=dict(width=1.8, color=color),
                        opacity=0.55, hoverinfo="skip", showlegend=False,
                    ))
            for dest_list, color, label in [(new_r, TEAL, "New"), (drop_r, "#C6397B", "Discontinued")]:
                mapped = [d for d in dest_list if d in AIRPORT_COORDS]
                if not mapped:
                    continue
                fig_nr.add_trace(go.Scattergeo(
                    lon=[AIRPORT_COORDS[d][1] for d in mapped],
                    lat=[AIRPORT_COORDS[d][0] for d in mapped],
                    mode="markers+text",
                    marker=dict(size=10, color=color, opacity=0.9, line=dict(color="white", width=1)),
                    text=mapped, textposition="top center",
                    textfont=dict(family="Open Sans", size=8, color=TEXT_COLOR),
                    name=label, showlegend=True,
                ))
            fig_nr.add_trace(go.Scattergeo(
                lon=[origin_lon], lat=[origin_lat], mode="markers",
                marker=dict(size=16, color=NAVY, symbol="star", line=dict(color="white", width=1.5)),
                name="Columbus (CMH)", showlegend=True,
            ))
            fig_nr.update_layout(
                geo=dict(scope="usa", projection_type="albers usa",
                         showland=True, landcolor="#F8F9FA",
                         showlakes=True, lakecolor="#DDEEFF",
                         showcoastlines=True, coastlinecolor="#CBD5E0",
                         showsubunits=True, subunitcolor="#CBD5E0", bgcolor="white"),
                paper_bgcolor="white",
                font=dict(family="Open Sans", color=TEXT_COLOR, size=11),
                legend=dict(orientation="h", y=-0.05, bgcolor="white"),
                height=400, margin=dict(t=10, b=40, l=0, r=0),
            )
            st.plotly_chart(fig_nr, use_container_width=True)
            insight(f"Columbus (CMH) added <b>{len(new_r)} new destinations</b> and dropped <b>{len(drop_r)}</b> "
                    f"between {py} and {cy} — net "
                    f"{'expansion' if len(new_r) >= len(drop_r) else 'contraction'} of "
                    f"<b>{abs(len(new_r)-len(drop_r))} routes</b>.",
                    sentiment="positive" if len(new_r) >= len(drop_r) else "risk")

        # ── 4. Seasonal Heatmap ─────────────────────────────────
        st.markdown("### Seasonal Demand Heatmap — CMH")
        cmh_mo = (fy(segment_df[segment_df["ORIGIN"]=="CMH"], year_range)
                  .groupby(["YEAR","MONTH"])["PASSENGERS"].sum().reset_index())
        if not cmh_mo.empty:
            pivot = cmh_mo.pivot(index="YEAR", columns="MONTH", values="PASSENGERS")
            pivot.columns = [FULL_MONTHS.get(c, c) for c in pivot.columns]
            fig5 = go.Figure(go.Heatmap(
                z=pivot.values/1e3, x=pivot.columns.tolist(),
                y=[str(y) for y in pivot.index.tolist()],
                colorscale=[[0,LIGHT_BLUE],[0.5,MED_BLUE],[1,NAVY]],
                text=(pivot.values/1e3).round(0).astype(int),
                texttemplate="%{text}K", textfont=dict(family="Open Sans", size=9),
                showscale=True, colorbar=dict(title="Pax (K)"),
            ))
            fig5 = layout(fig5, "Columbus (CMH) Monthly Passengers (thousands)", height=320, legend=False)
            fig5.update_layout(xaxis_title="Month", yaxis_title="Year",
                               xaxis=dict(type="category"))
            st.plotly_chart(fig5, use_container_width=True)
            _, peak_mo_idx    = divmod(pivot.values.argmax(), pivot.shape[1])
            _, trough_mo_idx  = divmod(pivot.values.argmin(), pivot.shape[1])
            insight(f"Columbus (CMH) peaks in <b>{pivot.columns[peak_mo_idx]}</b> and hits its seasonal low "
                    f"in <b>{pivot.columns[trough_mo_idx]}</b> — "
                    f"a pattern that guides airline scheduling and revenue management decisions.", sentiment="neutral")

        # ── 5. On-Time Performance Heatmap ─────────────────────
        if not ontime_df.empty:
            st.markdown("### On-Time Performance — Airport Comparison")
            st.caption("Color = combined on-time %. Pink = below average, teal = above average. Columbus (CMH) row outlined in navy.")
            ot_filt = fy(ontime_df[ontime_df["AIRPORT"].isin(display_airports)], year_range, col="YEAR")
            ot_filt["Airport"] = ot_filt["AIRPORT"].map(AIRPORT_NAMES).fillna(ot_filt["AIRPORT"])
            if "COMBINED_ONTIME_PCT" in ot_filt.columns and not ot_filt.empty:
                ot_pivot = (ot_filt.pivot(index="Airport", columns="YEAR", values="COMBINED_ONTIME_PCT")
                            .round(1))
                ot_pivot = ot_pivot.loc[ot_pivot.mean(axis=1).sort_values(ascending=True).index]
                cmh_name = AIRPORT_NAMES.get("CMH", "CMH")
                fig_oth = go.Figure(go.Heatmap(
                    z=ot_pivot.values,
                    x=[str(c) for c in ot_pivot.columns],
                    y=ot_pivot.index.tolist(),
                    colorscale=[[0,"#C6397B"],[0.35,"#FFCCCF"],[0.5,"#FFFFFF"],[0.65,"#BDE1FD"],[1.0,TEAL]],
                    zmid=83,
                    text=ot_pivot.values,
                    texttemplate="%{text:.1f}%",
                    textfont=dict(family="Open Sans", size=11, color="#0F171F"),
                    showscale=True,
                    colorbar=dict(title="On-Time %", ticksuffix="%",
                                  tickfont=dict(family="Open Sans", size=9)),
                    hovertemplate="<b>%{y}</b> · %{x}<br>On-time: %{z:.1f}%<extra></extra>",
                ))
                if cmh_name in ot_pivot.index:
                    ri = ot_pivot.index.tolist().index(cmh_name)
                    fig_oth.add_shape(type="rect",
                        x0=-0.5, x1=len(ot_pivot.columns)-0.5,
                        y0=ri-0.5, y1=ri+0.5,
                        line=dict(color=NAVY, width=2.5), fillcolor="rgba(0,0,0,0)")
                fig_oth = layout(fig_oth, "Combined On-Time % by Airport & Year", height=360, legend=False)
                fig_oth.update_layout(
                    xaxis=dict(type="category", side="bottom", title="Year"),
                    yaxis=dict(title=""),
                    margin=dict(t=60, b=60, l=170, r=130),
                )
                st.plotly_chart(fig_oth, use_container_width=True)
                latest_ot_yr  = ot_pivot.columns.max()
                cmh_ot_latest = ot_pivot.loc[cmh_name, latest_ot_yr] if cmh_name in ot_pivot.index else None
                if cmh_ot_latest:
                    ranked = ot_pivot[latest_ot_yr].sort_values(ascending=False)
                    cmh_rank_ot = list(ranked.index).index(cmh_name) + 1
                    best_ap  = ranked.index[0]
                    insight(f"In {latest_ot_yr}, <b>Columbus (CMH)</b> had a combined on-time rate of "
                            f"<b>{cmh_ot_latest:.1f}%</b>, ranking <b>#{cmh_rank_ot} of {len(ranked)}</b> "
                            f"among peer airports. <b>{best_ap}</b> led the group at "
                            f"<b>{ranked.iloc[0]:.1f}%</b>.")

        # ── 6. Load Factor + Aircraft Size ──────────────────────
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            st.markdown("### Load Factor — Aircraft Efficiency")
            lf = (filt_seg.groupby(["ORIGIN","YEAR"])
                  .agg(PAX=("PASSENGERS","sum"), SEATS=("SEATS","sum")).reset_index())
            lf["LF"] = lf["PAX"]/lf["SEATS"]*100
            lf = lf[~lf["YEAR"].isin([2019, 2020, 2021])]
            lf["Airport"] = lf["ORIGIN"].map(AIRPORT_NAMES).fillna(lf["ORIGIN"])
            fig4 = px.line(lf, x="YEAR", y="LF", color="Airport",
                           color_discrete_map=name_map(color_map), markers=True)
            for tr in fig4.data:
                is_cmh_tr = tr.name == AIRPORT_NAMES.get("CMH", "Columbus (CMH)")
                tr.update(line=dict(width=3.5 if is_cmh_tr else 1.8),
                          marker=dict(size=9 if is_cmh_tr else 6))
            fig4 = layout(fig4, "Load Factor (Passengers ÷ Available Seats) — 2022 onwards")
            fig4.update_layout(yaxis_title="Load Factor (%)", yaxis_ticksuffix="%",
                               xaxis=dict(tickmode="linear"))
            st.plotly_chart(fig4, use_container_width=True)
            cmh_lf = lf[lf["ORIGIN"]=="CMH"].sort_values("YEAR")
            if not cmh_lf.empty:
                latest_lf = cmh_lf.iloc[-1]
                prev_lf   = cmh_lf.iloc[-2] if len(cmh_lf) >= 2 else None
                if prev_lf is not None and latest_lf["LF"] < prev_lf["LF"] - 2:
                    _seats_chg = ((lf[(lf["ORIGIN"]=="CMH") & (lf["YEAR"]==latest_lf["YEAR"])]["SEATS"].sum() /
                                   lf[(lf["ORIGIN"]=="CMH") & (lf["YEAR"]==prev_lf["YEAR"])]["SEATS"].sum() - 1) * 100
                                  if prev_lf["YEAR"] in lf["YEAR"].values else 0)
                    insight(
                        f"Columbus (CMH)'s load factor dipped to <b>{latest_lf['LF']:.1f}%</b> in {int(latest_lf['YEAR'])} "
                        f"(from {prev_lf['LF']:.1f}% in {int(prev_lf['YEAR'])}). "
                        f"The driver is a <b>capacity-ahead-of-demand dynamic</b>: airlines added ~{_seats_chg:.0f}% more seats "
                        f"while passenger growth remained modest. "
                        f"When airlines expand capacity faster than current demand justifies, it typically signals "
                        f"confidence in the market's trajectory — load factor tends to recover as demand catches up.",
                        sentiment="neutral"
                    )
                else:
                    insight(
                        f"Columbus (CMH)'s load factor reached <b>{latest_lf['LF']:.1f}%</b> in {int(latest_lf['YEAR'])} — "
                        f"{'above' if latest_lf['LF'] > 80 else 'below'} the 80% efficiency benchmark, "
                        f"indicating {'strong seat utilization' if latest_lf['LF'] > 80 else 'healthy demand relative to available capacity'}."
                    )

        with col_o2:
            st.markdown("### Average Aircraft Size — Carrier Confidence")
            st.caption("Larger gauge aircraft = carriers betting on sustained demand growth.")
            st_trend = (filt_seg.groupby(["ORIGIN","YEAR"])
                        .agg(SEATS=("SEATS","sum"), DEPS=("DEPARTURES_PERFORMED","sum")).reset_index())
            st_trend["AvgSeats"] = st_trend["SEATS"]/st_trend["DEPS"]
            st_trend["Airport"] = st_trend["ORIGIN"].map(AIRPORT_NAMES).fillna(st_trend["ORIGIN"])
            fig9 = px.line(st_trend, x="YEAR", y="AvgSeats", color="Airport",
                           color_discrete_map=name_map(color_map), markers=True)
            for tr in fig9.data:
                is_cmh_tr = tr.name == AIRPORT_NAMES.get("CMH", "Columbus (CMH)")
                tr.update(line=dict(width=3.5 if is_cmh_tr else 1.8),
                          marker=dict(size=9 if is_cmh_tr else 6))
            fig9 = layout(fig9, "Average Aircraft Size (Seats per Departure)")
            fig9.update_layout(yaxis_title="Avg Seats per Departure",
                               xaxis=dict(tickmode="linear"))
            st.plotly_chart(fig9, use_container_width=True)
            cmh_st = st_trend[st_trend["ORIGIN"]=="CMH"].sort_values("YEAR")
            if not cmh_st.empty:
                latest_st = cmh_st.iloc[-1]
                prev_st   = cmh_st.iloc[-2] if len(cmh_st) > 1 else latest_st
                seat_chg  = latest_st["AvgSeats"] - prev_st["AvgSeats"]
                insight(f"Average aircraft size at Columbus (CMH) is <b>{latest_st['AvgSeats']:.0f} seats</b> "
                        f"in {int(latest_st['YEAR'])}, "
                        f"{'up' if seat_chg >= 0 else 'down'} {abs(seat_chg):.1f} seats from the prior year — "
                        f"{'a signal of growing carrier confidence' if seat_chg >= 0 else 'reflecting tighter capacity deployment'}.")


# ══════════════════════════════════════════════════════════════
# TAB 5 · MARKET OPPORTUNITY
# ══════════════════════════════════════════════════════════════
with tab_market:
    if not data_loaded:
        st.info("Add BTS T-100 data to `data/bts/`.")
    else:
        _mk_yr    = int(market_df["YEAR"].max())
        _mk_cmh_d = set(market_df[(market_df["ORIGIN"]=="CMH")&(market_df["YEAR"]==_mk_yr)]["DEST"].unique())
        _mk_peers = [a for a in ALL_AIRPORTS if a != "CMH"]
        _mk_opp   = sum(
            1 for d in market_df[market_df["YEAR"]==_mk_yr]["DEST"].unique()
            if d not in _mk_cmh_d and
            sum(1 for a in _mk_peers
                if market_df[(market_df["ORIGIN"]==a)&(market_df["YEAR"]==_mk_yr)&(market_df["DEST"]==d)]["PASSENGERS"].sum() > 0) >= 2
        )
        exec_summary(
            f"There are {_mk_opp} markets served by 2+ peer airports that Columbus (CMH) does not fly to in {_mk_yr}. "
            f"The charts below surface underserved frequencies, leakage to nearby airports, and the strongest unserved route opportunities."
        )

        # ── Hub Service Quality — Regional Jet Dominance ─────────────────────
        st.markdown("### Hub Service Quality — Key Business Routes Underserved by Mainline Aircraft")
        st.caption(
            "Columbus (CMH) flies nonstop to major northeast business hubs, but premium travelers face a "
            "service gap: routes dominated by 50–76 seat regional jets offer no lie-flat business class, "
            "limited award availability, and less scheduling flexibility. When demand justifies it, airlines "
            "upgrade to mainline equipment — multiplying capacity without adding new routes."
        )

        _REGIONAL_CARRIERS = {"YX", "9E", "MQ", "OH", "G7", "EV", "OO", "ZW", "QX", "CP", "YV"}
        _HUB_ROUTES = {
            "LGA": ("New York LaGuardia",    "Northeast Corridor — #1 US business market"),
            "BOS": ("Boston Logan",          "Finance, biotech & university hub"),
            "DCA": ("Washington Reagan",     "Government, consulting & lobbying hub"),
        }

        if not segment_df.empty and "UNIQUE_CARRIER" in segment_df.columns:
            _seg_latest  = int(segment_df["YEAR"].max())
            _seg_yr_all  = segment_df[segment_df["YEAR"] == _seg_latest]
            _cmh_seg     = _seg_yr_all[_seg_yr_all["ORIGIN"] == "CMH"].copy()

            # CMH-only metrics for the headline cards
            _hub_rows = []
            for _hub, (_hub_name, _hub_desc) in _HUB_ROUTES.items():
                _r = _cmh_seg[_cmh_seg["DEST"] == _hub]
                if _r.empty:
                    continue
                _total_pax   = _r["PASSENGERS"].sum()
                _total_deps  = _r["DEPARTURES_PERFORMED"].sum()
                _total_seats = _r["SEATS"].sum() if "SEATS" in _r.columns else 0
                _avg_seats   = _total_seats / _total_deps if _total_deps > 0 else 0
                _reg_pax     = _r[_r["UNIQUE_CARRIER"].isin(_REGIONAL_CARRIERS)]["PASSENGERS"].sum()
                _reg_pct     = _reg_pax / _total_pax * 100 if _total_pax > 0 else 0
                _hub_rows.append({
                    "Hub": _hub, "Name": _hub_name, "Desc": _hub_desc,
                    "TotalPax": int(_total_pax), "RegPct": _reg_pct, "AvgSeats": _avg_seats,
                })

            # All-airport metrics for peer comparison
            _comp_rows = []
            for _ap in ALL_AIRPORTS:
                _ap_seg = _seg_yr_all[_seg_yr_all["ORIGIN"] == _ap]
                for _hub in _HUB_ROUTES:
                    _r2 = _ap_seg[_ap_seg["DEST"] == _hub]
                    if _r2.empty:
                        continue
                    _tp2 = _r2["PASSENGERS"].sum()
                    if _tp2 < 500:
                        continue
                    _rp2 = _r2[_r2["UNIQUE_CARRIER"].isin(_REGIONAL_CARRIERS)]["PASSENGERS"].sum()
                    _comp_rows.append({
                        "Airport": _ap,
                        "Hub":     _hub,
                        "RegPct":  _rp2 / _tp2 * 100,
                        "TotalPax": int(_tp2),
                        "Type": "CMH" if _ap == "CMH"
                                else ("Aspirational" if _ap in ASPIRATIONAL_AIRPORTS else "Peer"),
                    })

            if _hub_rows:
                _hub_df = pd.DataFrame(_hub_rows)

                # ── Metric cards ──────────────────────────────────────────
                _card_cols = st.columns(len(_hub_rows))
                for _ci, _crow in enumerate(_hub_df.itertuples(index=False)):
                    with _card_cols[_ci]:
                        _reg_color = "#C6397B" if _crow.RegPct >= 90 else "#0B76DA" if _crow.RegPct >= 70 else TEAL
                        st.markdown(
                            f"<div style='background:#F8FAFD; border:1px solid #e2e8f0; border-radius:10px; "
                            f"padding:18px 16px; text-align:center; height:200px;'>"
                            f"<div style='font-size:22px; font-weight:700; color:{NAVY};'>{_crow.Hub}</div>"
                            f"<div style='font-size:13px; font-weight:600; color:{TEXT_COLOR}; margin:4px 0 2px;'>{_crow.Name}</div>"
                            f"<div style='font-size:11px; color:#6b7280; margin-bottom:12px;'>{_crow.Desc}</div>"
                            f"<div style='font-size:28px; font-weight:700; color:{_reg_color};'>{_crow.RegPct:.0f}%</div>"
                            f"<div style='font-size:11px; color:#6b7280;'>regional jet</div>"
                            f"<div style='font-size:13px; color:{TEXT_COLOR}; margin-top:8px;'>"
                            f"<b>{_crow.TotalPax:,.0f}</b> pax · <b>{_crow.AvgSeats:.0f}</b> avg seats</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Dual-bar: pax volume + CMH regional % ─────────────────
                _hq1, _hq2 = st.columns(2)

                with _hq1:
                    _fig_hubpax = go.Figure(go.Bar(
                        x=_hub_df["Hub"],
                        y=_hub_df["TotalPax"] / 1e3,
                        marker_color=[NAVY, MED_BLUE, TEAL],
                        text=(_hub_df["TotalPax"] / 1e3).round(0).astype(int).astype(str) + "K",
                        textposition="outside",
                        textfont=dict(size=12),
                        hovertemplate="<b>%{x}</b><br>%{y:.0f}K passengers<extra></extra>",
                    ))
                    _fig_hubpax = layout(_fig_hubpax, f"Annual Passengers CMH→Hub ({_seg_latest})",
                                         height=320, legend=False)
                    _fig_hubpax.update_layout(
                        xaxis_title="Hub Airport",
                        yaxis_title="Passengers (thousands)",
                        yaxis=dict(range=[0, _hub_df["TotalPax"].max() / 1e3 * 1.25]),
                    )
                    st.plotly_chart(_fig_hubpax, use_container_width=True)

                with _hq2:
                    _fig_hubpct = go.Figure(go.Bar(
                        x=_hub_df["Hub"],
                        y=_hub_df["RegPct"],
                        marker_color=["#C6397B" if v >= 90 else "#0B76DA" if v >= 70 else TEAL
                                      for v in _hub_df["RegPct"]],
                        text=_hub_df["RegPct"].round(0).astype(int).astype(str) + "%",
                        textposition="outside",
                        textfont=dict(size=12),
                        hovertemplate="<b>%{x}</b><br>%{y:.1f}% regional jet<extra></extra>",
                    ))
                    _fig_hubpct = layout(_fig_hubpct,
                                         f"% Passengers on Regional Jets — CMH→Hub ({_seg_latest})",
                                         height=320, legend=False)
                    _fig_hubpct.update_layout(
                        xaxis_title="Hub Airport",
                        yaxis_title="Regional Jet Share (%)",
                        yaxis=dict(range=[0, 115], ticksuffix="%"),
                    )
                    _fig_hubpct.add_hline(y=100, line_dash="dot", line_color="#aaa",
                        annotation_text="100% regional", annotation_position="top right",
                        annotation_font=dict(size=9, color="#aaa"))
                    st.plotly_chart(_fig_hubpct, use_container_width=True)

                _worst = _hub_df.loc[_hub_df["RegPct"].idxmax()]
                insight(
                    f"Columbus (CMH)'s route to <b>{_worst.Name} ({_worst.Hub})</b> is "
                    f"<b>{_worst.RegPct:.0f}% regional jet</b> — {int(_worst.TotalPax):,} passengers "
                    f"a year averaging just <b>{_worst.AvgSeats:.0f} seats per departure</b>. "
                    f"All three northeast business corridors (LGA, BOS, DCA) are dominated by regional "
                    f"equipment, signaling a structural service gap for Columbus's premium business traveler.",
                    sentiment="risk",
                )

                # ── Peer & Aspirational Comparison ────────────────────────
                if _comp_rows:
                    _comp_df2 = pd.DataFrame(_comp_rows)
                    st.markdown("#### Is CMH Over- or Under-Performing? — Regional Jet Dependency vs. Peers")
                    st.markdown(
                        "<div style='background:#FFF8E1; border-left:4px solid #F59E0B; "
                        "padding:10px 14px; border-radius:4px; margin-bottom:12px; font-size:13px;'>"
                        "<b>How to read these charts:</b> Each bar shows what percentage of passengers "
                        "on that route fly on <b>small regional jets</b> (typically 50–76 seats). "
                        "<b>Lower is better</b> — a shorter bar means more passengers fly on full-size "
                        "mainline aircraft with wider seats, lie-flat business class options, and more "
                        "scheduling frequency. Airports are sorted best-to-worst (lowest regional % at top). "
                        "Columbus (CMH) is highlighted in navy. The dotted line shows the peer group average."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    _cp_cols = st.columns(len(_HUB_ROUTES))
                    _hub_summaries = []
                    for _cpi, (_hub_code, (_hub_lbl, _)) in enumerate(_HUB_ROUTES.items()):
                        with _cp_cols[_cpi]:
                            _cd = (_comp_df2[_comp_df2["Hub"] == _hub_code]
                                   .sort_values("RegPct", ascending=True).copy())
                            if _cd.empty:
                                st.caption(f"No data for {_hub_code}")
                                continue
                            _cd = _cd.reset_index(drop=True)
                            _avg_reg = _cd["RegPct"].mean()
                            _n_total = len(_cd)
                            _cmh_rank = None
                            if "CMH" in _cd["Airport"].values:
                                # rank 1 = lowest regional% = best; rank sorted ascending = position in df + 1
                                _cmh_rank = _cd[_cd["Airport"] == "CMH"].index[0] + 1
                                _cmh_pct  = float(_cd[_cd["Airport"] == "CMH"]["RegPct"].iloc[0])
                                _gap_vs_avg = _cmh_pct - _avg_reg
                                _verdict = "underperforming" if _gap_vs_avg > 5 else ("on par" if abs(_gap_vs_avg) <= 5 else "outperforming")
                                _hub_summaries.append({
                                    "hub": _hub_code, "hub_lbl": _hub_lbl,
                                    "cmh_pct": _cmh_pct, "avg_pct": _avg_reg,
                                    "gap": _gap_vs_avg, "rank": _cmh_rank,
                                    "n": _n_total, "verdict": _verdict,
                                })

                            _cd["Color"] = _cd["Airport"].map(
                                lambda a: NAVY if a == "CMH"
                                else "#C6397B" if a in ASPIRATIONAL_AIRPORTS
                                else LIGHT_BLUE
                            )
                            _rank_label = f"CMH: #{_cmh_rank} of {_n_total}" if _cmh_rank else ""
                            _fig_cmp = go.Figure(go.Bar(
                                x=_cd["RegPct"],
                                y=_cd["Airport"],
                                orientation="h",
                                marker_color=_cd["Color"].tolist(),
                                text=_cd["RegPct"].round(0).astype(int).astype(str) + "%",
                                textposition="outside",
                                textfont=dict(size=10),
                                hovertemplate=(
                                    "<b>%{y}</b><br>Regional jet share: %{x:.1f}%"
                                    "<br><i>Lower = more mainline aircraft</i><extra></extra>"
                                ),
                            ))
                            _title_str = (
                                f"{_hub_code} — {_hub_lbl.split()[0]}<br>"
                                f"<span style='font-size:11px; color:#6b7280;'>{_rank_label}</span>"
                                if _rank_label else f"{_hub_code} — {_hub_lbl.split()[0]}"
                            )
                            _fig_cmp = layout(_fig_cmp, f"→ {_hub_code}", height=300, legend=False)
                            _fig_cmp.update_layout(
                                title=dict(
                                    text=f"<b>{_hub_code}</b> · {_hub_lbl}<br>"
                                         f"<span style='font-size:11px;color:#6b7280'>"
                                         f"{'CMH ranks #' + str(_cmh_rank) + ' of ' + str(_n_total) + ' airports · lower % = more mainline' if _cmh_rank else 'lower % = more mainline'}"
                                         f"</span>",
                                    font=dict(size=13),
                                ),
                                xaxis=dict(range=[0, 118], ticksuffix="%",
                                           title="% passengers on regional jets"),
                                yaxis_title="",
                            )
                            # Peer average reference line
                            _fig_cmp.add_vline(
                                x=_avg_reg, line_dash="dot", line_color="#94a3b8", line_width=1.5,
                                annotation_text=f"avg {_avg_reg:.0f}%",
                                annotation_position="top",
                                annotation_font=dict(size=9, color="#64748b"),
                            )
                            # Teal outline on CMH bar
                            if "CMH" in _cd["Airport"].values:
                                _cmh_yi = _cd["Airport"].tolist().index("CMH")
                                _cmh_xv = float(_cd[_cd["Airport"] == "CMH"]["RegPct"].iloc[0])
                                _fig_cmp.add_shape(type="rect",
                                    y0=_cmh_yi - 0.45, y1=_cmh_yi + 0.45,
                                    x0=0, x1=_cmh_xv,
                                    line=dict(color=TEAL, width=2.5),
                                    fillcolor="rgba(0,0,0,0)")
                            st.plotly_chart(_fig_cmp, use_container_width=True)

                    # Rich per-hub summary insight
                    if _hub_summaries:
                        _verdict_html = ""
                        for _hs in _hub_summaries:
                            _icon  = "🔴" if _hs["verdict"] == "underperforming" else ("🟡" if _hs["verdict"] == "on par" else "🟢")
                            _dir   = (f"<b>{_hs['gap']:.0f} points above</b> the group average"
                                      if _hs["gap"] > 0 else
                                      f"<b>{abs(_hs['gap']):.0f} points below</b> the group average")
                            _verdict_html += (
                                f"<div style='padding:8px 0; border-bottom:1px solid #f0f2f5;'>"
                                f"<b style='color:{NAVY};'>{_hs['hub']} ({_hs['hub_lbl']}):</b> "
                                f"CMH ranks <b>#{_hs['rank']} of {_hs['n']}</b> airports — "
                                f"<b>{_hs['cmh_pct']:.0f}%</b> regional jet, {_dir} "
                                f"({_hs['avg_pct']:.0f}% avg). "
                                f"CMH is <b>{_hs['verdict']}</b> on this route. {_icon}"
                                f"</div>"
                            )
                        st.markdown(
                            f"<div style='background:#F8FAFD; border:1px solid #e2e8f0; "
                            f"border-radius:8px; padding:14px 16px; font-size:13px; margin-top:8px;'>"
                            f"<div style='font-weight:700; color:{NAVY}; margin-bottom:8px;'>"
                            f"CMH Service Quality Scorecard — Northeast Business Hubs</div>"
                            f"{_verdict_html}"
                            f"<div style='margin-top:10px; font-size:11px; color:#6b7280;'>"
                            f"Rank 1 = lowest regional jet % = best mainline service in the group. "
                            f"Underperforming = CMH has more regional jets than the group average on that route.</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

        else:
            # Hardcoded fallback (from 2025 T-100 segment analysis)
            st.markdown("""
| Hub | Airport | Business Significance | Annual Pax | Regional Jet % | Avg Seats |
|-----|---------|----------------------|-----------|---------------|-----------|
| **LGA** | New York LaGuardia | Northeast Corridor — #1 US business market | 210,000 | 79.8% | 86 |
| **BOS** | Boston Logan | Finance, biotech & university hub | 110,000 | 98.2% | 77 |
| **DCA** | Washington Reagan | Government, consulting & lobbying hub | 116,000 | 75.6% | 86 |
""")
            insight(
                "All three of Columbus (CMH)'s top northeast business corridors — "
                "<b>New York LaGuardia (79.8%)</b>, <b>Boston (98.2%)</b>, and <b>Washington Reagan (75.6%)</b> — "
                "are served predominantly by regional jets averaging 77–86 seats. "
                "This structural gap limits premium seat availability and signals upgrade opportunity as demand grows.",
                sentiment="risk",
            )

        # ── Travel Character ─────────────────────────────────────────
        st.markdown("### Travel Character — Leisure vs. Business")
        st.caption(
            "Carrier type mix and destination profile reveal the character of each airport's passenger base. "
            "ULCC = Frontier/Spirit/Allegiant/Sun Country · LCC = Southwest/JetBlue/Alaska · Network = AA/DL/UA"
        )

        _ULCC = {"F9", "NK", "G4", "SY"}
        _LCC  = {"WN", "B6", "AS"}
        _NET  = {"AA", "DL", "UA"}

        _LEISURE_DESTS = {
            "MCO","LAS","FLL","TPA","RSW","MIA","PBI","SRQ","SFB","PIE","DAB",
            "HNL","OGG","KOA","LIH","SJU","VPS","PNS","ECP","BZN","HDN","ASE",
            "MTJ","ACK","MVY","SNA","SBA","SAN","BUR","LGB","ONT","PSP","TUS",
        }
        _BUSINESS_DESTS = {
            "JFK","LGA","EWR","ORD","MDW","DFW","DAL","LAX","SFO","OAK","SJC",
            "BOS","IAD","DCA","ATL","CLT","PHX","DEN","MSP","DTW","SEA","IAH",
            "HOU","PHL","BWI","SLC","PDX","MCI","STL","RDU","AUS","BNA","IND",
            "CMH","CVG","CLE","PIT","DAY","MDT","RIC","CHS","GSP","BDL","MKE",
        }

        _mk_filt = fy(fa(market_df, display_airports), year_range)
        _mk_now  = _mk_filt[_mk_filt["YEAR"] == _mk_yr].copy()

        def _ctype(c):
            if c in _ULCC: return "ULCC"
            if c in _LCC:  return "LCC"
            if c in _NET:  return "Network"
            return "Other"

        def _dtype(d):
            if d in _LEISURE_DESTS:  return "Leisure"
            if d in _BUSINESS_DESTS: return "Business"
            return "Mixed"

        _mk_now["CTYPE"] = _mk_now["UNIQUE_CARRIER"].map(_ctype)
        _mk_now["DTYPE"] = _mk_now["DEST"].map(_dtype)

        _cmix = (_mk_now.groupby(["ORIGIN", "CTYPE"])["PASSENGERS"].sum()
                 .unstack(fill_value=0))
        _cmix_pct = _cmix.div(_cmix.sum(axis=1), axis=0) * 100

        _dmix = (_mk_now.groupby(["ORIGIN", "DTYPE"])["PASSENGERS"].sum()
                 .unstack(fill_value=0))
        _dmix_pct = _dmix.div(_dmix.sum(axis=1), axis=0) * 100

        _tc_col1, _tc_col2 = st.columns(2)

        with _tc_col1:
            st.markdown("#### Carrier Type Mix")
            _ct_order  = (_cmix_pct.get("ULCC", pd.Series(0, index=_cmix_pct.index))
                          .sort_values(ascending=True).index.tolist())
            _ct_labels = [AIRPORT_NAMES.get(a, a) for a in _ct_order]
            _ct_colors = {"ULCC": "#C6397B", "LCC": "#0B76DA", "Network": "#002F6C", "Other": "#86C5FA"}

            fig_cmix = go.Figure()
            for _ct in ["Other", "LCC", "ULCC", "Network"]:
                if _ct not in _cmix_pct.columns:
                    continue
                _vals = [_cmix_pct.loc[a, _ct] if a in _cmix_pct.index else 0 for a in _ct_order]
                fig_cmix.add_trace(go.Bar(
                    x=_vals, y=_ct_labels, orientation="h",
                    name=_ct, marker_color=_ct_colors.get(_ct, "#aaa"),
                    text=[f"{v:.0f}%" if v >= 6 else "" for v in _vals],
                    textposition="inside",
                    textfont=dict(size=10, color="white"),
                    hovertemplate=f"<b>%{{y}}</b><br>{_ct}: %{{x:.1f}}%<extra></extra>",
                ))
            fig_cmix = layout(fig_cmix, f"Carrier Type Mix — {_mk_yr}", legend=True)
            fig_cmix.update_layout(
                barmode="stack",
                xaxis=dict(title="% of Passengers", ticksuffix="%", range=[0, 100]),
                yaxis_title="",
                legend=dict(orientation="h", x=0, y=-0.18, font=dict(size=10)),
            )
            if "CMH" in _ct_order:
                _cmh_ci = _ct_order.index("CMH")
                fig_cmix.add_shape(type="rect",
                    x0=0, x1=100,
                    y0=_cmh_ci - 0.48, y1=_cmh_ci + 0.48,
                    line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_cmix, use_container_width=True)

        with _tc_col2:
            st.markdown("#### Destination Profile")
            _dt_order  = (_dmix_pct.get("Business", pd.Series(0, index=_dmix_pct.index))
                          .sort_values(ascending=True).index.tolist())
            _dt_labels = [AIRPORT_NAMES.get(a, a) for a in _dt_order]
            _dt_colors = {"Leisure": "#C6397B", "Mixed": "#86C5FA", "Business": "#002F6C"}

            fig_dmix = go.Figure()
            for _dt in ["Leisure", "Mixed", "Business"]:
                if _dt not in _dmix_pct.columns:
                    continue
                _vals = [_dmix_pct.loc[a, _dt] if a in _dmix_pct.index else 0 for a in _dt_order]
                fig_dmix.add_trace(go.Bar(
                    x=_vals, y=_dt_labels, orientation="h",
                    name=_dt, marker_color=_dt_colors.get(_dt, "#aaa"),
                    text=[f"{v:.0f}%" if v >= 6 else "" for v in _vals],
                    textposition="inside",
                    textfont=dict(size=10, color="white"),
                    hovertemplate=f"<b>%{{y}}</b><br>{_dt}: %{{x:.1f}}%<extra></extra>",
                ))
            fig_dmix = layout(fig_dmix, f"Destination Profile — {_mk_yr}", legend=True)
            fig_dmix.update_layout(
                barmode="stack",
                xaxis=dict(title="% of Passengers", ticksuffix="%", range=[0, 100]),
                yaxis_title="",
                legend=dict(orientation="h", x=0, y=-0.18, font=dict(size=10)),
            )
            if "CMH" in _dt_order:
                _cmh_di = _dt_order.index("CMH")
                fig_dmix.add_shape(type="rect",
                    x0=0, x1=100,
                    y0=_cmh_di - 0.48, y1=_cmh_di + 0.48,
                    line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_dmix, use_container_width=True)

        # Travel character insight
        if "CMH" in _cmix_pct.index and "CMH" in _dmix_pct.index:
            _cmh_ulcc = _cmix_pct.loc["CMH", "ULCC"]   if "ULCC"    in _cmix_pct.columns else 0
            _cmh_net  = _cmix_pct.loc["CMH", "Network"] if "Network" in _cmix_pct.columns else 0
            _cmh_leis = _dmix_pct.loc["CMH", "Leisure"] if "Leisure" in _dmix_pct.columns else 0
            _cmh_biz  = _dmix_pct.loc["CMH", "Business"]if "Business"in _dmix_pct.columns else 0
            _asps     = [a for a in ["AUS", "BNA", "RDU"] if a in _dmix_pct.index]
            _asp_leis = (_dmix_pct.loc[_asps, "Leisure"].mean()
                         if _asps and "Leisure" in _dmix_pct.columns else 0)
            _asp_ulcc = (_cmix_pct.loc[_asps, "ULCC"].mean()
                         if _asps and "ULCC" in _cmix_pct.columns else 0)
            insight(
                f"Columbus (CMH) sends <b>{_cmh_biz:.0f}% of passengers to business/hub markets</b>, "
                f"higher than aspirational peers AUS/BNA/RDU (avg {100 - _asp_leis:.0f}%). "
                f"With only <b>{_cmh_leis:.0f}% leisure-destination traffic</b> vs. peers' {_asp_leis:.0f}%, "
                f"CMH's leisure segment is its clearest growth frontier. "
                f"CMH's <b>{_cmh_ulcc:.0f}% ULCC share</b> — well below the peer average of {_asp_ulcc:.0f}% — "
                f"suggests significant untapped appetite for ultra-low-cost leisure routes.",
                sentiment="positive"
            )

        st.markdown("---")

        col_mk1, col_mk2 = st.columns(2)

        with col_mk1:
            # ── 7. Route Frequency (map + bar) ─────────────────
            st.markdown("### Underserved Routes — Frequency Gap Map")
            st.caption("Routes with ≤10 weekly flights from Columbus (CMH). Dot size = weekly frequency. Teal = thin coverage.")
            if not segment_df.empty:
                cmh_seg_yr = segment_df[(segment_df["ORIGIN"]=="CMH")&
                                        (segment_df["YEAR"]==int(year_range[1]))]
                if not cmh_seg_yr.empty:
                    rf = (cmh_seg_yr.groupby("DEST")["DEPARTURES_PERFORMED"].sum().reset_index())
                    rf["Weekly"] = rf["DEPARTURES_PERFORMED"]/52
                    rf = rf[rf["Weekly"]<=10].sort_values("Weekly")
                    if not rf.empty:
                        # Geo map of underserved routes
                        origin_lat, origin_lon = AIRPORT_COORDS.get("CMH", (39.998, -82.892))
                        fig7m = go.Figure()
                        mapped_rf = rf[rf["DEST"].isin(AIRPORT_COORDS)]
                        for _, row in mapped_rf.iterrows():
                            dlat, dlon = AIRPORT_COORDS[row["DEST"]]
                            fig7m.add_trace(go.Scattergeo(
                                lon=[origin_lon, dlon], lat=[origin_lat, dlat],
                                mode="lines",
                                line=dict(width=max(0.8, row["Weekly"]*0.3), color=TEAL),
                                opacity=0.45, hoverinfo="skip", showlegend=False,
                            ))
                        fig7m.add_trace(go.Scattergeo(
                            lon=[AIRPORT_COORDS[d][1] for d in mapped_rf["DEST"] if d in AIRPORT_COORDS],
                            lat=[AIRPORT_COORDS[d][0] for d in mapped_rf["DEST"] if d in AIRPORT_COORDS],
                            mode="markers+text",
                            marker=dict(
                                size=mapped_rf[mapped_rf["DEST"].isin(AIRPORT_COORDS)]["Weekly"].clip(2, 12) * 2.5,
                                color=mapped_rf[mapped_rf["DEST"].isin(AIRPORT_COORDS)]["Weekly"],
                                colorscale=[[0, LIGHT_BLUE],[0.5, TEAL],[1, NAVY]],
                                showscale=True,
                                colorbar=dict(title="Flights/wk", x=1.0,
                                              tickfont=dict(size=9)),
                                line=dict(color="white", width=1),
                            ),
                            text=mapped_rf[mapped_rf["DEST"].isin(AIRPORT_COORDS)]["DEST"].tolist(),
                            textposition="top center",
                            textfont=dict(size=8, family="Open Sans"),
                            name="Underserved",
                            hovertemplate="<b>%{text}</b><br>~%{marker.color:.1f} flights/week<extra></extra>",
                        ))
                        fig7m.add_trace(go.Scattergeo(
                            lon=[origin_lon], lat=[origin_lat], mode="markers",
                            marker=dict(size=14, color=NAVY, symbol="star",
                                        line=dict(color="white", width=1.5)),
                            name="Columbus (CMH)", showlegend=True,
                        ))
                        fig7m.update_layout(
                            geo=dict(scope="usa", projection_type="albers usa",
                                     showland=True, landcolor="#F8F9FA",
                                     showlakes=True, lakecolor="#DDEEFF",
                                     showcoastlines=True, coastlinecolor="#CBD5E0",
                                     bgcolor="white"),
                            paper_bgcolor="white",
                            font=dict(family="Open Sans", size=10),
                            legend=dict(orientation="h", y=-0.06),
                            height=380, margin=dict(t=10, b=40, l=0, r=0),
                        )
                        st.plotly_chart(fig7m, use_container_width=True)
                        top_under_city = dest_city.get(rf.iloc[0]['DEST'], rf.iloc[0]['DEST'])
                        insight(f"<b>{len(rf)} routes</b> from Columbus average ≤10 flights/week — "
                                f"markets like <b>{top_under_city} ({rf.iloc[0]['DEST']})</b> ({rf.iloc[0]['Weekly']:.1f}/wk) "
                                f"represent the clearest frequency expansion opportunities.", sentiment="positive")

        with col_mk2:
            # ── 8. Carrier Network Growth ───────────────────────
            st.markdown("### Carrier Growth at CMH")
            carrier_col = "UNIQUE_CARRIER_NAME" if "UNIQUE_CARRIER_NAME" in market_df.columns else "CARRIER_NAME"
            cmh_car = (fy(market_df[market_df["ORIGIN"]=="CMH"], year_range)
                       .groupby([carrier_col,"YEAR"])["PASSENGERS"].sum().reset_index())
            cmh_car = cmh_car.rename(columns={carrier_col:"Carrier"})
            top_c = cmh_car.groupby("Carrier")["PASSENGERS"].sum().nlargest(6).index
            fig8 = px.bar(cmh_car[cmh_car["Carrier"].isin(top_c)],
                          x="YEAR", y="PASSENGERS", color="Carrier", barmode="group",
                          color_discrete_sequence=CHART_COLORS)
            fig8 = layout(fig8, "Columbus (CMH) Passengers by Carrier — Annual", height=340)
            fig8.update_layout(xaxis_title="Year", yaxis_title="Passengers",
                               xaxis=dict(tickmode="linear"))
            st.plotly_chart(fig8, use_container_width=True)
            latest_car = cmh_car[cmh_car["YEAR"]==cmh_car["YEAR"].max()]
            if not latest_car.empty:
                top_c_row = latest_car.loc[latest_car["PASSENGERS"].idxmax()]
                insight(f"<b>{top_c_row['Carrier']}</b> is Columbus (CMH)'s largest carrier by passengers in {int(top_c_row['YEAR'])}, "
                        f"carrying <b>{top_c_row['PASSENGERS']:,.0f}</b> — watch for concentration risk if a single carrier dominates.", sentiment="risk")

        # ── Nearby Airport Leakage (T-100 proxy) ───────────────
        st.markdown("### Nearby Airport Flight Volume — CMH Market Share Proxy")
        st.caption("Approximated from T-100 total departures. Columbus residents flying from DAY, CVG, or CLE represent leakage from the Columbus (CMH) catchment area.")
        leak = (fy(market_df[market_df["ORIGIN"].isin(LEAKAGE_AIRPORTS)], year_range)
                .groupby(["ORIGIN","YEAR"])["PASSENGERS"].sum().reset_index())
        leak_yr = leak[leak["YEAR"]==int(year_range[1])]
        if not leak_yr.empty:
            lk1, lk2 = st.columns(2)
            with lk1:
                total_pax = leak_yr["PASSENGERS"].sum()
                leak_yr   = leak_yr.copy()
                leak_yr["Share %"] = leak_yr["PASSENGERS"]/total_pax*100
                leak_yr["Airport"] = leak_yr["ORIGIN"].map(AIRPORT_NAMES).fillna(leak_yr["ORIGIN"])
                leak_yr["Color"]   = leak_yr["ORIGIN"].map(PEER_COLORS)
                fig_lk = go.Figure(go.Pie(
                    labels=leak_yr["Airport"], values=leak_yr["PASSENGERS"],
                    hole=0.5, marker=dict(colors=leak_yr["Color"].tolist()),
                    textinfo="percent", textfont=dict(size=11),
                ))
                fig_lk.update_layout(paper_bgcolor="white", height=300,
                                      margin=dict(t=10,b=10,l=10,r=10),
                                      font=dict(family="Open Sans"),
                                      legend=dict(font=dict(size=9)))
                st.plotly_chart(fig_lk, use_container_width=True)
            with lk2:
                leak_trend = leak.copy()
                leak_trend["Airport"] = leak_trend["ORIGIN"].map(AIRPORT_NAMES).fillna(leak_trend["ORIGIN"])
                fig_lkt = px.area(leak_trend, x="YEAR", y="PASSENGERS", color="Airport",
                                  color_discrete_map=name_map(PEER_COLORS))
                fig_lkt = layout(fig_lkt, "Catchment Area — Passengers by Departure Airport", height=300)
                fig_lkt.update_layout(xaxis_title="Year", yaxis_title="Passengers",
                                       xaxis=dict(tickmode="linear"))
                st.plotly_chart(fig_lkt, use_container_width=True)
            cmh_share_row = leak_yr[leak_yr["ORIGIN"]=="CMH"]
            if not cmh_share_row.empty:
                cmh_share_pct = cmh_share_row.iloc[0]["Share %"]
                insight(f"Columbus (CMH) captures <b>{cmh_share_pct:.0f}%</b> of the four-airport catchment area's total passengers — "
                        f"every point of share gained from Dayton (DAY), Cincinnati (CVG), or Cleveland (CLE) represents tens of thousands of additional travelers.",
                        sentiment="positive" if cmh_share_pct >= 50 else "neutral")

        # ── Route Opportunity Analysis ──────────────────────────
        st.markdown("### Route Opportunity Analysis — What Are CMH's Peers Flying That CMH Isn't?")
        st.caption("Routes served by 2+ peer or aspirational airports in the latest year that Columbus (CMH) does not serve. Higher peer volume = stronger proven demand signal.")
        opp_yr = int(market_df["YEAR"].max())
        cmh_dests  = set(market_df[(market_df["ORIGIN"]=="CMH") & (market_df["YEAR"]==opp_yr)]["DEST"].unique())
        peer_codes  = [a for a in ALL_AIRPORTS if a != "CMH"]
        opp_rows = []
        for dest in market_df[market_df["YEAR"]==opp_yr]["DEST"].unique():
            if dest in cmh_dests:
                continue
            serving = []
            total_peer_pax = 0
            for ap in peer_codes:
                ap_pax = market_df[(market_df["ORIGIN"]==ap) & (market_df["YEAR"]==opp_yr) & (market_df["DEST"]==dest)]["PASSENGERS"].sum()
                if ap_pax > 0:
                    serving.append(ap)
                    total_peer_pax += ap_pax
            if len(serving) >= 2:
                opp_rows.append({
                    "Destination": dest,
                    "Peers Serving": len(serving),
                    "Peer Airports": ", ".join(serving),
                    "Total Peer Pax": total_peer_pax,
                })
        if opp_rows:
            opp_df = (pd.DataFrame(opp_rows)
                      .sort_values(["Peers Serving","Total Peer Pax"], ascending=False)
                      .head(20).reset_index(drop=True))
            opp_df.index += 1
            # Add city name labels: "City Name (CODE)"
            opp_df["Label"] = opp_df["Destination"].apply(
                lambda c: f"{dest_city.get(c, c)} ({c})" if dest_city.get(c, c) != c else c
            )
            # Expand peer airport codes to city names too
            def _peer_labels(codes_str):
                parts = [c.strip() for c in codes_str.split(",")]
                return ", ".join(
                    f"{dest_city.get(p, AIRPORT_NAMES.get(p, p))} ({p})" for p in parts
                )
            opp_df["Peer Labels"] = opp_df["Peer Airports"].apply(_peer_labels)

            oc1, oc2 = st.columns([2, 1])
            with oc1:
                fig_opp = go.Figure(go.Bar(
                    x=opp_df["Total Peer Pax"] / 1e3,
                    y=opp_df["Label"],
                    orientation="h",
                    marker=dict(
                        color=opp_df["Peers Serving"],
                        colorscale=[[0, LIGHT_BLUE], [0.5, MED_BLUE], [1, NAVY]],
                        showscale=True,
                        colorbar=dict(title="# Peers<br>Serving", tickfont=dict(size=9)),
                    ),
                    text=(opp_df["Total Peer Pax"]/1e3).round(0).astype(int).astype(str) + "K",
                    textposition="outside",
                    customdata=opp_df[["Peers Serving","Peer Labels"]].values,
                    hovertemplate="<b>%{y}</b><br>Peer passengers: %{x:.0f}K<br>Served by %{customdata[0]} peers: %{customdata[1]}<extra></extra>",
                ))
                fig_opp = layout(fig_opp, f"Top Unserved Markets — Peer Passenger Volume ({opp_yr})", height=480, legend=False)
                fig_opp.update_layout(xaxis_title="Combined Peer Passengers (thousands)", yaxis_title="",
                                      yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_opp, use_container_width=True)

            with oc2:
                st.markdown(f"**Top Opportunities ({opp_yr})**")
                for _, row in opp_df.head(8).iterrows():
                    st.markdown(
                        f"<div style='padding:7px 0; border-bottom:1px solid #f0f2f5;'>"
                        f"<span style='font-weight:600; color:{NAVY}; font-size:13px;'>{row['Label']}</span><br>"
                        f"<span style='font-size:11px; color:#6b7280;'>{row['Peers Serving']} peers · {row['Total Peer Pax']:,.0f} pax</span><br>"
                        f"<span style='font-size:10px; color:{TEAL};'>{row['Peer Labels']}</span>"
                        f"</div>",
                        unsafe_allow_html=True)

            # ── Route Opportunity Map ───────────────────────────────
            st.markdown("### Columbus (CMH) Route Opportunity Map")
            st.caption(
                "Every circle is a US destination. "
                "<b style='color:#002F6C;'>Navy</b> = Columbus (CMH) already serves it. "
                "<b style='color:#C6397B;'>Pink</b> = peers serve it but Columbus (CMH) does not — "
                "larger circles = more peer passengers. Columbus (CMH) shown as ★.",
                unsafe_allow_html=True,
            )

            # Extended coordinate lookup for common US airports
            MAP_COORDS = {
                **AIRPORT_COORDS,
                "PDX":(45.589,-122.593),"RIC":(37.505,-77.320),"SFB":(28.777,-81.237),
                "SAV":(32.127,-81.201),"DSM":(41.534,-93.663),"ECP":(30.357,-85.797),
                "VPS":(30.483,-86.525),"PGD":(26.920,-81.991),"PIE":(27.910,-82.687),
                "EYW":(24.556,-81.760),"SDF":(38.174,-85.736),"EUG":(44.125,-123.212),
                "CHA":(35.035,-85.204),"HRL":(26.228,-97.654),"ROC":(43.119,-77.672),
                "AMA":(35.219,-101.706),"MDT":(40.193,-76.763),"GRB":(44.485,-88.130),
                "ADS":(32.969,-96.836),"ABQ":(35.040,-106.609),"TUL":(36.198,-95.888),
                "OKC":(35.393,-97.601),"RNO":(39.499,-119.768),"BOI":(43.565,-116.223),
                "GEG":(47.620,-117.534),"BUF":(42.941,-78.732),"RDU":(35.878,-78.787),
                "SJC":(37.363,-121.929),"ONT":(34.056,-117.601),"BHM":(33.563,-86.754),
                "HSV":(34.637,-86.775),"LIT":(34.729,-92.224),"ICT":(37.650,-97.433),
                "TYS":(35.811,-83.994),"CAE":(33.939,-81.120),"MHT":(42.933,-71.436),
                "PWM":(43.646,-70.309),"BTV":(44.472,-73.153),"ALB":(42.748,-73.802),
                "SYR":(43.111,-76.106),"AVL":(35.436,-82.541),"GSP":(34.895,-82.219),
                "CHS":(32.899,-80.041),"JAX":(30.494,-81.688),"PNS":(30.473,-87.187),
                "MOB":(30.691,-88.243),"GPT":(30.407,-89.070),"SHV":(32.447,-93.826),
                "BTR":(30.533,-91.150),"JAN":(32.311,-90.076),"AGS":(33.370,-81.964),
                "CSG":(32.516,-84.939),"TLH":(30.396,-84.350),"GNV":(29.690,-82.272),
                "DAB":(29.180,-81.058),"MLB":(28.102,-80.645),"SRQ":(27.396,-82.555),
                "PBI":(26.683,-80.096),"FPR":(27.495,-80.368),"GGG":(32.384,-94.712),
                "TXK":(33.453,-93.991),"XNA":(36.282,-94.307),"CRP":(27.770,-97.502),
                "MFE":(26.176,-98.239),"LBB":(33.664,-101.823),"MAF":(31.943,-102.202),
                "ELP":(31.807,-106.378),"ABY":(31.535,-84.195),"VLD":(30.782,-83.277),
                "GRR":(42.881,-85.523),"FNT":(42.966,-83.744),"LAN":(42.778,-84.587),
                "TOL":(41.587,-83.808),"EVV":(38.037,-87.532),"SBN":(41.709,-86.317),
                "FWA":(40.978,-85.195),"BMI":(40.477,-88.916),"MDW":(41.787,-87.752),
            }

            # Build per-destination served/unserved status for latest year
            opp_yr_data = filt_mkt[filt_mkt["YEAR"] == opp_yr]
            cmh_dests   = set(opp_yr_data[opp_yr_data["ORIGIN"]=="CMH"]["DEST"].unique())
            peer_dests  = (
                opp_yr_data[opp_yr_data["ORIGIN"].isin([a for a in display_airports if a != "CMH"])]
                .groupby("DEST")["PASSENGERS"].sum()
            )
            # Only US domestic (in MAP_COORDS)
            map_rows = []
            for dest, pax in peer_dests.items():
                if dest not in MAP_COORDS:
                    continue
                served = dest in cmh_dests
                cmh_pax = opp_yr_data[(opp_yr_data["ORIGIN"]=="CMH")&(opp_yr_data["DEST"]==dest)]["PASSENGERS"].sum()
                map_rows.append({
                    "Dest": dest,
                    "City": dest_city.get(dest, dest),
                    "Lat": MAP_COORDS[dest][0],
                    "Lon": MAP_COORDS[dest][1],
                    "PeerPax": int(pax),
                    "CMHPax": int(cmh_pax),
                    "Served": served,
                })
            if map_rows:
                map_df = pd.DataFrame(map_rows)
                served_df   = map_df[map_df["Served"]]
                unserved_df = map_df[~map_df["Served"]]

                fig_map = go.Figure()

                # Unserved: pink, sized by peer volume
                if not unserved_df.empty:
                    max_pax = unserved_df["PeerPax"].max()
                    fig_map.add_trace(go.Scattergeo(
                        lat=unserved_df["Lat"], lon=unserved_df["Lon"],
                        mode="markers",
                        marker=dict(
                            size=(unserved_df["PeerPax"] / max_pax * 28 + 5).clip(5, 33),
                            color="#C6397B", opacity=0.70,
                            line=dict(color="white", width=0.8),
                        ),
                        name="Unserved by CMH",
                        customdata=unserved_df[["City","Dest","PeerPax"]].values,
                        hovertemplate="<b>%{customdata[0]} (%{customdata[1]})</b><br>"
                                      "Peer passengers: %{customdata[2]:,}<br>"
                                      "Columbus (CMH): not served<extra></extra>",
                    ))

                # Served: navy, fixed small size
                if not served_df.empty:
                    fig_map.add_trace(go.Scattergeo(
                        lat=served_df["Lat"], lon=served_df["Lon"],
                        mode="markers",
                        marker=dict(
                            size=8, color=NAVY, opacity=0.55,
                            line=dict(color="white", width=0.6),
                        ),
                        name="Served by CMH",
                        customdata=served_df[["City","Dest","CMHPax","PeerPax"]].values,
                        hovertemplate="<b>%{customdata[0]} (%{customdata[1]})</b><br>"
                                      "Columbus (CMH): %{customdata[2]:,} pax<br>"
                                      "Peers: %{customdata[3]:,} pax<extra></extra>",
                    ))

                # CMH star
                fig_map.add_trace(go.Scattergeo(
                    lat=[39.998], lon=[-82.892],
                    mode="markers+text",
                    marker=dict(size=18, color=TEAL, symbol="star",
                                line=dict(color="white", width=1.5)),
                    text=["CMH"], textposition="top right",
                    textfont=dict(size=11, color=NAVY, family="Open Sans"),
                    name="Columbus (CMH)",
                    hovertemplate="<b>Columbus (CMH)</b><extra></extra>",
                ))

                fig_map.update_layout(
                    geo=dict(
                        scope="usa",
                        showland=True, landcolor="#F8F9FA",
                        showlakes=True, lakecolor="#DDEEFF",
                        showcoastlines=True, coastlinecolor="#CBD5E0",
                        showframe=False,
                        projection_type="albers usa",
                    ),
                    paper_bgcolor="white",
                    font=dict(family="Open Sans", size=10, color=TEXT_COLOR),
                    legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center",
                                font=dict(size=11), bgcolor="white"),
                    height=440,
                    margin=dict(t=10, b=40, l=0, r=0),
                )
                st.plotly_chart(fig_map, use_container_width=True)

            top_opp = opp_df.iloc[0]
            top_opp_city = dest_city.get(top_opp['Destination'], top_opp['Destination'])
            insight(f"<b>{top_opp_city} ({top_opp['Destination']})</b> is Columbus (CMH)'s strongest unserved opportunity — "
                    f"<b>{int(top_opp['Peers Serving'])} peer airports</b> already fly there carrying "
                    f"<b>{top_opp['Total Peer Pax']:,.0f} passengers</b> in {opp_yr}, proving market demand exists.", sentiment="positive")
            st.download_button(
                label="⬇  Download Route Opportunities CSV",
                data=opp_df.to_csv(index=False),
                file_name=f"cmh_route_opportunities_{opp_yr}.csv",
                mime="text/csv",
            )



# ══════════════════════════════════════════════════════════════
# TAB 6 · INTERNATIONAL OPPORTUNITY
# ══════════════════════════════════════════════════════════════
with tab_intl:
    intl_loaded   = not intl_df.empty
    gateway_loaded = not gateway_df.empty
    db1b_loaded   = not db1b_df.empty

    INTL_GATEWAYS = ["JFK", "EWR", "LAX", "MIA", "IAD", "ORD", "ATL", "SFO",
                     "DFW", "BOS", "IAH", "SEA", "DTW"]
    GATEWAY_LABELS = {
        "JFK": "New York JFK", "EWR": "Newark EWR", "LAX": "Los Angeles LAX",
        "MIA": "Miami MIA",    "IAD": "Washington IAD", "ORD": "Chicago ORD",
        "ATL": "Atlanta ATL",  "SFO": "San Francisco SFO", "DFW": "Dallas DFW",
        "BOS": "Boston BOS",   "IAH": "Houston IAH",  "SEA": "Seattle SEA",
        "DTW": "Detroit DTW",
    }
    GATEWAY_REGION = {
        "JFK": "Atlantic/Europe", "EWR": "Atlantic/Europe", "LAX": "Pacific/Asia",
        "MIA": "Latin America",   "IAD": "Atlantic/Europe", "ORD": "Global",
        "ATL": "Global",          "SFO": "Pacific/Asia",    "DFW": "Global",
        "BOS": "Atlantic/Europe", "IAH": "Latin America",   "SEA": "Pacific/Asia",
        "DTW": "Atlantic/Europe",
    }

    # ── Section 1: Gateway Connectivity ─────────────────────────
    if gateway_loaded:
        gw_latest  = int(gateway_df["Year"].max())
        gw_yr      = gateway_df[gateway_df["Year"] == gw_latest]
        gw_ap      = gw_yr[gw_yr["ORIGIN"].isin(display_airports)]

        # Aspirational comparison always uses AUS/BNA/RDU from unfiltered data
        gw_yr_asp  = gw_yr[gw_yr["ORIGIN"].isin(["AUS", "BNA", "RDU"])]

        cmh_total  = gw_yr[gw_yr["ORIGIN"] == "CMH"]["Departures"].sum()
        asp_total  = gw_yr_asp.groupby("ORIGIN")["Departures"].sum()
        asp_avg    = asp_total.mean() if not asp_total.empty else 0
        gap_pct    = (asp_avg - cmh_total) / asp_avg * 100 if asp_avg > 0 else 0

        # Weakest CMH gateways vs aspirational average (always unfiltered)
        cmh_by_gw  = gw_yr[gw_yr["ORIGIN"] == "CMH"].set_index("DEST")["Departures"]
        asp_by_gw  = gw_yr_asp.groupby("DEST")["Departures"].mean()
        common_gw  = cmh_by_gw.index.intersection(asp_by_gw.index)
        gap_by_gw  = (asp_by_gw[common_gw] - cmh_by_gw[common_gw]).sort_values(ascending=False)
        weakest_gw = gap_by_gw.index[0] if not gap_by_gw.empty else "LAX"

        # European gateway metrics (always unfiltered)
        EUR_GATEWAYS = ["JFK", "EWR", "IAD", "BOS", "ORD", "DTW"]
        cmh_eur_deps  = int(cmh_by_gw.reindex(EUR_GATEWAYS, fill_value=0).sum())
        asp_eur_deps  = int(asp_by_gw.reindex(EUR_GATEWAYS, fill_value=0).sum())
        eur_gap_pct   = (asp_eur_deps - cmh_eur_deps) / asp_eur_deps * 100 if asp_eur_deps > 0 else 0
        top_eur_gw    = cmh_by_gw.reindex(EUR_GATEWAYS, fill_value=0).idxmax()

        if gap_by_gw.empty:
            exec_summary(
                f"Columbus (CMH) operated <b>{cmh_total:,.0f} annual departures</b> to the 13 major US "
                f"international gateway airports in {gw_latest}. "
                f"Select aspirational peers in the sidebar to compare gateway connectivity."
            )
        else:
            exec_summary(
                f"Columbus (CMH) operated <b>{cmh_total:,.0f} annual departures</b> to the 13 major US "
                f"international gateway airports in {gw_latest} — <b>{gap_pct:.0f}% fewer</b> than the "
                f"aspirational peer average of {asp_avg:,.0f}. "
                f"The widest gap is <b>{GATEWAY_LABELS.get(weakest_gw, weakest_gw)}</b>, CMH's critical "
                f"underserved connection to the "
                f"{'Pacific & Asia' if weakest_gw in ['LAX','SFO','SEA'] else 'Latin America' if weakest_gw in ['MIA','IAH'] else 'transatlantic'} market."
            )

        # ── 1a. Gateway Heatmap ──────────────────────────────────
        st.markdown("### International Gateway Departure Frequency")
        st.caption(
            f"Annual nonstop departures from each peer airport to the 13 major US international gateway hubs ({gw_latest}). "
            "Darker = more departures. Columbus (CMH) row outlined."
        )

        hm_airports = [a for a in display_airports if a in gw_ap["ORIGIN"].values]
        hm_airports_sorted = sorted(
            hm_airports,
            key=lambda a: gw_ap[gw_ap["ORIGIN"]==a]["Departures"].sum(),
            reverse=True,
        )
        hm_gateways = sorted(INTL_GATEWAYS,
                             key=lambda g: gw_ap[gw_ap["DEST"]==g]["Departures"].sum(),
                             reverse=True)
        hm_z  = []
        hm_text = []
        for ap in hm_airports_sorted:
            row_z, row_t = [], []
            for gw in hm_gateways:
                val = int(gw_ap[(gw_ap["ORIGIN"]==ap) & (gw_ap["DEST"]==gw)]["Departures"].sum())
                row_z.append(val)
                row_t.append(f"{val:,}")
            hm_z.append(row_z)
            hm_text.append(row_t)

        hm_ylab = [AIRPORT_NAMES.get(a, a) for a in hm_airports_sorted]
        hm_xlab = [GATEWAY_LABELS.get(g, g) for g in hm_gateways]

        fig_hm = go.Figure(go.Heatmap(
            z=hm_z, x=hm_xlab, y=hm_ylab,
            text=hm_text, texttemplate="%{text}",
            colorscale=[[0,"#EBF5FF"],[0.3,"#0B76DA"],[1,"#002F6C"]],
            showscale=True,
            colorbar=dict(title="Annual<br>Departures", tickfont=dict(size=9)),
            hovertemplate="<b>%{y}</b> → <b>%{x}</b><br>%{text} departures<extra></extra>",
        ))
        if "Columbus (CMH)" in hm_ylab:
            cmh_hi = hm_ylab.index("Columbus (CMH)")
            fig_hm.add_shape(type="rect",
                x0=-0.5, x1=len(hm_gateways)-0.5,
                y0=cmh_hi-0.5, y1=cmh_hi+0.5,
                line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)",
            )
        fig_hm = layout(fig_hm, f"Gateway Departure Frequency by Airport — {gw_latest}",
                        height=380, legend=False)
        fig_hm.update_layout(
            xaxis=dict(side="bottom", tickangle=-30, tickfont=dict(size=10)),
            yaxis=dict(tickfont=dict(size=10)),
        )
        st.plotly_chart(fig_hm, use_container_width=True)

        hi1, hi2 = st.columns(2)
        with hi1:
            insight(
                f"<b>Pacific gateway gap:</b> Columbus (CMH) operated "
                f"<b>{cmh_by_gw.get('LAX', 0):,.0f} LAX</b> and "
                f"<b>{cmh_by_gw.get('SFO', 0):,.0f} SFO departures</b> in {gw_latest} — "
                f"vs aspirational peer averages of <b>{asp_by_gw.get('LAX', 0):,.0f}</b> and "
                f"<b>{asp_by_gw.get('SFO', 0):,.0f}</b>. "
                f"Thin Pacific gateway service limits same-day connections to Asia.",
                sentiment="risk",
            )
        with hi2:
            _eur_city = GATEWAY_LABELS.get(top_eur_gw, top_eur_gw).rsplit(" ", 1)[0]
            insight(
                f"<b>European gateway gap:</b> Columbus (CMH) operated <b>{cmh_eur_deps:,} annual departures</b> "
                f"to the six primary transatlantic departure hubs (JFK, EWR, IAD, BOS, ORD, DTW) in {gw_latest} — "
                f"<b>{eur_gap_pct:.0f}% fewer</b> than the aspirational peer average of {asp_eur_deps:,}. "
                f"Columbus (CMH)'s strongest European gateway link is <b>{_eur_city} ({top_eur_gw})</b> "
                f"with <b>{cmh_by_gw.get(top_eur_gw, 0):,} departures</b>.",
                sentiment="risk",
            )

        st.markdown("---")

        # ── 1b. Gateway Trend + CMH Gap Analysis ────────────────
        st.markdown("### Gateway Frequency Trends & CMH's Critical Gaps")
        gc1, gc2 = st.columns([3, 2])

        with gc1:
            st.caption("Total annual departures to all 13 international gateway airports.")
            trend_rows = []
            for yr in sorted(gateway_df["Year"].unique()):
                yr_sub = gateway_df[(gateway_df["Year"]==yr) & (gateway_df["ORIGIN"].isin(display_airports))]
                for ap in display_airports:
                    total_deps = yr_sub[yr_sub["ORIGIN"]==ap]["Departures"].sum()
                    trend_rows.append({"Year": yr, "Airport": ap, "Departures": total_deps})
            trend_df = pd.DataFrame(trend_rows)

            fig_trend = go.Figure()
            for ap in display_airports:
                ap_t = trend_df[trend_df["Airport"]==ap].sort_values("Year")
                if ap_t["Departures"].sum() == 0:
                    continue
                is_cmh = ap == "CMH"
                fig_trend.add_trace(go.Scatter(
                    x=ap_t["Year"], y=ap_t["Departures"],
                    mode="lines+markers",
                    name=AIRPORT_NAMES.get(ap, ap),
                    line=dict(color=color_map.get(ap, "#aaa"), width=3 if is_cmh else 1.8),
                    marker=dict(size=8 if is_cmh else 5),
                ))
            fig_trend = layout(fig_trend, "Total Gateway Departures by Airport (2019–2025)", height=360)
            fig_trend.update_layout(
                xaxis=dict(tickmode="linear", dtick=1, tickformat="d"),
                yaxis_title="Annual Departures to Gateways",
                hovermode="x unified",
            )
            covid_band(fig_trend)
            st.plotly_chart(fig_trend, use_container_width=True)

        with gc2:
            st.caption(f"Columbus (CMH) vs aspirational peer average — biggest departure gaps ({gw_latest}).")
            top_gaps = gap_by_gw.head(6).reset_index()
            top_gaps.columns = ["Gateway", "Gap"]
            top_gaps["Label"] = top_gaps["Gateway"].map(GATEWAY_LABELS).fillna(top_gaps["Gateway"])
            top_gaps["CMH"] = top_gaps["Gateway"].map(lambda g: int(cmh_by_gw.get(g, 0)))
            top_gaps["Peer Avg"] = top_gaps["Gateway"].map(lambda g: int(asp_by_gw.get(g, 0)))
            top_gaps = top_gaps.sort_values("Gap")

            fig_gap = go.Figure()
            fig_gap.add_trace(go.Bar(
                x=top_gaps["Peer Avg"], y=top_gaps["Label"],
                name="Aspirational Avg", orientation="h",
                marker_color=LIGHT_BLUE,
            ))
            fig_gap.add_trace(go.Bar(
                x=top_gaps["CMH"], y=top_gaps["Label"],
                name="Columbus (CMH)", orientation="h",
                marker_color=NAVY,
            ))
            fig_gap = layout(fig_gap, f"CMH Gateway Gaps vs Aspirational Peers ({gw_latest})", height=380)
            fig_gap.update_layout(
                barmode="overlay",
                xaxis_title="Annual Departures",
                yaxis_title="",
                legend=dict(orientation="v", x=1.02, y=1, xanchor="left", yanchor="top", font=dict(size=10)),
                margin=dict(r=130),
            )
            st.plotly_chart(fig_gap, use_container_width=True)

        insight(
            f"Since 2019, Columbus (CMH) has grown gateway departures from "
            f"<b>{int(trend_df[(trend_df['Airport']=='CMH')&(trend_df['Year']==2019)]['Departures'].sum()):,}</b> "
            f"to <b>{int(cmh_total):,}</b> in {gw_latest} — but aspirational peers have grown faster, "
            f"widening the gap. Closing it requires targeted frequency additions on LAX, SFO, and MIA.",
            sentiment="neutral",
        )

    st.markdown("---")

    # ── Section 2: DB1B Gateway O&D Connectivity ────────────────
    if db1b_loaded:
        EUR_GW = ["JFK", "EWR", "IAD", "BOS", "ORD", "DTW"]
        PAC_GW = ["LAX", "SFO", "SEA"]
        LAT_GW = ["MIA", "IAH", "DFW", "ATL"]

        db1b_latest_yr = int(db1b_df["Year"].max())
        db1b_yr = db1b_df[db1b_df["Year"] == db1b_latest_yr]

        st.markdown("### Latent International Demand — CMH Passengers Connecting via Gateways")
        st.caption(
            f"Actual O&D passengers from Columbus (CMH) connecting through each major international gateway in {db1b_latest_yr} "
            "(DB1B 10% ticket sample, annualized). These passengers are already traveling internationally — through a hub connection."
        )

        db1c, db1d = st.columns(2)
        with db1c:
            # Gateway breakdown bar chart for CMH
            cmh_db1b = (db1b_yr[db1b_yr["Airport"]=="CMH"]
                        .set_index("Gateway")["Passengers"]
                        .reindex(INTL_GATEWAYS, fill_value=0)
                        .reset_index())
            cmh_db1b.columns = ["Gateway", "Passengers"]
            cmh_db1b["Label"] = cmh_db1b["Gateway"].map(GATEWAY_LABELS).fillna(cmh_db1b["Gateway"])
            cmh_db1b["Region"] = cmh_db1b["Gateway"].map(
                lambda g: "Europe" if g in EUR_GW else "Pacific/Asia" if g in PAC_GW else "Latin America/Global"
            )
            region_colors = {"Europe": MED_BLUE, "Pacific/Asia": TEAL, "Latin America/Global": "#A053AC"}
            cmh_db1b["Color"] = cmh_db1b["Region"].map(region_colors)
            cmh_db1b = cmh_db1b.sort_values("Passengers", ascending=True)

            fig_od = go.Figure(go.Bar(
                x=cmh_db1b["Passengers"],
                y=cmh_db1b["Label"],
                orientation="h",
                marker_color=cmh_db1b["Color"].tolist(),
                text=cmh_db1b["Passengers"].apply(lambda v: f"{v:,.0f}"),
                textposition="outside", textfont=dict(size=10),
                customdata=cmh_db1b["Region"],
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} CMH passengers<br>%{customdata}<extra></extra>",
            ))
            fig_od = layout(fig_od, f"CMH Connecting Passengers by International Gateway ({db1b_latest_yr})",
                            height=400, legend=False)
            fig_od.update_layout(xaxis_title="Connecting Passengers (DB1B sample)",
                                 yaxis_title="")
            st.plotly_chart(fig_od, use_container_width=True)

        with db1d:
            # Region summary: Europe vs Pacific vs LatAm
            eur_pax = int(cmh_db1b[cmh_db1b["Gateway"].isin(EUR_GW)]["Passengers"].sum())
            pac_pax = int(cmh_db1b[cmh_db1b["Gateway"].isin(PAC_GW)]["Passengers"].sum())
            lat_pax = int(cmh_db1b[cmh_db1b["Gateway"].isin(LAT_GW)]["Passengers"].sum())
            total_intl_pax = eur_pax + pac_pax + lat_pax
            st.markdown(f"#### International Demand Breakdown ({db1b_latest_yr})")

            for region, pax, color in [
                ("Europe", eur_pax, MED_BLUE),
                ("Pacific & Asia", pac_pax, TEAL),
                ("Latin America & Global Hubs", lat_pax, "#A053AC"),
            ]:
                pct = pax / total_intl_pax * 100 if total_intl_pax > 0 else 0
                st.markdown(
                    f"<div style='padding:10px 14px; border-left:4px solid {color}; "
                    f"background:#F8F9FA; border-radius:0 8px 8px 0; margin:8px 0;'>"
                    f"<span style='font-weight:700; color:{color}; font-size:14px;'>{region}</span><br>"
                    f"<span style='font-size:22px; font-weight:700; color:{TEXT_COLOR};'>{pax:,}</span> "
                    f"<span style='font-size:12px; color:#6b7280;'>connecting pax ({pct:.0f}% of tracked total)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("<br>", unsafe_allow_html=True)
            insight(
                f"<b>{eur_pax:,} Columbus passengers</b> connected through European gateway hubs in {db1b_latest_yr} — "
                f"the largest international demand segment at <b>{eur_pax/(eur_pax+pac_pax+lat_pax)*100:.0f}%</b> of tracked international connecting traffic. "
                f"This latent European demand validates the case for direct or improved transatlantic gateway service from Columbus (CMH).",
                sentiment="positive",
            )

        st.markdown("---")

    # ── Section 3: Foreign-Born Population ──────────────────────
    st.markdown("### Columbus MSA Foreign-Born Population — International Demand Signal")
    st.caption("Foreign residents drive VFR (Visiting Friends & Relatives) travel. Each region below represents latent demand for direct international routes.")
    fb_df = fetch_foreign_born_regions()
    if not fb_df.empty:
        fig_fb = go.Figure(go.Bar(
            x=fb_df["Foreign-Born"],
            y=fb_df["Region"],
            orientation="h",
            marker_color=[TEAL if i == len(fb_df)-1 else MED_BLUE for i in range(len(fb_df))],
            text=fb_df["Foreign-Born"].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig_fb = layout(fig_fb, "Columbus MSA Foreign-Born Population by World Region (ACS 2023)", height=400, legend=False)
        fig_fb.update_layout(xaxis_title="Foreign-Born Residents", yaxis_title="",
                             xaxis=dict(range=[0, fb_df["Foreign-Born"].max() * 1.2]))
        st.plotly_chart(fig_fb, use_container_width=True)
        top_region = fb_df.iloc[-1]
        total_fb   = fb_df["Foreign-Born"].sum()
        insight(
            f"The Columbus metro has <b>{total_fb:,.0f} foreign-born residents</b> across tracked world regions. "
            f"<b>{top_region['Region']}</b> is the largest group at <b>{top_region['Foreign-Born']:,.0f} residents</b> — "
            f"a direct indicator of VFR demand for routes to that region that Columbus (CMH) is not yet serving.",
            sentiment="positive",
        )
    else:
        st.caption("Foreign-born data unavailable (Census API timeout). Re-load the page to retry.")

    st.markdown("---")

    # ── Section 4a: CMH Current International Status ─────────────────────────
    # Sources: CMH Monthly Statistics Report Dec 2025; flycolumbus.com press releases
    st.markdown("### Current & Upcoming International Service at CMH")
    st.caption(
        "Sources: CMH Monthly Statistics Report (Dec 2025, flycolumbus.com); "
        "Air Canada route announcements; flycolumbus.com press releases"
    )

    # ── Route cards ──────────────────────────────────────────────────────────
    _card_css = (
        "border-radius:8px; padding:14px 16px; height:100%; "
        "font-family:sans-serif; line-height:1.5;"
    )
    _rc1, _rc2, _rc3 = st.columns(3)
    with _rc1:
        st.markdown(
            f"<div style='{_card_css} border:2px solid {TEAL}; background:#f0fafa;'>"
            f"<div style='font-size:11px; font-weight:700; color:{TEAL}; text-transform:uppercase; letter-spacing:.05em;'>Cancun, Mexico — CUN</div>"
            f"<div style='font-size:18px; font-weight:700; color:{NAVY}; margin:4px 0;'>Spring Seasonal</div>"
            f"<div style='font-size:12px; color:#374151;'>"
            f"<b>Southwest Airlines</b> · Seasonal (Mar–May)<br>"
            f"<b>American Airlines</b> · Seasonal (Dec–Apr)<br>"
            f"<b>Vacation Express / Viva Aerobus</b> · Charter (spring break)<br>"
            f"<b>Frontier Airlines</b> · Seasonal"
            f"</div>"
            f"<div style='margin-top:8px; font-size:11px; color:#6b7280;'>Multiple carriers; charter &amp; scheduled</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _rc2:
        st.markdown(
            f"<div style='{_card_css} border:2px solid {NAVY}; background:#f0f4ff;'>"
            f"<div style='font-size:11px; font-weight:700; color:{NAVY}; text-transform:uppercase; letter-spacing:.05em;'>Toronto, Canada — YYZ</div>"
            f"<div style='font-size:18px; font-weight:700; color:{NAVY}; margin:4px 0;'>Summer Seasonal</div>"
            f"<div style='font-size:12px; color:#374151;'>"
            f"<b>Air Canada</b> · Daily nonstop<br>"
            f"Active: May–December<br>"
            f"20+ year route from CMH<br>"
            f"2025: <b>44,994 total passengers</b>"
            f"</div>"
            f"<div style='margin-top:8px; font-size:11px; color:#6b7280;'>Air Canada's YYZ hub connects to global network</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _rc3:
        st.markdown(
            f"<div style='{_card_css} border:2px solid #d97706; background:#fffbeb;'>"
            f"<div style='display:flex; align-items:center; gap:8px;'>"
            f"<span style='font-size:11px; font-weight:700; color:#d97706; text-transform:uppercase; letter-spacing:.05em;'>Montreal, Canada — YUL</span>"
            f"<span style='background:#d97706; color:white; font-size:9px; font-weight:700; padding:2px 6px; border-radius:4px; letter-spacing:.05em;'>NEW</span>"
            f"</div>"
            f"<div style='font-size:18px; font-weight:700; color:{NAVY}; margin:4px 0;'>Launching May 1, 2026</div>"
            f"<div style='font-size:12px; color:#374151;'>"
            f"<b>Air Canada</b> · Daily nonstop<br>"
            f"Flight time: 1h 45m<br>"
            f"First-ever CMH–Montréal nonstop<br>"
            f"YUL is a <b>US preclearance</b> airport"
            f"</div>"
            f"<div style='margin-top:8px; font-size:11px; color:#6b7280;'>Connects CMH to Air Canada's European network via YUL</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Hard-coded from CMH Monthly Stats PDF (Dec 2025 report) — Air Canada CMH-YYZ
    # Jun/Jul/Aug/Nov/Dec are exact from PDF; May/Sep/Oct estimated to match 44,994 total
    _AC_MONTHLY = {
        "Jan": 0, "Feb": 0, "Mar": 0, "Apr": 0,
        "May": 5_800, "Jun": 8_969, "Jul": 7_674,
        "Aug": 6_132, "Sep": 6_500, "Oct": 6_451,
        "Nov": 1_747, "Dec": 1_721,
    }
    _AC_TOTAL    = 44_994
    _AC_ENPLANED = 21_354

    # Peer direct international scheduled route counts (approximate, summer 2025/26)
    # CMH: 2 scheduled (YYZ + CUN via WN/AA) + YUL launching May 2026
    _PEER_INTL_ROUTES = {
        "CMH": 2, "IND": 1, "CVG": 2, "CLE": 3,
        "PIT": 3, "DAY": 0, "AUS": 12, "BNA": 5, "RDU": 5,
    }
    _PEER_INTL_2026 = {
        "CMH": 3,  # +YUL May 2026
    }

    col_ac1, col_ac2 = st.columns([3, 2])
    with col_ac1:
        _months = list(_AC_MONTHLY.keys())
        _pax    = list(_AC_MONTHLY.values())
        _colors = [TEAL if p > 0 else "#e5e7eb" for p in _pax]
        _labels = [f"{p:,}" if p > 3_000 else "" for p in _pax]
        fig_ac = go.Figure(go.Bar(
            x=_months, y=_pax,
            marker_color=_colors,
            text=_labels,
            textposition="outside",
            textfont=dict(size=9),
        ))
        fig_ac = layout(fig_ac,
            "Air Canada CMH ↔ Toronto (YYZ) — 2025 Monthly Passengers (Both Directions)",
            height=310, legend=False)
        fig_ac.update_layout(
            xaxis_title="",
            yaxis_title="Passengers",
            yaxis=dict(range=[0, 11_000]),
        )
        fig_ac.add_annotation(
            text="† May, Sep, Oct estimated to match 44,994 annual total · Source: CMH Monthly Stats Report Dec 2025",
            xref="paper", yref="paper", x=1, y=-0.2,
            showarrow=False, font=dict(size=9, color="#9ca3af"),
            xanchor="right",
        )
        st.plotly_chart(fig_ac, use_container_width=True)

    with col_ac2:
        _pi_rows = [
            {"Code": k, "Label": AIRPORT_NAMES.get(k, k),
             "Routes": v, "Routes2026": _PEER_INTL_2026.get(k, v)}
            for k, v in _PEER_INTL_ROUTES.items()
            if k in display_airports
        ]
        _pi_df = (pd.DataFrame(_pi_rows)
                  .sort_values("Routes2026", ascending=True)
                  .reset_index(drop=True))
        fig_pi = go.Figure()
        # 2025 bars
        fig_pi.add_trace(go.Bar(
            name="2025",
            x=_pi_df["Routes"],
            y=_pi_df["Label"],
            orientation="h",
            marker_color=[TEAL if c == "CMH" else NAVY for c in _pi_df["Code"]],
            opacity=0.85,
        ))
        # 2026 increment for CMH
        _cmh_pi_mask = _pi_df["Code"] == "CMH"
        if _cmh_pi_mask.any():
            _pi_df_cmh = _pi_df[_cmh_pi_mask].copy()
            _incr = _pi_df_cmh["Routes2026"] - _pi_df_cmh["Routes"]
            fig_pi.add_trace(go.Bar(
                name="+YUL May 2026",
                x=_incr.values,
                y=_pi_df_cmh["Label"].values,
                orientation="h",
                marker_color="#d97706",
                opacity=0.9,
                text=[f"+{int(v)}" for v in _incr.values],
                textposition="outside",
                textfont=dict(size=9, color="#d97706"),
            ))
        if "CMH" in _pi_df["Code"].values:
            _cmh_pi_i = _pi_df["Code"].tolist().index("CMH")
            _cmh_pi_v = _pi_df.iloc[_cmh_pi_i]["Routes2026"]
            fig_pi.add_shape(
                type="rect",
                x0=-0.15, x1=_cmh_pi_v + 0.5,
                y0=_cmh_pi_i - 0.48, y1=_cmh_pi_i + 0.48,
                line=dict(color=TEAL, width=2.5),
                fillcolor="rgba(0,0,0,0)",
            )
        fig_pi = layout(fig_pi, "Direct International Routes — 2025 vs. 2026 (Approx.)", height=310, legend=True)
        fig_pi.update_layout(
            barmode="stack",
            xaxis_title="Scheduled Routes",
            yaxis_title="",
            xaxis=dict(range=[0, 16]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
        )
        fig_pi.add_annotation(
            text="† Approx.; excludes charter-only · AUS/BNA/RDU include Mexico &amp; Caribbean",
            xref="paper", yref="paper", x=1, y=-0.2,
            showarrow=False, font=dict(size=9, color="#9ca3af"),
            xanchor="right",
        )
        st.plotly_chart(fig_pi, use_container_width=True)

    _asp_routes = max(
        _PEER_INTL_ROUTES.get(a, 0)
        for a in ["AUS", "BNA", "RDU"]
        if a in display_airports
    ) if any(a in display_airports for a in ["AUS", "BNA", "RDU"]) else 12
    _asp_names  = [AIRPORT_NAMES.get(a, a) for a in ["AUS", "BNA", "RDU"] if a in display_airports]
    _asp_str    = " and ".join(_asp_names) if _asp_names else "aspirational peers"
    insight(
        f"CMH currently operates <b>2 international scheduled routes</b> — "
        f"Air Canada to Toronto (YYZ, seasonal May–Dec; 20+ year route) and "
        f"seasonal Cancun (CUN) via Southwest, American, and charter operators. "
        f"Air Canada's Toronto service carried <b>{_AC_TOTAL:,} total passengers</b> "
        f"({_AC_ENPLANED:,} enplaned) in 2025, with a strong summer peak. "
        f"With Air Canada's <b>first-ever CMH–Montréal (YUL) daily nonstop launching May 1, 2026</b> — "
        f"a US preclearance hub with European connections — CMH will reach <b>3 international routes</b> this summer. "
        f"{_asp_str} {'serve' if len(_asp_names) > 1 else 'serves'} "
        f"<b>{_asp_routes}+ international routes</b>, so meaningful expansion remains ahead.",
        sentiment="neutral",
    )

    st.markdown("---")

    # ── Section 4: Direct International Service (T-100 Intl) ────
    st.markdown("### Direct International Service — Historical (T-100)")
    if intl_loaded:
        intl_latest_yr = int(intl_df["YEAR"].max())
        intl_dep = intl_df[intl_df["ORIGIN"].isin(display_airports)].copy()
        intl_yr  = intl_dep[intl_dep["YEAR"] == intl_latest_yr]
        cmh_intl = intl_yr[intl_yr["ORIGIN"] == "CMH"]["PASSENGERS"].sum()
        n_peers_with_intl = intl_yr[intl_yr["ORIGIN"] != "CMH"]["ORIGIN"].nunique()

        col_i1, col_i2 = st.columns(2)
        with col_i1:
            pax_by_ap = (intl_yr.groupby("ORIGIN")["PASSENGERS"].sum()
                         .reindex(display_airports, fill_value=0)
                         .reset_index())
            pax_by_ap.columns = ["Code", "Passengers"]
            pax_by_ap["Label"] = pax_by_ap["Code"].map(AIRPORT_NAMES).fillna(pax_by_ap["Code"])
            pax_by_ap["Color"] = pax_by_ap["Code"].map(color_map)
            pax_by_ap = pax_by_ap.sort_values("Passengers", ascending=True)
            fig_ipax = go.Figure(go.Bar(
                x=pax_by_ap["Passengers"] / 1e3,
                y=pax_by_ap["Label"],
                orientation="h",
                marker_color=pax_by_ap["Color"].tolist(),
                text=(pax_by_ap["Passengers"] / 1e3).round(0).astype(int).astype(str) + "K",
                textposition="outside", textfont=dict(size=10),
            ))
            if "CMH" in pax_by_ap["Code"].values:
                cmh_i = pax_by_ap["Code"].tolist().index("CMH")
                cmh_v = pax_by_ap.iloc[cmh_i]["Passengers"] / 1e3
                fig_ipax.add_shape(type="rect",
                    x0=-0.5, x1=max(cmh_v, 1),
                    y0=cmh_i - 0.48, y1=cmh_i + 0.48,
                    line=dict(color=TEAL, width=2.5), fillcolor="rgba(0,0,0,0)")
            fig_ipax = layout(fig_ipax, f"International Passengers Departing — {intl_latest_yr}", height=360, legend=False)
            fig_ipax.update_layout(xaxis_title="Passengers (thousands)", yaxis_title="")
            st.plotly_chart(fig_ipax, use_container_width=True)
            cmh_intl_str = f"{cmh_intl:,.0f} passengers" if cmh_intl > 0 else "no scheduled international service"
            top_intl_ap  = pax_by_ap.sort_values("Passengers", ascending=False).iloc[0]
            insight(
                f"<b>{top_intl_ap['Label']}</b> leads the peer group with "
                f"<b>{top_intl_ap['Passengers']/1e3:.0f}K international passengers</b> in {intl_latest_yr}. "
                f"Columbus (CMH) carried {cmh_intl_str}.",
                sentiment="positive" if cmh_intl > 0 else "risk",
            )

        with col_i2:
            st.markdown("#### International Destinations Over Time")
            dest_trend_rows = []
            for ap in display_airports:
                for yr in sorted(intl_dep["YEAR"].unique()):
                    n = intl_dep[(intl_dep["ORIGIN"]==ap)&(intl_dep["YEAR"]==yr)]["DEST_COUNTRY_NAME"].nunique()
                    dest_trend_rows.append({"Airport": AIRPORT_NAMES.get(ap, ap), "Code": ap, "Year": int(yr), "Countries": n})
            if dest_trend_rows:
                dt_df = pd.DataFrame(dest_trend_rows)
                fig_idt = go.Figure()
                for ap in display_airports:
                    ap_dt = dt_df[dt_df["Code"]==ap].sort_values("Year")
                    if ap_dt.empty or ap_dt["Countries"].sum() == 0:
                        continue
                    is_cmh = ap == "CMH"
                    fig_idt.add_trace(go.Scatter(
                        x=ap_dt["Year"], y=ap_dt["Countries"],
                        mode="lines+markers", name=AIRPORT_NAMES.get(ap, ap),
                        line=dict(color=color_map.get(ap, "#aaa"), width=3 if is_cmh else 1.8),
                        marker=dict(size=8 if is_cmh else 6),
                    ))
                fig_idt = layout(fig_idt, "Unique International Countries Served", height=360)
                fig_idt.update_layout(xaxis_title="Year", yaxis_title="Countries",
                                      xaxis=dict(tickmode="linear", dtick=1, tickformat="d"),
                                      hovermode="x unified")
                covid_band(fig_idt)
                st.plotly_chart(fig_idt, use_container_width=True)

        st.markdown("---")

        cmh_countries = set(intl_yr[intl_yr["ORIGIN"]=="CMH"]["DEST_COUNTRY_NAME"].dropna().unique())
        peer_codes    = [a for a in display_airports if a != "CMH"]
        gap_rows = []
        for country in intl_yr["DEST_COUNTRY_NAME"].dropna().unique():
            if country in cmh_countries:
                continue
            serving   = [a for a in peer_codes
                         if intl_yr[(intl_yr["ORIGIN"]==a)&(intl_yr["DEST_COUNTRY_NAME"]==country)]["PASSENGERS"].sum() > 0]
            total_pax = intl_yr[intl_yr["ORIGIN"].isin(peer_codes) &
                                (intl_yr["DEST_COUNTRY_NAME"]==country)]["PASSENGERS"].sum()
            if len(serving) >= 2:
                gap_rows.append({"Country": country, "Peers Serving": len(serving),
                                 "Peer Airports": ", ".join(serving), "Total Peer Pax": int(total_pax)})
        if gap_rows:
            gap_df = (pd.DataFrame(gap_rows)
                      .sort_values(["Peers Serving","Total Peer Pax"], ascending=False)
                      .head(15).reset_index(drop=True))
            gap_df["Peer Labels"] = gap_df["Peer Airports"].apply(
                lambda s: ", ".join(AIRPORT_NAMES.get(c.strip(), c.strip()) for c in s.split(","))
            )
            ig1, ig2 = st.columns([2, 1])
            with ig1:
                fig_igap = go.Figure(go.Bar(
                    x=gap_df["Total Peer Pax"] / 1e3,
                    y=gap_df["Country"],
                    orientation="h",
                    marker=dict(color=gap_df["Peers Serving"],
                                colorscale=[[0, LIGHT_BLUE],[0.5, MED_BLUE],[1, NAVY]],
                                showscale=True,
                                colorbar=dict(title="# Peers<br>Serving", tickfont=dict(size=9))),
                    text=(gap_df["Total Peer Pax"]/1e3).round(0).astype(int).astype(str)+"K",
                    textposition="outside",
                    customdata=gap_df[["Peers Serving","Peer Labels"]].values,
                    hovertemplate="<b>%{y}</b><br>Peer passengers: %{x:.0f}K<br>%{customdata[0]} peers: %{customdata[1]}<extra></extra>",
                ))
                fig_igap = layout(fig_igap, f"Unserved International Markets — Peer Volume ({intl_latest_yr})", height=460, legend=False)
                fig_igap.update_layout(xaxis_title="Combined Peer Passengers (thousands)",
                                       yaxis_title="", yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_igap, use_container_width=True)
            with ig2:
                st.markdown(f"**Top Gaps ({intl_latest_yr})**")
                for _, row in gap_df.head(8).iterrows():
                    st.markdown(
                        f"<div style='padding:7px 0; border-bottom:1px solid #f0f2f5;'>"
                        f"<span style='font-weight:600; color:{NAVY}; font-size:13px;'>{row['Country']}</span><br>"
                        f"<span style='font-size:11px; color:#6b7280;'>{row['Peers Serving']} peers · {row['Total Peer Pax']:,.0f} pax</span><br>"
                        f"<span style='font-size:10px; color:{TEAL};'>{row['Peer Labels']}</span>"
                        f"</div>",
                        unsafe_allow_html=True)
            top_gap = gap_df.iloc[0]
            insight(
                f"<b>{top_gap['Country']}</b> is the strongest international gap — "
                f"<b>{int(top_gap['Peers Serving'])} peer airports</b> serve it carrying "
                f"<b>{top_gap['Total Peer Pax']:,.0f} passengers</b> in {intl_latest_yr}, "
                f"with zero direct service from Columbus (CMH).",
                sentiment="positive",
            )
            st.download_button(
                label="⬇  Download International Gap Analysis CSV",
                data=gap_df.drop(columns=["Peer Labels"]).to_csv(index=False),
                file_name=f"cmh_international_gaps_{intl_latest_yr}.csv",
                mime="text/csv",
            )
    else:
        st.info(
            "**Direct international service data not yet loaded.**  \n"
            "Once the BTS TranStats site is responsive, run `python fetch_international.py` "
            "for download instructions. This section will populate automatically once data "
            "is placed in `data/bts/intl_raw/`.",
            icon="ℹ️",
        )

    if not gateway_loaded:
        st.info("Gateway connectivity data not available — ensure T-100 Segment files are present in `data/bts/`.")


# ══════════════════════════════════════════════════════════════
# TAB 7 · INTERNAL TAB 1  (rename + populate at work)
# ══════════════════════════════════════════════════════════════
with tab_internal_1:
    # ── Data loader — reads from data/internal/ which is gitignored ──
    def load_internal_tab1():
        path = os.path.join("data", "internal", "tab1_data.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)

    _int1_df = load_internal_tab1()
    if _int1_df.empty:
        exec_summary(
            "This tab will be populated with internal company data at work. "
            "Place your data file at <code>data/internal/tab1_data.csv</code> "
            "and update this section."
        )
        st.info(
            "**Internal data not found.**  \n"
            "Add your data file to `data/internal/` (gitignored) and build out this section "
            "following the same chart patterns used in the other tabs.",
            icon="🔒",
        )
    else:
        # ── Replace this block with your tab content ──────────────────
        exec_summary("Internal Tab 1 — update this summary once data is loaded.")
        st.markdown("### Tab 7 Heading")
        st.dataframe(_int1_df.head(20))


# ══════════════════════════════════════════════════════════════
# TAB 8 · INTERNAL TAB 2  (rename + populate at work)
# ══════════════════════════════════════════════════════════════
with tab_internal_2:
    def load_internal_tab2():
        path = os.path.join("data", "internal", "tab2_data.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)

    _int2_df = load_internal_tab2()
    if _int2_df.empty:
        exec_summary(
            "This tab will be populated with internal company data at work. "
            "Place your data file at <code>data/internal/tab2_data.csv</code> "
            "and update this section."
        )
        st.info(
            "**Internal data not found.**  \n"
            "Add your data file to `data/internal/` (gitignored) and build out this section "
            "following the same chart patterns used in the other tabs.",
            icon="🔒",
        )
    else:
        exec_summary("Internal Tab 2 — update this summary once data is loaded.")
        st.markdown("### Tab 8 Heading")
        st.dataframe(_int2_df.head(20))


# ============================================================
# Footer
# ============================================================
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#aaa;font-size:0.75em;font-family:Open Sans,sans-serif;'>"
    "Data: BTS T-100 Domestic Market & Segment · BTS On-Time Performance · "
    "U.S. Census Bureau ACS 1-Year · FRED — Federal Reserve Bank of St. Louis"
    "</div>", unsafe_allow_html=True,
)
