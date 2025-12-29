import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Paths
BW_JSON_PATH = Path("docs/data/bw_ais.json")
SNAPSHOT_PATH = Path("docs/data/bw_snapshots.json")
MAIN_MSG_PATH = Path("docs/data/ais_msg_main.json")

# =========================
# Helper functions
# =========================

def load_bw_messages(path: Path):
    if not path.exists():
        print(f"⚠️ {path} not found, returning empty list")
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            # If it's a dict, try to get 'rigs' key
            if isinstance(data, dict):
                messages = data.get("rigs", [])
            elif isinstance(data, list):
                messages = data
            else:
                print(f"⚠️ Unexpected JSON structure in {path}, returning empty list")
                return []

            # Keep only dicts
            messages = [m for m in messages if isinstance(m, dict)]
            return messages
    except json.JSONDecodeError:
        print(f"⚠️ Could not decode JSON in {path}, returning empty list")
        return []

def load_snapshots(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except json.JSONDecodeError:
        print(f"⚠️ Could not decode JSON in {path}, returning empty dict")
        return {}

def save_json_safely(data: dict, path: Path):
    if not data:
        print(f"⚠️ No data to save to {path}, skipping write")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Saved JSON to {path} ({len(data)} entries)")
    except Exception as e:
        print(f"❌ Failed to save {path}: {e}")

# =========================
# Main
# =========================

def main():
    now = datetime.now(timezone.utc)
    bw_messages = load_bw_messages(BW_JSON_PATH)
    snapshots = load_snapshots(SNAPSHOT_PATH)

    if not bw_messages:
        print(f"⚠️ No BW messages found in {BW_JSON_PATH}, skipping snapshot update")
        return

    print(f"ℹ️ Loaded {len(bw_messages)} BW messages")

    # Process messages
    for msg in bw_messages:
        try:
            msg_dt = datetime.fromisoformat(msg["msgtime"].replace("Z", "+00:00"))
        except Exception:
            continue

        mmsi = msg.get("mmsi")
        if mmsi is None:
            continue

        if mmsi not in snapshots:
            snapshots[mmsi] = {
                "msg_recent": None,
                "running_msgs": [],
                "msg_12h": None,
                "msg_1d": None,
                "msg_2d": None
            }

        rig_snap = snapshots[mmsi]
        rig_snap["msg_recent"] = msg
        running_msgs = rig_snap.setdefault("running_msgs", [])

        # Avoid duplicates
        if all(r.get("msgtime") != msg["msgtime"] for r in running_msgs):
            running_msgs.append({"msg": msg, "msgtime_dt": msg_dt})

        running_msgs.sort(key=lambda x: x["msgtime_dt"])
        if len(running_msgs) > 12:
            running_msgs[:] = running_msgs[-12:]

        # msg_12h
        rig_snap["msg_12h"] = None
        for r in running_msgs:
            if now - r["msgtime_dt"] >= timedelta(hours=12):
                rig_snap["msg_12h"] = r["msg"]
                break

        # Remove messages older than 12h
        running_msgs[:] = [r for r in running_msgs if now - r["msgtime_dt"] < timedelta(hours=12)]

    # Update msg_1d / msg_2d at midnight UTC
    if now.hour == 0 and now.minute < 60:
        for rig_snap in snapshots.values():
            rig_snap["msg_2d"] = rig_snap.get("msg_1d")
            rig_snap["msg_1d"] = rig_snap.get("msg_12h")

    # Clean internal datetime
    for rig_snap in snapshots.values():
        for r in rig_snap.get("running_msgs", []):
            r.pop("msgtime_dt", None)

    # Save snapshots
    save_json_safely(snapshots, SNAPSHOT_PATH)

    # Build main AIS message doc
    main_doc = {
        mmsi: {
            "msg_recent": rig_snap.get("msg_recent"),
            "msg_12h": rig_snap.get("msg_12h"),
            "msg_1d": rig_snap.get("msg_1d"),
            "msg_2d": rig_snap.get("msg_2d"),
        }
        for mmsi, rig_snap in snapshots.items()
        if rig_snap.get("msg_recent") is not None
    }

    print(f"Main doc has {len(main_doc)} entries. Keys: {list(main_doc.keys())[:5]}")  # show first 5 keys
    save_json_safely(main_doc, MAIN_MSG_PATH)


if __name__ == "__main__":
    main()
