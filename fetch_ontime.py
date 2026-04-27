"""
Downloads BTS On-Time Performance monthly zip files (2019-2024),
filters to CMH peer/aspirational airports, aggregates to annual airport-level
on-time stats, and saves a single clean CSV to data/bts/ontime_summary.csv.

Disk-efficient: each zip is downloaded, filtered, then deleted before the next.
"""

import os
import io
import zipfile
import requests
import pandas as pd

AIRPORTS = ["CMH", "IND", "CVG", "CLE", "PIT", "DAY", "AUS", "BNA", "RDU"]
YEARS    = range(2019, 2026)
MONTHS   = range(1, 13)
OUT_DIR  = "data/bts"
OUT_FILE = os.path.join(OUT_DIR, "ontime_summary.csv")

BASE_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

KEEP_COLS = [
    "Year", "Month", "UniqueCarrier", "Origin", "Dest",
    "Cancelled", "Diverted",
    "DepDel15", "ArrDel15",
    "DepDelay", "ArrDelay",
]

os.makedirs(OUT_DIR, exist_ok=True)

summary_rows = []
total = len(list(YEARS)) * 12

done = 0
for year in YEARS:
    for month in MONTHS:
        done += 1
        url = BASE_URL.format(year=year, month=month)
        label = f"{year}-{month:02d}"
        print(f"[{done}/{total}] Downloading {label}...", end=" ", flush=True)

        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
        except Exception as e:
            print(f"SKIP ({e})")
            continue

        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                csv_name = [n for n in z.namelist() if n.endswith(".csv")][0]
                with z.open(csv_name) as f:
                    df = pd.read_csv(f, low_memory=False)

            # Normalize column names
            df.columns = df.columns.str.strip()

            # Filter to our airports (origin or dest)
            df = df[df["Origin"].isin(AIRPORTS) | df["Dest"].isin(AIRPORTS)].copy()

            if df.empty:
                print("no matching rows, skip")
                continue

            # Coerce numeric
            for col in ["Cancelled", "Diverted", "DepDel15", "ArrDel15", "DepDelay", "ArrDelay"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Aggregate by year/month/origin airport
            dep_grp = (
                df[df["Origin"].isin(AIRPORTS)]
                .groupby(["Year", "Month", "Origin"])
                .agg(
                    dep_flights=("Cancelled", "count"),
                    dep_cancelled=("Cancelled", "sum"),
                    dep_delayed=("DepDel15", "sum"),
                )
                .reset_index()
                .rename(columns={"Origin": "Airport"})
            )

            arr_grp = (
                df[df["Dest"].isin(AIRPORTS)]
                .groupby(["Year", "Month", "Dest"])
                .agg(
                    arr_flights=("Cancelled", "count"),
                    arr_cancelled=("Cancelled", "sum"),
                    arr_delayed=("ArrDel15", "sum"),
                )
                .reset_index()
                .rename(columns={"Dest": "Airport"})
            )

            merged = dep_grp.merge(arr_grp, on=["Year", "Month", "Airport"], how="outer")
            summary_rows.append(merged)
            print(f"ok — {len(merged)} airport-month rows")

        except Exception as e:
            print(f"ERROR parsing: {e}")
            continue

if summary_rows:
    result = pd.concat(summary_rows, ignore_index=True)

    # Roll up to annual airport level
    annual = (
        result.groupby(["Year", "Airport"])
        .agg(
            dep_flights=("dep_flights", "sum"),
            dep_cancelled=("dep_cancelled", "sum"),
            dep_delayed=("dep_delayed", "sum"),
            arr_flights=("arr_flights", "sum"),
            arr_cancelled=("arr_cancelled", "sum"),
            arr_delayed=("arr_delayed", "sum"),
        )
        .reset_index()
    )

    annual["dep_ontime_pct"] = (
        (annual["dep_flights"] - annual["dep_cancelled"] - annual["dep_delayed"])
        / (annual["dep_flights"] - annual["dep_cancelled"])
        * 100
    ).round(1)

    annual["arr_ontime_pct"] = (
        (annual["arr_flights"] - annual["arr_cancelled"] - annual["arr_delayed"])
        / (annual["arr_flights"] - annual["arr_cancelled"])
        * 100
    ).round(1)

    annual["combined_ontime_pct"] = (
        (annual["dep_ontime_pct"] + annual["arr_ontime_pct"]) / 2
    ).round(1)

    annual.to_csv(OUT_FILE, index=False)
    print(f"\nSaved: {OUT_FILE}")
    print(annual[annual["Airport"] == "CMH"].to_string(index=False))
else:
    print("No data collected.")
