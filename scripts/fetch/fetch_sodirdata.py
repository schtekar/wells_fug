# data is saved to docs/sodirdata.json

import requests
import json
from datetime import datetime, timedelta

# --- Konfig ---
layer = 201  # All wellbores
base_url = "https://factmaps.sodir.no/api/rest/services/Factmaps/FactMapsWGS84/FeatureServer"
query_url = f"{base_url}/{layer}/query"
page_size = 1000

# Legg til ekstra felter: operator, well type, field
out_fields = (
    "wlbWellboreName,"
    "wlbPurpose,"
    "wlbStatus,"
    "wlbEntryDate,"
    "wlbDrillingFacilityFixedOrMove,"
    "wlbDrillingFacility,"
    "wlbDrillingOperator,"
    "wlbWellType,"
    "wlbField"
)

# --- 1️⃣ Finn alle OBJECTIDs ---
id_params = {"where": "1=1", "returnIdsOnly": "true", "f": "json"}
id_response = requests.get(query_url, params=id_params)
id_response.raise_for_status()
object_ids = sorted(id_response.json().get("objectIds", []))
print(f"Fant {len(object_ids)} brønner totalt")

# --- 2️⃣ Hent alle features i batches ---
features = []
for i in range(0, len(object_ids), page_size):
    batch_ids = object_ids[i:i + page_size]
    where_clause = f"OBJECTID >= {batch_ids[0]} AND OBJECTID <= {batch_ids[-1]}"
    params = {"where": where_clause, "outFields": out_fields, "outSR": 4326, "f": "json"}
    resp = requests.get(query_url, params=params)
    resp.raise_for_status()
    batch_features = resp.json().get("features", [])
    features.extend(batch_features)
    print(f"Hentet {len(batch_features)} brønner ({i + len(batch_features)}/{len(object_ids)})")

print(f"Totalt features hentet: {len(features)}")

# --- 3️⃣ Filtrering ---
today = datetime.today()
cutoff_date = today - timedelta(days=100)
relevant_purposes = {"PRODUCTION", "INJECTION", "WILDCAT"}
filtered_wells = []

for feature in features:
    attr = feature.get("attributes", {})
    geom = feature.get("geometry", {})

    status = (attr.get("wlbStatus") or "").upper()
    purpose = (attr.get("wlbPurpose") or "").upper()
    entry_val = attr.get("wlbEntryDate")

    # Status
    status_ok = status in {"ONLINE/OPERATIONAL", ""}

    # EntryDate (ESRI date kan være millisekund siden 1970)
    if entry_val in (None, "", 0):
        entry_ok = True
        entry_date_str = ""
    else:
        try:
            # Hvis tall og veldig stort → ESRI timestamp (millis)
            if isinstance(entry_val, int) and entry_val > 1e7:
                entry_date = datetime.utcfromtimestamp(entry_val / 1000)
            elif isinstance(entry_val, int):
                entry_date = datetime.strptime(str(entry_val), "%Y%m%d")
            else:
                entry_date = datetime.strptime(str(entry_val)[:10], "%Y-%m-%d")

            entry_ok = entry_date >= cutoff_date
            entry_date_str = entry_date.strftime("%Y-%m-%d")
        except Exception:
            entry_ok = False
            entry_date_str = str(entry_val)

    # Purpose
    purpose_ok = purpose in relevant_purposes

    if status_ok and entry_ok and purpose_ok and geom and "x" in geom and "y" in geom:
        filtered_wells.append({
            "well": attr.get("wlbWellboreName"),
            "purpose": purpose,
            "status": status,
            "entryDate": entry_date_str,
            "rig_name": attr.get("wlbDrillingFacility") or "UNKNOWN",
            "rig_type": attr.get("wlbDrillingFacilityFixedOrMove") or "UNKNOWN",
            "operator": attr.get("wlbDrillingOperator") or "UNKNOWN",
            "well_type": attr.get("wlbWellType") or "UNKNOWN",
            "field": attr.get("wlbField") or "UNKNOWN",
            "lat": geom["y"],
            "lon": geom["x"]
        })

print(f"Etter filtrering: {len(filtered_wells)} relevante brønner")

# --- 4️⃣ Lagre ---
with open("docs/sodirdata.json", "w") as f:
    json.dump(filtered_wells, f, indent=2)

print(f"✅ Lagret {len(filtered_wells)} relevante brønner til docs/sodirdata.json")
