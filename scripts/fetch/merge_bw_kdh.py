# merge_bw_kdh.py
import json
from pathlib import Path

# Paths
BW_SNAPSHOT_PATH = Path("docs/data/bw_snapshots.json")
KDH_PATH = Path("docs/data/kdhdata.json")
OUTPUT_PATH = Path("docs/data/ais_msg_main2.json")

def load_json_safe(path: Path, default):
    if not path.exists():
        print(f"⚠️ {path} not found, using default")
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️ {path} contains invalid JSON, using default")
        return default

def save_json_atomic(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)
    print(f"✅ Saved merged JSON to {path} ({len(data)} entries)")

def main():
    bw_data = load_json_safe(BW_SNAPSHOT_PATH, {})
    kdh_data = load_json_safe(KDH_PATH, {})

    merged = {}

    # Merge BW data
    for mmsi, rig_snap in bw_data.items():
        merged[str(mmsi)] = {
            "msg_recent": rig_snap.get("msg_recent"),
            "msg_12h": rig_snap.get("msg_12h"),
            "msg_1d": rig_snap.get("msg_1d"),
            "msg_2d": rig_snap.get("msg_2d")
        }

    # Merge KDH data
    for mmsi, rig_snap in kdh_data.items():
        if not rig_snap:
            continue  # skip rigs with empty dict
        mmsi_str = str(mmsi)
        if mmsi_str not in merged:
            merged[mmsi_str] = {}
        for tag in ["msg_3d", "msg_1w", "msg_1mo"]:
            if tag in rig_snap:
                merged[mmsi_str][tag] = rig_snap[tag]

    save_json_atomic(merged, OUTPUT_PATH)

    # Debug: preview
    print("Preview of first 5 entries:")
    for i, (k, v) in enumerate(merged.items()):
        if i >= 5:
            break
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
