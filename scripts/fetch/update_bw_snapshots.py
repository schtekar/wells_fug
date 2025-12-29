# scripts/fetch/update_bw_snapshots.py
# Purpose: maintain rolling snapshots of BW AIS data for each rig

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from scripts.config.rig_registry import RIG_MMSI

# -------------------------
# Config
# -------------------------
BW_AIS_PATH = Path("docs/data/bw_ais.json")
SNAPSHOT_PATH = Path("docs/data/bw_snapshots.json")
MAX_RUNNING_MSGS = 12  # Keep last 12 messages for each rig
HOURS_12 = 12

# -------------------------
# Helper functions
# -------------------------
def load_json(path: Path) -> Any:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")

def parse_iso_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)

# -------------------------
# Main logic
# -------------------------
def main():
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    
    # Load latest BW messages
    try:
        bw_messages = load_json(BW_AIS_PATH)
    except Exception as e:
        print(f"⚠️ Could not load {BW_AIS_PATH}: {e}")
        bw_messages = []

    # Load existing snapshots
    snapshots = load_json(SNAPSHOT_PATH)

    for rig_name, mmsi in RIG_MMSI.items():
        rig_snap = snapshots.get(rig_name, {
            "msg_recent": None,
            "running_msgs": [],
            "msg_12h": None,
            "msg_1d": None,
            "msg_2d": None
        })

        # Find latest message for this rig
        msgs_for_rig = [m for m in bw_messages if m.get("mmsi") == mmsi]
        if msgs_for_rig:
            latest_msg = max(msgs_for_rig, key=lambda m: parse_iso_utc(m["msgtime"]))
            latest_ts = parse_iso_utc(latest_msg["msgtime"])

            # Update msg_recent if newer
            if not rig_snap["msg_recent"] or latest_ts > parse_iso_utc(rig_snap["msg_recent"]["msgtime"]):
                rig_snap["msg_recent"] = latest_msg
                rig_snap["running_msgs"].append(latest_msg)

        # Prune running messages older than 12h
        pruned_msgs = []
        for msg in rig_snap["running_msgs"]:
            msg_ts = parse_iso_utc(msg["msgtime"])
            if now_utc - msg_ts < timedelta(hours=HOURS_12):
                pruned_msgs.append(msg)
        rig_snap["running_msgs"] = pruned_msgs[-MAX_RUNNING_MSGS:]  # keep last MAX_RUNNING_MSGS

        # Update msg_12h if first message reaches 12h
        if not rig_snap["msg_12h"]:
            for msg in rig_snap["running_msgs"]:
                msg_ts = parse_iso_utc(msg["msgtime"])
                if now_utc - msg_ts >= timedelta(hours=HOURS_12):
                    rig_snap["msg_12h"] = msg
                    break

        snapshots[rig_name] = rig_snap

    # -------------------------
    # Midnight UTC updates (roll 12h → 1d → 2d)
    # -------------------------
    # We'll check if we need to roll by checking the date in snapshots
    last_roll_date = snapshots.get("_last_roll_date")
    if last_roll_date != today_str:
        for rig_snap in snapshots.values():
            if isinstance(rig_snap, dict):
                rig_snap["msg_2d"] = rig_snap.get("msg_1d")
                rig_snap["msg_1d"] = rig_snap.get("msg_12h")
        snapshots["_last_roll_date"] = today_str

    # Write snapshots
    write_json(snapshots, SNAPSHOT_PATH)

if __name__ == "__main__":
    main()
