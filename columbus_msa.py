import os
import requests
import pandas as pd

# =========================
# User settings
# =========================
OUTDIR = "output"
os.makedirs(OUTDIR, exist_ok=True)

# Columbus, OH MSA code used by Census API and BLS/FRED metro series
MSA_CODE = "18140"
MSA_NAME = "Columbus, OH MSA"

# ACS years to pull
ACS_YEARS = [2022, 2023, 2024, 2025]

# For ACS:
# - 1-year ACS is available for 2022-2024 in most metro contexts; 2025 may not yet be available depending on release timing.
# - We will try each year and keep whichever returns successfully.
ACS_DATASET = "acs/acs1"

# Optional API keys
CENSUS_KEY = os.getenv("CENSUS_API_KEY", "").strip()

# =========================
# Helpers
# =========================
def census_get(year, group_or_vars, geo_for, dataset=ACS_DATASET, geo_in=None, is_group=False):
    base = f"https://api.census.gov/data/{year}/{dataset}"
    if is_group:
        url = f"{base}/groups/{group_or_vars}.json"
        params = {"get": f"group({group_or_vars})", "for": geo_for}
    else:
        url = base
        params = {"get": group_or_vars, "for": geo_for}

    if geo_in:
        params["in"] = geo_in
    if CENSUS_KEY:
        params["key"] = CENSUS_KEY

    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data[1:], columns=data[0])

def safe_to_numeric(s):
    return pd.to_numeric(s, errors="coerce")

