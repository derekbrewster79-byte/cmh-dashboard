"""
Processes BTS T-100 International Market data (All Carriers, 2019–present).

BTS international segment/market data requires a manual one-time download —
the BTS site's form pages require browser session state that cannot be automated.

Run this script first; if no data files are found it prints step-by-step
download instructions. Once you have placed the files in data/bts/intl_raw/,
re-run to produce data/bts/intl_market_summary.csv.
"""

import os
import glob
import zipfile
import pandas as pd

AIRPORTS = ["CMH", "IND", "CVG", "CLE", "PIT", "DAY", "AUS", "BNA", "RDU"]
OUT_DIR  = "data/bts"
RAW_DIR  = os.path.join(OUT_DIR, "intl_raw")
OUT_FILE = os.path.join(OUT_DIR, "intl_market_summary.csv")

KEEP_COLS = [
    "YEAR", "MONTH",
    "UNIQUE_CARRIER", "UNIQUE_CARRIER_NAME",
    "ORIGIN", "ORIGIN_CITY_NAME", "ORIGIN_COUNTRY", "ORIGIN_COUNTRY_NAME",
    "DEST",   "DEST_CITY_NAME",   "DEST_COUNTRY",   "DEST_COUNTRY_NAME",
    "PASSENGERS", "FREIGHT", "DISTANCE", "CLASS",
]

DOWNLOAD_INSTRUCTIONS = """
┌─────────────────────────────────────────────────────────────────────────────┐
│          BTS T-100 International Market — Manual Download Steps             │
└─────────────────────────────────────────────────────────────────────────────┘

BTS T-100 International data is not available for automated download.
You'll need to download it manually from the BTS TranStats site (~5 min).

  Download URL:
  https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=GD2

  Steps:
  1.  Open the URL above in your browser.
  2.  In the "Filter by Year and Month" section choose a Year (e.g. 2024)
      and leave Month as "All".
  3.  In the "Filter Geography" section leave all fields blank
      (we filter to our airports in this script).
  4.  In the "Select Columns" section click "Select All".
  5.  Click the "Download" button — a zip file will be saved.
  6.  Repeat steps 2–5 for each year you want (2019–2024 recommended).
  7.  Place all downloaded zip files (or extracted CSVs) in:

        data/bts/intl_raw/

  8.  Re-run this script:  python fetch_international.py

Note: The zip files are named like "T_T100I_MARKET_ALL_CARRIER_2024.zip"
or the CSV inside will be named similarly. Either format is accepted.
"""


def _read_csv_from_zip(zpath):
    with zipfile.ZipFile(zpath) as z:
        csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(csv_name) as f:
            return pd.read_csv(f, low_memory=False, encoding="latin-1")


def _process_df(df):
    df.columns = df.columns.str.strip().str.upper()
    mask = df["ORIGIN"].isin(AIRPORTS) | df["DEST"].isin(AIRPORTS)
    df = df[mask].copy()
    if df.empty:
        return None
    keep = [c for c in KEEP_COLS if c in df.columns]
    df = df[keep]
    for col in ["PASSENGERS", "FREIGHT", "DISTANCE", "YEAR", "MONTH"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    zips = glob.glob(os.path.join(RAW_DIR, "*.zip"))
    csvs = glob.glob(os.path.join(RAW_DIR, "*.csv"))

    if not zips and not csvs:
        print(DOWNLOAD_INSTRUCTIONS)
        return

    all_rows = []

    for zpath in sorted(zips):
        name = os.path.basename(zpath)
        print(f"Reading {name}...", end=" ", flush=True)
        try:
            df = _read_csv_from_zip(zpath)
            df = _process_df(df)
            if df is None:
                print("no matching rows, skip")
            else:
                all_rows.append(df)
                print(f"ok — {len(df):,} rows")
        except Exception as e:
            print(f"ERROR: {e}")

    for cpath in sorted(csvs):
        name = os.path.basename(cpath)
        print(f"Reading {name}...", end=" ", flush=True)
        try:
            df = pd.read_csv(cpath, low_memory=False, encoding="latin-1")
            df = _process_df(df)
            if df is None:
                print("no matching rows, skip")
            else:
                all_rows.append(df)
                print(f"ok — {len(df):,} rows")
        except Exception as e:
            print(f"ERROR: {e}")

    if not all_rows:
        print("\nNo valid rows found in any file. Check file format.")
        return

    result = pd.concat(all_rows, ignore_index=True)
    result.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(result):,} rows → {OUT_FILE}")

    print("\nTop international routes at peer airports (most recent year):")
    latest = result["YEAR"].max()
    summary = (
        result[result["YEAR"] == latest]
        .groupby(["ORIGIN", "DEST_COUNTRY_NAME"])["PASSENGERS"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    print(summary.to_string())


if __name__ == "__main__":
    main()
