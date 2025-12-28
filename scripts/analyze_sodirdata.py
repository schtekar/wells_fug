
import pandas as pd
import json
import os

DATA_PATH = "docs/sodirdata.json"
OUT_PATH = "docs/sodirdata_summary.json"

if not os.path.exists(DATA_PATH):
    print(f"❌ Fant ikke {DATA_PATH}. Avbryter analyse.")
    exit(1)

df = pd.read_json(DATA_PATH)

# --- Sørg for forventede kolonner ---
expected_cols = [
    "purpose",
    "status",
    "entryDate",
    "rig_name",
    "rig_type",
    "operator",
    "well_type",
    "field",
    "well"
]

for col in expected_cols:
    if col not in df.columns:
        df[col] = "UNKNOWN"

# --- Normalisering ---
df["purpose"] = df["purpose"].astype(str).str.upper()
df["status"] = df["status"].astype(str).str.upper()

# --- EntryDate → datetime (NaT for blanks) ---
df["entryDate_dt"] = pd.to_datetime(df["entryDate"], errors="coerce")

# --- Nye tellinger ---
entered_wells = df["entryDate_dt"].notna().sum()
not_started_wells = df["entryDate_dt"].isna().sum()

# --- 10 nyligst entrede brønner ---
latest_entered = (
    df[df["entryDate_dt"].notna()]
    .sort_values("entryDate_dt", ascending=False)
    .head(10)
    .loc[:, ["entryDate", "operator", "field", "well", "rig_name"]]
    .rename(columns={
        "entryDate": "entry_date",
        "operator": "operator",
        "field": "field",
        "well": "well_name",
        "rig_name": "rig"
    })
    .to_dict(orient="records")
)

# --- Eksisterende + nye sammendrag ---
summary = {
    "total_wells": int(len(df)),
    "purpose_counts": df["purpose"].value_counts().to_dict(),
    "online_operational": int((df["status"] == "ONLINE/OPERATIONAL").sum()),

    "entry_status": {
        "entered": int(entered_wells),
        "not_started": int(not_started_wells)
    },

    "latest_entered_wells": latest_entered,

    "top_rigs": (
        df[df["rig_name"] != "UNKNOWN"]
        .groupby("rig_name")
        .size()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    ),

    "rig_type_counts": df["rig_type"].value_counts().to_dict(),
    "operator_counts": df["operator"].value_counts().to_dict(),
    "well_type_counts": df["well_type"].value_counts().to_dict(),
    "field_counts": df["field"].value_counts().to_dict()
}

# --- Skriv til fil ---
with open(OUT_PATH, "w") as f:
    json.dump(summary, f, indent=2)

print("✅ Analyse fullført. Resultat lagret i docs/sodirdata_summary.json")
