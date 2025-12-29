# scripts/analyze/rw_keystats.py
"""
Compute key statistics from rig and well data for visualization.

Outputs JSON to docs/data/rw_keystats.json with:
- Number of rigs
- Number of wells
- Entered vs not entered wells
- Stationary vs moving rigs
- Number of jackups and semi-subs
"""

import json
from pathlib import Path
from typing import Dict, Any

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
        "semisubs": 0
    }

    # Wells stats
    for w in wells:
        if w.get("entryDate"):
            stats["entered_wells"] += 1
        else:
            stats["not_entered_wells"] += 1

    # Rigs stats
    for rig in rigs_data.values():
        if rig.get("rig_moving"):
            stats["moving_rigs"] += 1
        else:
            stats["stationary_rigs"] += 1

        rig_type = rig.get("rig_type", "").upper() if "rig_type" in rig else ""
        if rig_type == "JACKUP":
            stats["jackups"] += 1
        elif rig_type == "SEMI-SUB":
            stats["semisubs"] += 1

    save_json_atomic(stats, OUTPUT_PATH)

if __name__ == "__main__":
    main()
