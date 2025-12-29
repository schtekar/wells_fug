# scripts/fetch/update_lastknownpos.py

"""
Update last known positions for all rigs by merging BW and KDH latest data
with previously stored last-known positions.

- Reads docs/data/bw_ais.json and docs/data/kdhdata.json
- Reads existing lastknowndata.json if present
- Updates positions for rigs with new data, preserves old positions otherwise
- Writes updated lastknowndata.json to docs/data/lastknowndata.json
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

from scripts.config.rig_registry import RIG_MMSI

# ---------------------------
# Paths
# ---------------------------
BW_FILE = Path("docs/data/bw_ais.json")
KDH_FILE = Path("docs/data/kdhdata.json")
LAST_KNOWN_FILE = Path("docs/data/lastknowndata.json")

# ---------------------------
# Helper functions
# ---------------------------
def read_json(path: Path) -> Any:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None

def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")

# ---------------------------
# Load previous last-known positions
# ---------------------------
last_known: Dict[str, Dict[str, Any]] = {}
existing_data = read_json(LAST_KNOWN_FILE)
if existing_data:
    for entry in existing_data.get("rigs", []):
        rig_name = entry["rig_name"]
        last_known[rig_name] = entry

# ---------------------------
# Load latest BW data
# ---------------------------
bw_data = read_json(BW_FILE) or []
for entry in bw_data:
    rig_name = entry.get("rig_name")
    if rig_name and entry.get("latitude") is not None and entry.get("longitude") is not None:
        last_known[rig_name] = {
            "rig_name": rig_name,
            "mmsi": entry.get("mmsi"),
            "latitude": entry.get("latitude"),
            "longitude": entry.get("longitude"),
            "msgtime": entry.get("msgtime"),
            "source": entry.get("source", "barentswatch"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

# ---------------------------
# Load latest KDH data
# ---------------------------
kdh_data = read_json(KDH_FILE) or {}
for entry in kdh_data.get("rigs", []):
    rig_name = entry.get("rig_name")
    if rig_name and entry.get("lat") is not None and entry.get("lon") is not None:
        last_known[rig_name] = {
            "rig_name": rig_name,
            "mmsi": entry.get("mmsi"),
            "latitude": entry.get("lat"),
            "longitude": entry.get("lon"),
            "msgtime": entry.get("timestamp"),
            "source": entry.get("source", "kystdatahuset"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

# ---------------------------
# Ensure all rigs from registry exist
# ---------------------------
for rig_name in RIG_MMSI.keys():
    if rig_name not in last_known:
        last_known[rig_name] = {
            "rig_name": rig_name,
            "mmsi": RIG_MMSI[rig_name],
            "latitude": None,
            "longitude": None,
            "msgtime": None,
            "source": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

# ---------------------------
# Write updated last-known positions
# ---------------------------
output = {
    "fetched_at": datetime.now(timezone.utc).isoformat(),
    "rigs": list(last_known.values())
}

write_json(output, LAST_KNOWN_FILE)
