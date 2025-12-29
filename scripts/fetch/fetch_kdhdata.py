# fetch_kdhdata.py
"""
Fetch historical rig positions from Kystdatahuset (KDH) and merge into ais_msg_main.json.

- Fetches positions for rigs in RIG_MMSI
- Time window: 10:00–12:00 UTC
- Days ago: 3, 7, 30 → msg_3d, msg_1w, msg_1mo
- Stores messages in BW-compatible format
- Safely merges into ais_msg_main.json (atomic, concurrency-safe)
"""

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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

KDH_PATH = Path("docs/data/kdhdata.json")
MAIN_MSG_PATH = Path("docs/data/ais_msg_main.json")

# =========================
# Safe JSON helpers
# =========================
def load_json_safe(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️ {path} contains invalid JSON, using default")
        return default


def save_json_atomic(data: Any, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)
    print(f"✅ Saved {path} ({len(data) if isinstance(data, dict) else 'list'})")

# =========================
# Time helper
# =========================
def get_time_interval(days_ago: int) -> tuple[str, str]:
    d = datetime.now(timezone.utc) - timedelta(days=days_ago)
    start_dt = d.replace(hour=10, minute=0, second=0, microsecond=0)
    end_dt = d.replace(hour=12, minute=0, second=0, microsecond=0)
    return (
        start_dt.strftime("%Y%m%d%H%M"),
        end_dt.strftime("%Y%m%d%H%M"),
    )

# =========================
# Main
# =========================
def main():
    print("🔐 Authenticating with Kystdatahuset...")
    auth_payload = {"username": USERNAME, "password": PASSWORD}
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "wells_fug/1.0",
    }

    r = requests.post(AUTH_URL, json=auth_payload, headers=headers)
    r.raise_for_status()
    auth_data = r.json()

    if not auth_data.get("success"):
        raise RuntimeError(f"❌ Authentication failed: {auth_data}")

    jwt = auth_data["data"]["JWT"]
    print("✅ Authentication OK")

    ais_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt}",
        "User-Agent": "wells_fug/1.0",
    }

    print("🌍 Fetching well registry...")
    wells = requests.get(DATA_URL).json()
    rigs = {w["rig_name"] for w in wells if w["rig_name"] in RIG_MMSI}
    print(f"🎯 Rigs found: {sorted(rigs)}")

    # Load existing data safely
    main_doc = load_json_safe(MAIN_MSG_PATH, {})
    kdh_store = {}

    days_tags = [(3, "msg_3d"), (7, "msg_1w"), (30, "msg_1mo")]

    for rig in rigs:
        mmsi = str(RIG_MMSI[rig])   # normalize MMSI
        kdh_store[mmsi] = {}

        print(f"\n🚢 {rig} (MMSI {mmsi})")

        for days_ago, tag in days_tags:
            start, end = get_time_interval(days_ago)
            payload = {
                "mmsiIds": [int(mmsi)],
                "start": start,
                "end": end,
                "minSpeed": 0,
            }

            r = requests.post(AIS_URL, json=payload, headers=ais_headers)
            r.raise_for_status()
            datapoints = r.json().get("data", [])

            print(f"  ⏱ {days_ago}d ago {start}-{end}: {len(datapoints)} points")

            if not datapoints:
                continue

            last = datapoints[-1]
            msg = {
                "mmsi": int(mmsi),
                "rig_name": rig,
                "latitude": last[3],
                "longitude": last[2],
                "msgtime": last[1],
                "source": "kystdatahuset",
            }

            kdh_store[mmsi][tag] = msg

            main_doc.setdefault(mmsi, {})
            main_doc[mmsi][tag] = msg

            print(f"    ✅ Stored {tag}")

    # Atomic writes
    save_json_atomic(kdh_store, KDH_PATH)
    save_json_atomic(main_doc, MAIN_MSG_PATH)

    print("✅ KDH AIS merge complete")

if __name__ == "__main__":
    main()
