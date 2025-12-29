# data is saved to docs/kdhdata.json

"""
Fetch latest AIS positions for offshore rigs from Kystdatahuset (KDH) API.

This script:
- Authenticates with KDH using username/password
- Loads relevant wells from Sodir data
- Filters for rigs in the registry
- Fetches first + last AIS positions per rig for 2 or 3 days ago
- Adds internal _timestamp_dt for comparison
- Writes cleaned JSON data for downstream use
"""

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

import requests
from scripts.config.rig_registry import RIG_MMSI

# =========================
# Configuration
# =========================

AUTH_URL = "https://kystdatahuset.no/ws/api/auth/login"
AIS_URL = "https://kystdatahuset.no/ws/api/ais/positions/for-mmsis-time"
DATA_URL = "https://schtekar.github.io/wells_fug/sodirdata.json"

USERNAME = os.getenv("KDH_USERNAME")
PASSWORD = os.getenv("KDH_PW")

OUTPUT_PATH = Path("docs/kdhdata.json")

if not USERNAME or not PASSWORD:
    raise RuntimeError("❌ Missing KDH_USERNAME or KDH_PW environment variables")

# =========================
# Helper functions
# =========================

def authenticate_kdh(username: str, password: str) -> str:
    """Authenticate with Kystdatahuset and return JWT token."""
    print("🔐 Authenticating with Kystdatahuset...")
    payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json", "Accept": "*/*", "User-Agent": "wells_fug/1.0"}
    resp = requests.post(AUTH_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"❌ Authentication failed: {data}")
    print("✅ JWT received")
    return data["data"]["JWT"]

def get_time_interval_utc(days_ago: int) -> (str, str):
    """Return UTC start and end strings (YYYYMMDDHHMM) for 18:00–23:59 UTC on a given day."""
    d = datetime.now(timezone.utc) - timedelta(days=days_ago)
    start = d.replace(hour=18, minute=0, second=0, microsecond=0)
    end = d.replace(hour=23, minute=59, second=59, microsecond=0)
    return start.strftime("%Y%m%d%H%M"), end.strftime("%Y%m%d%H%M")

def fetch_wells() -> List[str]:
    """Fetch well data from Sodir JSON and return rig names found in registry."""
    print("🌍 Fetching wells from Sodir...")
    wells = requests.get(DATA_URL).json()
    unique_rigs = {w["rig_name"] for w in wells if w["rig_name"] in RIG_MMSI}
    print(f"🎯 Rigs found in registry: {unique_rigs}")
    return list(unique_rigs)

def fetch_rig_positions(jwt: str, rig_names: List[str]) -> List[Dict[str, Any]]:
    """Fetch first + last AIS positions per rig for 2 or 3 days ago, including internal _timestamp_dt."""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {jwt}", "User-Agent": "wells_fug/1.0"}
    rig_positions: List[Dict[str, Any]] = []

    for rig in rig_names:
        mmsi = RIG_MMSI[rig]
        print(f"\n🚢 Fetching positions for {rig} (MMSI {mmsi})")
        found_data = False

        for days_ago in [2, 3]:
            start, end = get_time_interval_utc(days_ago)
            payload = {"mmsiIds": [mmsi], "start": start, "end": end, "minSpeed": 0}
            print(f"  ⏱ Trying {days_ago} days ago: {start}–{end}")

            resp = requests.post(AIS_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            datapoints = data.get("data", [])

            print(f"    → success={data.get('success')}, datapoints={len(datapoints)}")
            if data.get("success") and datapoints:
                first, last = datapoints[0], datapoints[-1]
                for idx, point in enumerate([first, last], start=1):
                    ts_raw = point[1]
                    ts_dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    rig_positions.append({
                        "rig_name": rig,
                        "mmsi": mmsi,
                        "days_ago": days_ago,
                        "position_type": "first" if idx == 1 else "last",
                        "lat": point[3],
                        "lon": point[2],
                        "speed": point[4],
                        "course": point[5],
                        "timestamp": ts_raw,
                        "_timestamp_dt": ts_dt,  # internal only for comparison
                    })
                print(f"    ✅ Stored first + last for {days_ago} days ago")
                found_data = True
                break
            else:
                print(f"    ⚠️ No data found for {days_ago} days ago")

        if not found_data:
            print(f"    ❌ No data found for {rig} for either 2 or 3 days ago")

    # Remove internal datetime before returning
    for v in rig_positions:
        v.pop("_timestamp_dt", None)

    return rig_positions

def write_json(data: Any, path: Path) -> None:
    """Write JSON data to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")

# =========================
# Main entry point
# =========================

def main() -> None:
    jwt = authenticate_kdh(USERNAME, PASSWORD)
    rig_names = fetch_wells()
    positions = fetch_rig_positions(jwt, rig_names)

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "kystdatahuset",
        "rigs": positions,
    }

    write_json(output, OUTPUT_PATH)

if __name__ == "__main__":
    main()
