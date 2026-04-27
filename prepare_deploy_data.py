"""
One-time script to generate deployment-ready data for Streamlit Community Cloud.

Filters the large national BTS CSVs (~1.1 GB) down to only the 9 airports used
by the dashboard, producing a data/deploy/ folder (~10-15 MB) that can be
committed to GitHub and served by Streamlit Cloud.

Run once from the project root:
    python prepare_deploy_data.py
"""

import os
import glob
import shutil
import pandas as pd

SRC_DIR    = "data/bts"
DEPLOY_DIR = "data/deploy"

ALL_AIRPORTS = ["CMH", "IND", "CVG", "CLE", "PIT", "DAY", "AUS", "BNA", "RDU"]

MARKET_COLS = {
    "YEAR", "MONTH", "UNIQUE_CARRIER", "UNIQUE_CARRIER_NAME",
    "CARRIER", "CARRIER_NAME",
    "ORIGIN", "ORIGIN_CITY_NAME", "DEST", "DEST_CITY_NAME",
    "PASSENGERS", "FREIGHT", "DISTANCE", "CLASS",
}
SEGMENT_COLS = MARKET_COLS | {
    "SEATS", "DEPARTURES_SCHEDULED", "DEPARTURES_PERFORMED",
    "AIRCRAFT_TYPE", "AIRCRAFT_GROUP", "AIR_TIME",
}

# Small files to copy as-is (already airport-filtered or tiny)
COPY_AS_IS = [
    "ontime_summary.csv",
    "db1b_gateway_connectivity.csv",
    "intl_market_summary.csv",   # may not exist — handled gracefully
]

os.makedirs(DEPLOY_DIR, exist_ok=True)

# ── Process T-100 Market and Segment CSVs ────────────────────────────────────
csv_files = sorted(glob.glob(os.path.join(SRC_DIR, "T_T100D_*.csv")))
if not csv_files:
    print(f"No T_T100D_*.csv files found in {SRC_DIR}. Run fetch scripts first.")
else:
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        out   = os.path.join(DEPLOY_DIR, fname)
        print(f"Processing {fname}...", end=" ", flush=True)
        try:
            header   = pd.read_csv(fpath, nrows=0, encoding="latin-1")
            all_cols = {c.strip().upper(): c.strip() for c in header.columns}
            is_seg   = "DEPARTURES_PERFORMED" in all_cols and "SEATS" in all_cols
            want     = SEGMENT_COLS if is_seg else MARKET_COLS
            usecols  = [orig for norm, orig in all_cols.items() if norm in want]

            df = pd.read_csv(fpath, usecols=usecols, encoding="latin-1", low_memory=False)
            df.columns = df.columns.str.strip().str.upper()

            if "ORIGIN" in df.columns:
                df = df[df["ORIGIN"].isin(ALL_AIRPORTS)].copy()

            df.to_csv(out, index=False)
            src_mb  = os.path.getsize(fpath) / 1e6
            out_mb  = os.path.getsize(out)   / 1e6
            print(f"{src_mb:.0f} MB → {out_mb:.1f} MB ({len(df):,} rows)")
        except Exception as e:
            print(f"ERROR: {e}")

# ── Copy small files ──────────────────────────────────────────────────────────
for fname in COPY_AS_IS:
    src = os.path.join(SRC_DIR, fname)
    dst = os.path.join(DEPLOY_DIR, fname)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"Copied {fname} ({os.path.getsize(dst)/1e3:.0f} KB)")
    else:
        print(f"Skipped {fname} (not present in {SRC_DIR})")

# ── Summary ───────────────────────────────────────────────────────────────────
total_mb = sum(
    os.path.getsize(os.path.join(DEPLOY_DIR, f)) / 1e6
    for f in os.listdir(DEPLOY_DIR)
    if f.endswith(".csv")
)
print(f"\nDone. data/deploy/ is {total_mb:.1f} MB total.")
print("Next steps:")
print("  git add data/deploy/")
print("  git commit -m 'Add pre-filtered deploy data'")
print("  git push")
