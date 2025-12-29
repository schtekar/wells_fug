# scripts/analyze/rw_keystats.py
"""
Compute key statistics from rig and well data for visualization.

Outputs JSON to docs/data/rw_keystats.json with:
- Number of rigs
- Number of wells
- Entered vs not entered wells
- Stationary vs moving rigs
- Number of jackups and semi-subs
- List of recently entered wells, sorted by entry date
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

from scripts.config.rig_registry import RIG_REGISTRY

# =========================
# Paths
# =========================
SODIR_PATH = Path("docs/data/sodirdata.json")
RIG_WELL_PATH = Path("docs/data/rig_well_analysis.json")
OUTPUT_PATH = Path("docs/data/rw_keystats.json")

# =========================
# Safe JSON loader
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

# =========================
# Save JSON
# =========================
def save_json_atomic(data: Dict[str, Any], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)
    print(f"✅ Key statistics written to {path}")

# =========================
# Main computation
# =========================
def main():
    wells = load_json_safe(SODIR_PATH, [])
    rigs_data = load_json_safe(RIG_WELL_PATH, {}).get("rigs", {})

    stats = {
        "num_rigs": len(rigs_data),
        "num_wells": len(wells),
        "entered_wells": 0,
        "not_entered_wells": 0,
        "stationary_rigs": 0,
        "moving_rigs": 0,
        "jackups": 0,
        "semisubs": 0,
        "recent_wells": []  # will store wells sorted by entry date
    }

    now = datetime.now(timezone.utc)
    entered_wells_list: List[Dict[str, Any]] = []

    # ------------------------
    # Wells stats
    # ------------------------
    for w in wells:
        entry_date_str = w.get("entryDate")
        if entry_date_str:
            stats["entered_wells"] += 1
            try:
                entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_since_entry = (now - entry_date).days
            except Exception:
                days_since_entry = None

            entered_wells_list.append({
                "wellbore_name": w.get("wellbore_name"),
                "rig_name": w.get("rig_name"),
                "entry_date": entry_date_str,
                "days_since_entry": days_since_entry
            })
        else:
            stats["not_entered_wells"] += 1

    # Sort wells by newest entry date
    stats["recent_wells"] = sorted(
        entered_wells_list,
        key=lambda x: x["days_since_entry"] if x["days_since_entry"] is not None else 99999
    )

    # ------------------------
    # Rigs stats
    # ------------------------
    for rig_name, rig in rigs_data.items():
        if rig.get("rig_moving"):
            stats["moving_rigs"] += 1
        else:
            stats["stationary_rigs"] += 1

        # Determine rig type via registry
        registry_info = RIG_REGISTRY.get(rig_name.upper())
        rig_type = registry_info.get("type", "").upper() if registry_info else ""
        if rig_type == "JACK-UP":
            stats["jackups"] += 1
        elif rig_type == "SEMI-SUB":
            stats["semisubs"] += 1

    # ------------------------
    # Save output
    # ------------------------
    save_json_atomic(stats, OUTPUT_PATH)


if __name__ == "__main__":
    main()
