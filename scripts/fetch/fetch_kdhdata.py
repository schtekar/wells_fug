# data is saved to data/raw/kdhdata.json
# accessible from docs/kdhdata.json

"""
Fetch AIS positions from Kystdatahuset (KDH) for known rigs.

This script:
- Authenticates using username/password
- Fetches well/rig data
- Retrieves first and last positions for 2 and 3 days ago
- Stores results as JSON with metadata
"""

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

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

if not USERNAME or not PASSWORD:
    raise RuntimeError("❌ Missing KDH_USERNAME or KDH_PW in environment")

OUTPUT_PATH = Path("data/raw/kdhdata.json")

# =========================
# Helper functions
# =========================

def write_json(data: Any, path: Path) -> None:
    """Write JSON data to disk, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")


def get_time_interval(days_ago: int) -> (str, str):
    """
    Return 18:00–23:59 UTC for a given day `days_ago`.
    """
    d = datetime.now(timezone.utc) - timedelta(days=days_ago)
    start = d.replace(hour=18, minute=0, second=0, microsecond=0).strftime("%Y%m%d%H%M")
    end = d.replace(hour=23, minute=59, second=59, microsecond=0).strftime("%Y%m%d%H%M")
    return start, end


# =========================
# Main entry point
# =========================

def main() -> None:
    print("🔐 Authenticating with Kystdatahuset...")

    auth_payload = {"username": USERNAME, "password": PASSWORD}
    headers = {"Content-Type": "application/json", "Accept": "*/*", "User-Agent": "wells_fug/1.0"}

    resp = requests.post(AUTH_URL, json=auth_payload, headers=headers)
    resp.raise_for_status()
    auth_data = resp.json()

    if not auth_data.get("success"):
        raise RuntimeError(f"❌ Authentication failed: {auth_data}")

    JWT = auth_data["data"]["JWT"]
    print("✅ Authentication OK – JWT received")

    # Fetch well/rig data
    print("🌍 Fetching well/rig data...")
    wells = requests.get(DATA_URL).json()

    unique_rigs = {w["rig_name"] for w in wells if w["rig_name"] in RIG_MMSI}
    print(f"🎯 Rigs found in registry: {unique_rigs}")

    # Headers for AIS requests
    ais_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {JWT}", "User-Agent": "wells_fug/1.0"}

    rig_positions: List[Dict[str, Any]] = []

    for rig in unique_rigs:
        mmsi = RIG_MMSI[rig]
        print(f"\n🚢 {rig} (MMSI {mmsi})")

        found_data = False

        for days_ago in [2, 3]:
            start, end = get_time_interval(days_ago)
            payload = {"mmsiIds": [mmsi], "start": start, "end": end, "minSpeed": 0}

            print(f"  ⏱ Trying {days_ago} days ago: {start}–{end}")

            r = requests.post(AIS_URL, json=payload, headers=ais_headers)
            r.raise_for_status()
            data = r.json()
            datapoints = data.get("data", [])
            print(f"    → success={data.get('success')} datapoints={len(datapoints)}")

            if data.get("success") and datapoints:
                first = datapoints[0]
                last = datapoints[-1]

                rig_positions.append({
                    "rig_name": rig,
                    "mmsi": mmsi,
                    "days_ago": days_ago,
                    "position_type": "first",
                    "lat": first[3],
                    "lon": first[2],
                    "speed": first[4],
                    "course": first[5],
                    "timestamp": first[1]
                })

                rig_positions.append({
                    "rig_name": rig,
                    "mmsi": mmsi,
                    "days_ago": days_ago,
                    "position_type": "last",
                    "lat": last[3],
                    "lon": last[2],
                    "speed": last[4],
                    "course": last[5],
                    "timestamp": last[1]
                })

                print(f"    ✅ Saved first + last for {days_ago} days ago")
                found_data = True
                break
            else:
                print(f"    ⚠️ No data found for {days_ago} days ago")

        if not found_data:
            print(f"    ❌ No data found for {rig} on either 2 or 3 days ago")

    # Add metadata for fetch
    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "kystdatahuset",
        "rigs": rig_positions,
    }

    write_json(output, OUTPUT_PATH)


if __name__ == "__main__":
    main()
