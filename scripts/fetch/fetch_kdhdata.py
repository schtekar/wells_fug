import json
import math
from pathlib import Path
from datetime import datetime, timezone

# =========================
# Paths
# =========================
SODIR_PATH = Path("docs/data/sodirdata.json")
AIS_MAIN_PATH = Path("docs/data/ais_msg_main.json")  # includes BW + KDH messages
OUTPUT_PATH = Path("docs/data/rig_well_analysis.json")

# =========================
# Thresholds
# =========================
STATIONARY_THRESHOLD_M = 50   # configurable
ONSITE_THRESHOLD_M = 100      # distance to consider rig onsite at well

# =========================
# Geo helpers
# =========================
def valid_coords(lat, lon):
    try:
        return (
            lat is not None
            and lon is not None
            and not math.isnan(lat)
            and not math.isnan(lon)
        )
    except Exception:
        return False

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

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

def save_json_atomic(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)

# =========================
# Reference position helper
# =========================
from scripts.config.rw_analysis_config import REFERENCE_POSITION_OPTIONS

def get_reference_position(rig_data, period="12h"):
    """
    Return reference position dict for movement comparison.
    period: "12h", "1d", "2d", "3d", "1w", "1mo"
    """
    config = REFERENCE_POSITION_OPTIONS.get(period)
    if not config:
        return None
    return rig_data.get(config["tag"])

# =========================
# Main analysis
# =========================
def main():
    sodir = load_json_safe(SODIR_PATH, [])
    main_data = load_json_safe(AIS_MAIN_PATH, {})

    now = datetime.now(timezone.utc)

    # Index wells by rig
    wells_by_rig = {}
    for w in sodir:
        rig = w.get("rig_name")
        if rig and valid_coords(w.get("lat"), w.get("lon")):
            wells_by_rig.setdefault(rig, []).append(w)

    rig_results = {}

    for mmsi_key, rig_snap in main_data.items():
        mmsi = str(mmsi_key)  # normalize MMSI

        recent = rig_snap.get("msg_recent")
        if not recent or not valid_coords(recent.get("latitude"), recent.get("longitude")):
            continue

        rig_name = recent.get("rig_name")
        lat = recent.get("latitude")
        lon = recent.get("longitude")

        # -----------------------
        # Movement analysis
        # -----------------------
        reference_pos = get_reference_position(rig_snap, period="12h")

        movement_km = None
        movement_m = None
        rig_moving = False

        if reference_pos and valid_coords(
            reference_pos.get("latitude"), reference_pos.get("longitude")
        ):
            movement_km = haversine_km(
                reference_pos["latitude"],
                reference_pos["longitude"],
                lat,
                lon,
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
            if reference_pos and movement_km:
                ref_distance_km = haversine_km(
                    reference_pos["latitude"],
                    reference_pos["longitude"],
                    w_lat,
                    w_lon,
                )
                distance_moved_km = movement_km or 0.001
                approach_ratio = max(
                    0, (ref_distance_km - distance_km) / distance_moved_km
                )

            assigned_wells.append(
                {
                    "wellbore_name": w["wellbore_name"],
                    "distance_m": round(distance_m, 1),
                    "approach_ratio": None
                    if approach_ratio is None
                    else round(approach_ratio, 3),
                }
            )

            if min_distance is None or distance_m < min_distance:
                min_distance = distance_m
                likely_target_well = w["wellbore_name"]

        rig_results[rig_name] = {
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "last_seen": recent.get("msgtime"),
            "rig_moving": rig_moving,
            "movement_m": None if movement_m is None else round(movement_m, 1),
            "assigned_wells": assigned_wells,
            "likely_target_well": likely_target_well,
        }

    save_json_atomic(
        {
            "generated_at": now.isoformat(),
            "rigs": rig_results,
        },
        OUTPUT_PATH,
    )

    print(f"✅ Rig–well analysis written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