def first_working_acs_years(years, group, geo_for, is_group=True):
    frames = []
    for y in years:
        try:
            df = census_get(y, group, geo_for, is_group=is_group)
            df["year"] = y
            frames.append(df)
        except Exception as e:
            print(f"Skipping ACS {group} {y}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def fetch_csv(url):
    return pd.read_csv(url)

# =========================
# Geography selector
# =========================
# Census API geography for metro areas:
#   for=metropolitan statistical area/micropolitan statistical area:18140
GEO_FOR = f"metropolitan statistical area/micropolitan statistical area:{MSA_CODE}"

# =========================
# ACS pulls
# =========================

# 1) B01003 Total population
pop_frames = []
for y in ACS_YEARS:
    try:
        df = census_get(y, "B01003_001E", GEO_FOR, is_group=False)
        df["year"] = y
        pop_frames.append(df)
    except Exception as e:
        print(f"B01003 {y} skipped: {e}")
pop = pd.concat(pop_frames, ignore_index=True) if pop_frames else pd.DataFrame()
if not pop.empty:
    pop = pop.rename(columns={"B01003_001E": "total_population"})
    pop["total_population"] = safe_to_numeric(pop["total_population"])

# 2) B19013 Median household income
mhi_frames = []
for y in ACS_YEARS:
    try:
        df = census_get(y, "B19013_001E", GEO_FOR, is_group=False)
        df["year"] = y
        mhi_frames.append(df)
    except Exception as e:
        print(f"B19013 {y} skipped: {e}")
mhi = pd.concat(mhi_frames, ignore_index=True) if mhi_frames else pd.DataFrame()
if not mhi.empty:
    mhi = mhi.rename(columns={"B19013_001E": "median_household_income"})
    mhi["median_household_income"] = safe_to_numeric(mhi["median_household_income"])

# 3) B19301 Per capita income
pci_frames = []
for y in ACS_YEARS:
    try:
        df = census_get(y, "B19301_001E", GEO_FOR, is_group=False)
        df["year"] = y
        pci_frames.append(df)
    except Exception as e:
        print(f"B19301 {y} skipped: {e}")
pci = pd.concat(pci_frames, ignore_index=True) if pci_frames else pd.DataFrame()
if not pci.empty:
    pci = pci.rename(columns={"B19301_001E": "per_capita_income"})
    pci["per_capita_income"] = safe_to_numeric(pci["per_capita_income"])

# 4) B19001 Household income distribution
# We pull the whole group so we can aggregate to your custom brackets.
b19001_frames = []
for y in ACS_YEARS:
    try:
        df = census_get(y, "B19001", GEO_FOR, is_group=True)
        df["year"] = y
        b19001_frames.append(df)
    except Exception as e:
        print(f"B19001 {y} skipped: {e}")
b19001 = pd.concat(b19001_frames, ignore_index=True) if b19001_frames else pd.DataFrame()

# 5) B01001 Sex by age
b01001_frames = []
for y in ACS_YEARS:
    try:
        df = census_get(y, "B01001", GEO_FOR, is_group=True)
        df["year"] = y
        b01001_frames.append(df)
    except Exception as e:
        print(f"B01001 {y} skipped: {e}")
b01001 = pd.concat(b01001_frames, ignore_index=True) if b01001_frames else pd.DataFrame()

# =========================
# BLS / FRED unemployment rate
# =========================
# Annual LAUS series for Columbus MSA:
# FRED series: LAUMT391814000000003A
# This is the annual average unemployment rate for the Columbus, OH MSA.
fred_unemp_url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=LAUMT391814000000003A"
unemp = fetch_csv(fred_unemp_url)
unemp = unemp.rename(columns={"DATE": "date", "LAUMT391814000000003A": "unemployment_rate"})
unemp["date"] = pd.to_datetime(unemp["date"], errors="coerce")
unemp["year"] = unemp["date"].dt.year
unemp["unemployment_rate"] = pd.to_numeric(unemp["unemployment_rate"], errors="coerce")
unemp = unemp[unemp["year"].isin(ACS_YEARS)].copy()

# If you want the annual average by year, FRED annual series is already annual.
unemp_yearly = unemp[["year", "unemployment_rate"]].dropna().drop_duplicates().sort_values("year")

# =========================
# Transform B19001 into requested brackets
# =========================
# B19001 variables are counts of households by income bracket.
# We create bracket buckets:
# Under 25K, 25K-49K, 50K-74K, 75K-99K, 100K-149K, 150K+
#
# ACS B19001 bins:
# 001 total
# 002 <10k
# 003 10-15k
# 004 15-20k
# 005 20-25k
# 006 25-30k
# 007 30-35k
# 008 35-40k
# 009 40-45k
# 010 45-50k
# 011 50-60k
# 012 60-75k
# 013 75-100k
# 014 100-125k
# 015 125-150k
# 016 150-200k
# 017 200k+

def agg_income_distribution(df_year):
    d = df_year.copy()
    for col in d.columns:
        if col.endswith("E") and col != "year":
            d[col] = pd.to_numeric(d[col], errors="coerce")

    total = d["B19001_001E"].iloc[0]

    buckets = {
        "Under $25K": ["B19001_002E", "B19001_003E", "B19001_004E", "B19001_005E"],
        "$25K–$49K": ["B19001_006E", "B19001_007E", "B19001_008E", "B19001_009E", "B19001_010E"],
        "$50K–$74K": ["B19001_011E", "B19001_012E"],
        "$75K–$99K": ["B19001_013E"],
        "$100K–$149K": ["B19001_014E", "B19001_015E"],
        "$150K+": ["B19001_016E", "B19001_017E"],
    }

    rows = []
    for label, cols in buckets.items():
        val = d[cols].iloc[0].sum()
        rows.append({
            "year": int(d["year"].iloc[0]),
            "income_bracket": label,
            "households": float(val),
            "pct_households": float(val) / float(total) * 100 if pd.notna(total) and total != 0 else None
        })
    return pd.DataFrame(rows)

income_dist = pd.concat([agg_income_distribution(b19001[b19001["year"] == y]) for y in b19001["year"].dropna().unique()], ignore_index=True) if not b19001.empty else pd.DataFrame()

# =========================
# Transform B01001 into requested age bands
# =========================
# Age bands requested:
# Gen Alpha (0–14), Gen Z (15–28), Millennials (29–44), Gen X (45–60), Baby Boomers (61–79), Silent+ (80+)
#
# B01001 age bins (male/female) must be summed. We map ages as:
# 0-4, 5-9, 10-14 -> Gen Alpha
# 15-17, 18-19, 20, 21, 22-24, 25-29 -> Gen Z, but 29 is tricky
# We'll use exact ACS bins and approximate:
#   15-19 and 20-24 and 25-29 combined, then split is impossible without microdata.
# For a clean published table, use the closest exact bins:
# - 15-19, 20-24, 25-29 to approximate 15-28.
# - 29 is included in 25-29, so note this is a 29-inclusive approximation.
#
# Better approach: if you want exact bands, use microdata. For table work, this is the standard limitation.

age_cols = [c for c in b01001.columns if c.startswith("B01001_") and c.endswith("E")]

# Mapping from age bin labels to B01001 cols for each sex.
# Male: 003-025; Female: 027-049 (excluding totals 001, 026)
# We'll construct via known ACS bin indices.
male_bins = {
    "0-4": "B01001_003E", "5-9": "B01001_004E", "10-14": "B01001_005E",
    "15-17": "B01001_006E", "18-19": "B01001_007E", "20": "B01001_008E", "21": "B01001_009E", "22-24": "B01001_010E",
    "25-29": "B01001_011E", "30-34": "B01001_012E", "35-39": "B01001_013E", "40-44": "B01001_014E",
    "45-49": "B01001_015E", "50-54": "B01001_016E", "55-59": "B01001_017E", "60-61": "B01001_018E",
    "62-64": "B01001_019E", "65-66": "B01001_020E", "67-69": "B01001_021E", "70-74": "B01001_022E",
    "75-79": "B01001_023E", "80-84": "B01001_024E", "85+": "B01001_025E"
}
female_bins = {
    "0-4": "B01001_027E", "5-9": "B01001_028E", "10-14": "B01001_029E",
    "15-17": "B01001_030E", "18-19": "B01001_031E", "20": "B01001_032E", "21": "B01001_033E", "22-24": "B01001_034E",
    "25-29": "B01001_035E", "30-34": "B01001_036E", "35-39": "B01001_037E", "40-44": "B01001_038E",
    "45-49": "B01001_039E", "50-54": "B01001_040E", "55-59": "B01001_041E", "60-61": "B01001_042E",
    "62-64": "B01001_043E", "65-66": "B01001_044E", "67-69": "B01001_045E", "70-74": "B01001_046E",
    "75-79": "B01001_047E", "80-84": "B01001_048E", "85+": "B01001_049E"
}

def agg_age_band(df_year):
    d = df_year.copy()
    for c in d.columns:
        if c.endswith("E"):
            d[c] = pd.to_numeric(d[c], errors="coerce")

    bands = {
        "Gen Alpha (0-14)": ["0-4", "5-9", "10-14"],
        "Gen Z (15-28)": ["15-17", "18-19", "20", "21", "22-24", "25-29"],
        "Millennials (29-44)": ["25-29", "30-34", "35-39", "40-44"],
        "Gen X (45-60)": ["45-49", "50-54", "55-59", "60-61"],
        "Baby Boomers (61-79)": ["60-61", "62-64", "65-66", "67-69", "70-74", "75-79"],
        "Silent+ (80+)": ["80-84", "85+"],
    }

    rows = []
    for label, bins in bands.items():
        cols = []
        for b in bins:
            cols.append(male_bins[b])
            cols.append(female_bins[b])
        val = d[cols].iloc[0].sum()
        rows.append({
            "year": int(d["year"].iloc[0]),
            "age_group": label,
            "population": float(val)
        })
    return pd.DataFrame(rows)

age_dist = pd.concat([agg_age_band(b01001[b01001["year"] == y]) for y in b01001["year"].dropna().unique()], ignore_index=True) if not b01001.empty else pd.DataFrame()

# =========================
# Final output tables
# =========================
# Core annual table
annual = pd.DataFrame({"year": sorted(set(ACS_YEARS))})
if not pop.empty:
    annual = annual.merge(pop[["year", "total_population"]].drop_duplicates(), on="year", how="left")
if not mhi.empty:
    annual = annual.merge(mhi[["year", "median_household_income"]].drop_duplicates(), on="year", how="left")
if not pci.empty:
    annual = annual.merge(pci[["year", "per_capita_income"]].drop_duplicates(), on="year", how="left")
if not unemp_yearly.empty:
    annual = annual.merge(unemp_yearly, on="year", how="left")

# Save
annual.to_csv(os.path.join(OUTDIR, "columbus_msa_annual_acs_bls.csv"), index=False)
if not income_dist.empty:
    income_dist.to_csv(os.path.join(OUTDIR, "columbus_msa_income_distribution.csv"), index=False)
if not age_dist.empty:
    age_dist.to_csv(os.path.join(OUTDIR, "columbus_msa_age_distribution.csv"), index=False)
if not b19001.empty:
    b19001.to_csv(os.path.join(OUTDIR, "columbus_msa_b19001_raw.csv"), index=False)
if not b01001.empty:
    b01001.to_csv(os.path.join(OUTDIR, "columbus_msa_b01001_raw.csv"), index=False)

print("Done.")
print(f"Saved files to: {OUTDIR}")
print(annual.head(10).to_string(index=False))