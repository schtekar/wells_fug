# fetch_kdhdata.py
"""
Fetch historical rig positions from Kystdatahuset (KDH) and merge into ais_msg_main.json.

- Fetches positions for rigs in RIG_MMSI
- Time window: 10:00–12:00 UTC
- Days ago: 3, 7, 30 → msg_3d, msg_1w, msg_1mo
- Stores messages in BW-compatible format
- Merges with existing ais_msg_main.json
"""

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from scripts.config.rig_registry import RIG_MMSI

# =========================
# Config
# =========================
AUTH_URL = "https://kystdatahuset.no/ws/api/auth/login"
AIS_URL = "https://kystdatahuset.no/ws/api/ais/positions/for-mmsis-time"
DATA_URL = "https://schtekar.github.io/wells_fug/data/sodirdata.json"

USERNAME = os.getenv("KDH_USERNAME")
PASSWORD = os.getenv("KDH_PW")

if not USERNAME or not PASSWORD:
    raise RuntimeError("❌ Missing KDH_USERNAME or KDH_PW in environment")

KDH_PATH = Path("data/raw/kdhdata.json")          # filtered and stored KDH messages
MAIN_MSG_PATH = Path("docs/data/ais_msg_main.json")

# =========================
# Helpers
# =========================
def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")

def get_time_interval(days_ago: int) -> (str, str):
    """
    Return 10:00–12:00 UTC for a given day `days_ago`.
    """
    d = datetime.now(timezone.utc) - timedelta(days=days_ago)
    start_dt = d.replace(hour=10, minute=0, second=0, microsecond=0)
    end_dt = d.replace(hour=12, minute=0, second=0, microsecond=0)
    start = start_dt.strftime("%Y%m%d%H%M")
    end = end_dt.strftime("%Y%m%d%H%M")
    return start, end

# =========================
# Main
# =========================
def main():
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

    ais_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {JWT}", "User-Agent": "wells_fug/1.0"}

    # Load existing main doc if exists
    if MAIN_MSG_PATH.exists():
        with MAIN_MSG_PATH.open("r", encoding="utf-8") as f:
            main_doc = json.load(f)
    else:
        main_doc = {}

    # Load or initialize KDH storage
    kdh_messages_store = {}

    # Define days and tags
    days_tags = [(3, "msg_3d"), (7, "msg_1w"), (30, "msg_1mo")]

    for rig in unique_rigs:
        mmsi = RIG_MMSI[rig]
        kdh_messages_store[mmsi] = {}
        print(f"\n🚢 {rig} (MMSI {mmsi})")

        for days_ago, tag in days_tags:
            start, end = get_time_interval(days_ago)
            payload = {"mmsiIds": [mmsi], "start": start, "end": end, "minSpeed": 0}

            r = requests.post(AIS_URL, json=payload, headers=ais_headers)
            r.raise_for_status()
            data = r.json()
            datapoints = data.get("data", [])
            print(f"  ⏱ {days_ago}d ago {start}-{end}: {len(datapoints)} points")

            if datapoints:
                last = datapoints[-1]
                msgtime_raw = last[1]
                msgtime_dt = datetime.fromisoformat(msgtime_raw.replace("Z", "+00:00"))
                msg = {
                    "mmsi": mmsi,
                    "rig_name": rig,
                    "latitude": last[3],
                    "longitude": last[2],
                    "msgtime": msgtime_raw,
                    "_msgtime_dt": msgtime_dt.isoformat(),
                    "source": "kystdatahuset",
                }
                kdh_messages_store[mmsi][tag] = msg
                # Merge into main_doc
                if mmsi not in main_doc:
                    main_doc[mmsi] = {}
                main_doc[mmsi][tag] = msg
                print(f"    ✅ Stored {tag}")
            else:
                print(f"    ⚠️ No data for {days_ago}d ago")

    # Save filtered KDH data
    write_json(kdh_messages_store, KDH_PATH)
    # Update main doc
    write_json(main_doc, MAIN_MSG_PATH)

if __name__ == "__main__":
    main()
