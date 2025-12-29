# data is saved to data/raw/bw_ais.json
# accessible from (docs/) data/bw_ais.json

"""
Fetch and filter latest AIS positions for offshore rigs from BarentsWatch Live AIS API.

This script:
- Obtains an access token using client credentials
- Fetches AIS messages from the last N minutes
- Filters messages to known rigs (from rig_registry)
- Keeps only the latest message per rig (MMSI)
- Writes a cleaned JSON file for downstream use
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

TOKEN_URL = "https://id.barentswatch.no/connect/token"
AIS_URL = "https://live.ais.barentswatch.no/live/v1/latest/ais"

# Secrets stored in GitHub Actions
CLIENT_ID = os.getenv("BWAPI_CLIENTID_URLENCODED")
CLIENT_SECRET = os.getenv("BWAPI_PWSECRET")

# Time window for AIS messages
TIME_WINDOW_MINUTES = 10

# Output path
OUTPUT_PATH = Path("data/raw/bw_ais.json")

# Reverse lookup: MMSI -> rig name
MMSI_TO_RIG = {mmsi: name for name, mmsi in RIG_MMSI.items()}

# =========================
# Helper functions
# =========================

def get_bw_token(client_id: str, client_secret: str) -> str:
    """Obtain an access token from BarentsWatch using client credentials."""
    if not client_id or not client_secret:
        raise RuntimeError("❌ Missing BWAPI secrets")

    token_body = (
        f"grant_type=client_credentials"
        f"&client_id={client_id}"
        f"&client_secret={client_secret}"
        f"&scope=ais"
    )

    resp = requests.post(
        TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data=token_body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_ais_messages(access_token: str, minutes_back: int = TIME_WINDOW_MINUTES) -> List[Dict[str, Any]]:
    """Fetch AIS messages from BarentsWatch for the last `minutes_back` minutes."""
    since_time = (datetime.now(timezone.utc) - timedelta(minutes=minutes_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"📡 Fetching AIS messages since {since_time}")

    resp = requests.get(
        AIS_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        params={"since": since_time},
        timeout=60,
    )
    resp.raise_for_status()
    messages = resp.json()
    print(f"📦 Received {len(messages)} AIS messages total")
    return messages


def filter_latest_by_rig(
    messages: List[Dict[str, Any]],
    rig_mmsi_dict: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Filter messages to known rigs and keep only the latest message per MMSI."""
    rig_mmsi_set = set(rig_mmsi_dict.values())
    latest_by_mmsi: Dict[int, Dict[str, Any]] = {}

    for msg in messages:
        mmsi = msg.get("mmsi")
        lat = msg.get("latitude")
        lon = msg.get("longitude")
        msgtime_raw = msg.get("msgtime")

        if mmsi not in rig_mmsi_set or lat is None or lon is None or msgtime_raw is None:
            continue

        rig_name = MMSI_TO_RIG.get(mmsi, "UNKNOWN")

        # Parse to datetime for comparison
        msgtime = datetime.fromisoformat(msgtime_raw.replace("Z", "+00:00"))

        prev = latest_by_mmsi.get(mmsi)
        if not prev or msgtime > prev["_msgtime_dt"]:
            latest_by_mmsi[mmsi] = {
                "mmsi": mmsi,
                "rig_name": rig_name,
                "latitude": lat,
                "longitude": lon,
                "msgtime": msgtime_raw,   # keep original string for JSON
                "_msgtime_dt": msgtime,   # internal only
                "source": "barentswatch",
            }

    # Remove internal datetime before returning
    for v in latest_by_mmsi.values():
        v.pop("_msgtime_dt", None)

    print(f"🛢️ Found {len(latest_by_mmsi)} rigs with valid positions")
    return list(latest_by_mmsi.values())

from typing import Any

def write_json(data: Any, path: Path) -> None:
    """Write JSON data to disk, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")

# =========================
# Main entry point
# =========================

def main() -> None:
    print("🔐 Fetching BarentsWatch access token...")
    token = get_bw_token(CLIENT_ID, CLIENT_SECRET)
    print("✅ Access token received")

    messages = fetch_ais_messages(token, TIME_WINDOW_MINUTES)
    rigs = filter_latest_by_rig(messages, RIG_MMSI)

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "barentswatch",
        "rigs": rigs,
    }

    write_json(output, OUTPUT_PATH)

if __name__ == "__main__":
    main()
