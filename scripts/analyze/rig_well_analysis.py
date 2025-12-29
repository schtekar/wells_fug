import json
import math
from pathlib import Path
from datetime import datetime, timezone

# =========================
# Paths
# =========================

SODIR_PATH = Path("docs/data/sodirdata.json")
BW_SNAPSHOTS_PATH = Path("docs/data/bw_snapshots.json")
KDH_PATH = Path("docs/data/kdhdata.json")  # optional
OUTPUT_PATH = Path("docs/data/rig_well_analysis.json")

# =========================
# Thresholds (tune freely)
# =========================

STATIONARY_THRESHOLD_M = 50
ON_SITE_DISTANCE_M = 200

# =========================
# Utilities
# =========================

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def valid_coords(lat, lon):
    return isinstance(lat, (int, float)) and isinstance(lon, (int, float))


# =========================
# Main analysis
# =========================

def main():
    sodir = load_json(SODIR_PATH, [])
    bw_snapshots = load_json(BW_SNAPSHOTS_PATH, {})
    kdh = load_json(KDH_PATH, [])

    now = datetime.now(timezone.utc).isoformat()

    # -------------------------
    # Index wells by rig
    # -------------------------

    wells_by_rig = {}
    wells_by_name = {}

    for well in sodir:
        rig = well.get("rig_name")
        if not rig:
            continue

        wells_by_rig.setdefault(rig, []).append(well)
        wells_by_name[well.get("wellbore_name")] = well

    # -------------------------
    # Analyze rigs
    # -------------------------

    rig_results = {}
    well_results = {}

    for mmsi, snap in bw_snapshots.items():
        msg = snap.get("msg_recent")
        if not msg:
            continue

        rig_name = msg.get("rig_name")
        lat = msg.get("latitude")
        lon = msg.get("longitude")

        if not rig_name or not valid_coords(lat, lon):
            continue

        # ---------------------
        # Movement detection
        # ---------------------

        running = snap.get("running_msgs", [])
        movement_m = None
        is_moving = None

        if len(running) >= 2:
            prev = running[-2]["msg"]
            if valid_coords(prev.get("latitude"), prev.get("longitude")):
                dist_km = haversine_km(
                    prev["latitude"],
                    prev["longitude"],
                    lat,
                    lon
                )
                movement_m = dist_km * 1000
                is_moving = movement_m > STATIONARY_THRESHOLD_M

        # ---------------------
        # Assigned wells
        # ---------------------

        assigned_wells = wells_by_rig.get(rig_name, [])

        future_wells = [
            w for w in assigned_wells
            if not w.get("entryDate")
        ]

        # ---------------------
        # Distance to wells
        # ---------------------

        closest_well = None
        closest_distance_m = None
        on_site_well = None

        for well in assigned_wells:
            wlat = well.get("lat")
            wlon = well.get("lon")

            if not valid_coords(wlat, wlon):
                continue

            dist_m = haversine_km(lat, lon, wlat, wlon) * 1000

            well_results[well["wellbore_name"]] = {
                "rig_name": rig_name,
                "distance_to_rig_m": round(dist_m, 1),
            }

            if closest_distance_m is None or dist_m < closest_distance_m:
                closest_distance_m = dist_m
                closest_well = well

            if (
                not is_moving
                and dist_m <= ON_SITE_DISTANCE_M
                and well.get("entryDate")
            ):
                on_site_well = well

        # ---------------------
        # Status classification
        # ---------------------

        if on_site_well:
            status = "on_site"
            confidence = "high"
        elif not is_moving:
            status = "stationary"
            confidence = "medium"
        else:
            status = "moving"
            confidence = "medium"

        rig_results[rig_name] = {
            "mmsi": mmsi,
            "latest_position": {
                "lat": lat,
                "lon": lon,
                "msgtime": msg.get("msgtime"),
                "source": msg.get("source"),
            },
            "is_moving": is_moving,
            "movement_m": None if movement_m is None else round(movement_m, 1),
            "status": status,
            "confidence": confidence,
            "closest_well": (
                closest_well.get("wellbore_name") if closest_well else None
            ),
            "closest_distance_m": (
                None if closest_distance_m is None else round(closest_distance_m, 1)
            ),
            "future_wells": [
                w.get("wellbore_name") for w in future_wells
            ],
            "on_site_well": (
                on_site_well.get("wellbore_name") if on_site_well else None
            ),
        }

    # -------------------------
    # Save result
    # -------------------------

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": now,
                "rigs": rig_results,
                "wells": well_results,
            },
            f,
            indent=2,
        )

    print(f"✅ Rig–well analysis written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
