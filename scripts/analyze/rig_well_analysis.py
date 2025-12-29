import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta

# =========================
# Paths
# =========================

SODIR_PATH = Path("docs/data/sodirdata.json")
BW_SNAPSHOTS_PATH = Path("docs/data/bw_snapshots.json")
KDH_PATH = Path("docs/data/kdhdata.json")  # optional fallback
OUTPUT_PATH = Path("docs/data/rig_well_analysis.json")

# =========================
# Thresholds
# =========================

STATIONARY_THRESHOLD_M = 50  # configurable
ONSITE_THRESHOLD_M = 100     # distance to consider rig onsite at well

# =========================
# Geo helpers
# =========================

def valid_coords(lat, lon):
    try:
        return lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
    except Exception:
        return False

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# =========================
# Loaders
# =========================

def load_json(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# =========================
# Reference position helper
# =========================

def get_reference_position(rig_snap, source="12h"):
    """
    Return reference position dict for movement comparison.
    source: "12h", "1d", "2d", or "kdh"
    """
    if source == "12h" and rig_snap.get("msg_12h"):
        return rig_snap["msg_12h"]
    elif source == "1d" and rig_snap.get("msg_1d"):
        return rig_snap["msg_1d"]
    elif source == "2d" and rig_snap.get("msg_2d"):
        return rig_snap["msg_2d"]
    elif rig_snap.get("kdh_last"):  # optional KDH fallback
        return rig_snap["kdh_last"]
    return None

# =========================
# Main analysis
# =========================

def main():
    sodir = load_json(SODIR_PATH) or []
    snapshots = load_json(BW_SNAPSHOTS_PATH) or {}
    kdh_data = load_json(KDH_PATH) or {}

    now = datetime.now(timezone.utc)

    # Index wells by rig
    wells_by_rig = {}
    for w in sodir:
        rig = w.get("rig_name")
        if rig and valid_coords(w.get("lat"), w.get("lon")):
            wells_by_rig.setdefault(rig, []).append(w)

    rig_results = {}

    for mmsi, snap in snapshots.items():
        recent = snap.get("msg_recent")
        if not recent or not valid_coords(recent.get("latitude"), recent.get("longitude")):
            continue

        rig_name = recent.get("rig_name")
        lat = recent.get("latitude")
        lon = recent.get("longitude")

        # Determine reference position for movement
        reference_pos = get_reference_position(snap, source="12h")
        movement_m = None
        rig_moving = False

        if reference_pos and valid_coords(reference_pos.get("latitude"), reference_pos.get("longitude")):
            movement_km = haversine_km(
                reference_pos["latitude"], reference_pos["longitude"], lat, lon
            )
            movement_m = movement_km * 1000
            rig_moving = movement_m > STATIONARY_THRESHOLD_M

        # -----------------------
        # Assigned wells & approach
        # -----------------------
        assigned_wells = []
        likely_target_well = None
        min_distance = None

        for w in wells_by_rig.get(rig_name, []):
            w_lat = w["lat"]
            w_lon = w["lon"]
            distance_km = haversine_km(lat, lon, w_lat, w_lon)
            distance_m = distance_km * 1000

            approach_ratio = None
            if reference_pos:
                ref_distance_km = haversine_km(reference_pos["latitude"], reference_pos["longitude"], w_lat, w_lon)
                distance_moved_km = movement_km if movement_m else 0.001  # avoid zero division
                approach_ratio = max(0, (ref_distance_km - distance_km)/distance_moved_km)

            assigned_wells.append({
                "wellbore_name": w["wellbore_name"],
                "distance_m": round(distance_m,1),
                "approach_ratio": None if approach_ratio is None else round(approach_ratio,3)
            })

            if min_distance is None or distance_m < min_distance:
                min_distance = distance_m
                likely_target_well = w["wellbore_name"]

        rig_results[rig_name] = {
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "last_seen": recent.get("msgtime"),
            "rig_moving": rig_moving,
            "movement_m": None if movement_m is None else round(movement_m,1),
            "assigned_wells": assigned_wells,
            "likely_target_well": likely_target_well
        }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump({"generated_at": now.isoformat(), "rigs": rig_results}, f, indent=2)

    print(f"✅ Rig–well analysis written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
