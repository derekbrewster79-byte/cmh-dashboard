"""Supplements fetch_ontime.py — downloads only 2025 months and merges into ontime_summary.csv."""
import os, io, zipfile, requests, pandas as pd

AIRPORTS = ["CMH", "IND", "CVG", "CLE", "PIT", "DAY", "AUS", "BNA", "RDU"]
OUT_FILE = "data/bts/ontime_summary.csv"
BASE_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

summary_rows = []
for month in range(1, 13):
    url = BASE_URL.format(year=2025, month=month)
    print(f"[2025-{month:02d}]", end=" ", flush=True)
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            csv_name = [n for n in z.namelist() if n.endswith(".csv")][0]
            with z.open(csv_name) as f:
                df = pd.read_csv(f, low_memory=False)
        df.columns = df.columns.str.strip()
        df = df[df["Origin"].isin(AIRPORTS) | df["Dest"].isin(AIRPORTS)].copy()
        if df.empty:
            print("no rows"); continue
        for col in ["Cancelled","Diverted","DepDel15","ArrDel15","DepDelay","ArrDelay"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        dep = df[df["Origin"].isin(AIRPORTS)].groupby(["Year","Month","Origin"]).agg(
            dep_flights=("Cancelled","count"), dep_cancelled=("Cancelled","sum"), dep_delayed=("DepDel15","sum")
        ).reset_index().rename(columns={"Origin":"Airport"})
        arr = df[df["Dest"].isin(AIRPORTS)].groupby(["Year","Month","Dest"]).agg(
            arr_flights=("Cancelled","count"), arr_cancelled=("Cancelled","sum"), arr_delayed=("ArrDel15","sum")
        ).reset_index().rename(columns={"Dest":"Airport"})
        summary_rows.append(dep.merge(arr, on=["Year","Month","Airport"], how="outer"))
        print("ok")
    except Exception as e:
        print(f"SKIP ({e})")

if summary_rows:
    new_data = pd.concat(summary_rows, ignore_index=True)
    new_annual = new_data.groupby(["Year","Airport"]).agg(
        dep_flights=("dep_flights","sum"), dep_cancelled=("dep_cancelled","sum"), dep_delayed=("dep_delayed","sum"),
        arr_flights=("arr_flights","sum"), arr_cancelled=("arr_cancelled","sum"), arr_delayed=("arr_delayed","sum"),
    ).reset_index()
    new_annual["dep_ontime_pct"] = ((new_annual["dep_flights"]-new_annual["dep_cancelled"]-new_annual["dep_delayed"])/(new_annual["dep_flights"]-new_annual["dep_cancelled"])*100).round(1)
    new_annual["arr_ontime_pct"] = ((new_annual["arr_flights"]-new_annual["arr_cancelled"]-new_annual["arr_delayed"])/(new_annual["arr_flights"]-new_annual["arr_cancelled"])*100).round(1)
    new_annual["combined_ontime_pct"] = ((new_annual["dep_ontime_pct"]+new_annual["arr_ontime_pct"])/2).round(1)

    if os.path.exists(OUT_FILE):
        existing = pd.read_csv(OUT_FILE)
        existing = existing[existing["Year"] != 2025]  # drop any partial 2025
        combined = pd.concat([existing, new_annual], ignore_index=True)
    else:
        combined = new_annual

    combined.to_csv(OUT_FILE, index=False)
    print(f"\nMerged 2025 data into {OUT_FILE}")
