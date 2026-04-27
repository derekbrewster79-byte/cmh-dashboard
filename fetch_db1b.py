"""
Downloads BTS DB1B Origin-Destination Survey (Market file), 2019–present.
Filters to itineraries where CMH or a peer/aspirational airport is the
origin or destination, then saves a compact summary to:
  data/bts/db1b_summary.csv

Each quarterly zip is ~100 MB; filtered rows are kept in memory and the
zip is discarded before the next download.

Run:  python fetch_db1b.py
"""

import os
import io
import zipfile
import requests
import pandas as pd

AIRPORTS = ["CMH", "IND", "CVG", "CLE", "PIT", "DAY", "AUS", "BNA", "RDU"]
YEARS    = range(2019, 2026)
QUARTERS = range(1, 5)
OUT_DIR  = "data/bts"
OUT_FILE = os.path.join(OUT_DIR, "db1b_summary.csv")

BASE_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "Origin_and_Destination_Survey_DB1BMarket_{year}_{quarter}.zip"
)

# BTS DB1B Market column names (after uppercasing)
KEEP_COLS = [
    "YEAR", "QUARTER",
    "ORIGIN", "DEST",
    "PASSENGERS",
    "MKTFARE",       # market fare (one-way)
    "MKTDISTANCE",   # market distance
    "MKTCOUPONS",    # number of segments
    "OPCARRIER",     # operating carrier
]

os.makedirs(OUT_DIR, exist_ok=True)
all_rows = []

for year in YEARS:
    for quarter in QUARTERS:
        url   = BASE_URL.format(year=year, quarter=quarter)
        label = f"{year} Q{quarter}"
        print(f"[{label}] Downloading...", end=" ", flush=True)

        try:
            r = requests.get(url, timeout=300)
            r.raise_for_status()
        except Exception as e:
            print(f"SKIP ({e})")
            continue

        # Redirect to ErrorPage means the quarter isn't published yet
        if b"ErrorPage" in r.url.encode() or len(r.content) < 10_000:
            print("not available yet, skip")
            continue

        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
                with z.open(csv_name) as f:
                    df = pd.read_csv(f, low_memory=False)

            df.columns = df.columns.str.strip().str.upper()

            mask = df["ORIGIN"].isin(AIRPORTS) | df["DEST"].isin(AIRPORTS)
            df   = df[mask].copy()

            if df.empty:
                print("no matching rows, skip")
                continue

            keep = [c for c in KEEP_COLS if c in df.columns]
            df   = df[keep]

            for col in ["PASSENGERS", "MARKET_FARE", "MARKET_DISTANCE",
                        "MARKET_COUPONS", "YEAR", "QUARTER"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            all_rows.append(df)
            print(f"ok — {len(df):,} rows")

        except Exception as e:
            print(f"ERROR parsing: {e}")

if all_rows:
    result = pd.concat(all_rows, ignore_index=True)
    result.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(result):,} rows → {OUT_FILE}")

    print("\nSample — top O&D markets from CMH (most recent quarter):")
    latest_yr = int(result["YEAR"].max())
    latest_q  = int(result[result["YEAR"] == latest_yr]["QUARTER"].max())
    sample = (
        result[
            (result["YEAR"] == latest_yr) &
            (result["QUARTER"] == latest_q) &
            (result["ORIGIN"] == "CMH")
        ]
        .groupby(["ORIGIN", "DEST"])
        .agg(passengers=("PASSENGERS", "sum"), avg_fare=("MARKET_FARE", "mean"))
        .sort_values("passengers", ascending=False)
        .head(20)
    )
    print(sample.to_string())
else:
    print("No data collected — check network or BTS URL format.")
