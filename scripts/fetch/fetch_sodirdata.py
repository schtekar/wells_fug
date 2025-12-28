# data is saved to data/raw/sodirdata.json

"""
Fetch and filter wellbore data from the SODIR (Norwegian Offshore Directorate) API.

This script:
- Retrieves all wellbore features using paginated OBJECTID queries
- Filters to recently entered or not-yet-entered wells
- Excludes wells that will never be drilled
- Writes a cleaned JSON file for downstream use

Designed to run in GitHub Actions.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

import requests


# =========================
# Configuration
# =========================

# SODIR FeatureServer configuration
LAYER_ID = 201  # All wellbores
BASE_URL = "https://factmaps.sodir.no/api/rest/services/Factmaps/FactMapsWGS84/FeatureServer"
QUERY_URL = f"{BASE_URL}/{LAYER_ID}/query"
PAGE_SIZE = 1000

# Output configuration
OUTPUT_PATH = Path("data/raw/sodirdata.json")

# Filtering rules
DAYS_LOOKBACK = 100
EXCLUDED_STATUSES = {
    "WILL NEVER BE DRILLED"
}

# Fields to request from the API
OUT_FIELDS = (
    "wlbWellboreName,"
    "wlbWell,"
    "wlbPurpose,"
    "wlbStatus,"
    "wlbEntryDate,"
    "wlbDrillingFacilityFixedOrMove,"
    "wlbDrillingFacility,"
    "wlbDrillingOperator,"
    "wlbWellType,"
    "wlbField,"
    "wlbFactPageUrl"
)


# =========================
# Helper functions
# =========================

def fetch_all_object_ids() -> List[int]:
    """Fetch all OBJECTIDs from the SODIR FeatureServer."""
    params = {
        "where": "1=1",
        "returnIdsOnly": "true",
        "f": "json"
    }

    response = requests.get(QUERY_URL, params=params)
    response.raise_for_status()

    object_ids = response.json().get("objectIds", [])
    return sorted(object_ids)


def fetch_features_by_objectid_range(object_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Fetch all features from the API using OBJECTID range pagination.
    """
    features: List[Dict[str, Any]] = []

    for i in range(0, len(object_ids), PAGE_SIZE):
        batch = object_ids[i:i + PAGE_SIZE]

        where_clause = f"OBJECTID >= {batch[0]} AND OBJECTID <= {batch[-1]}"
        params = {
            "where": where_clause,
            "outFields": OUT_FIELDS,
            "outSR": 4326,
            "f": "json"
        }

        response = requests.get(QUERY_URL, params=params)
        response.raise_for_status()

        batch_features = response.json().get("features", [])
        features.extend(batch_features)

        print(f"Fetched {len(batch_features)} features "
              f"({i + len(batch_features)}/{len(object_ids)})")

    return features


def parse_entry_date(entry_value: Any) -> datetime | None:
    """
    Parse the SODIR entry date into a datetime object.

    Returns None if the entry date is missing or invalid.
    """
    if entry_value in (None, "", 0):
        return None

    try:
        if isinstance(entry_value, int) and entry_value > 1e7:
            # ESRI timestamp (milliseconds since epoch)
            return datetime.utcfromtimestamp(entry_value / 1000)

        if isinstance(entry_value, int):
            # YYYYMMDD format
            return datetime.strptime(str(entry_value), "%Y%m%d")

        # ISO-like string
        return datetime.strptime(str(entry_value)[:10], "%Y-%m-%d")

    except Exception:
        return None


def is_recent_or_unentered(entry_date: datetime | None, cutoff: datetime) -> bool:
    """Return True if entry date is missing or newer than cutoff."""
    return entry_date is None or entry_date >= cutoff


def filter_features(features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply business rules to filter and normalize SODIR features.
    """
    cutoff_date = datetime.today() - timedelta(days=DAYS_LOOKBACK)
    filtered: List[Dict[str, Any]] = []

    for feature in features:
        attributes = feature.get("attributes", {})
        geometry = feature.get("geometry", {})

        # Geometry validation
        if not geometry or "x" not in geometry or "y" not in geometry:
            continue

        status = (attributes.get("wlbStatus") or "").upper()
        if status in EXCLUDED_STATUSES:
            continue

        entry_date_raw = attributes.get("wlbEntryDate")
        entry_date = parse_entry_date(entry_date_raw)

        if not is_recent_or_unentered(entry_date, cutoff_date):
            continue

        filtered.append({
            "wellbore_name": attributes.get("wlbWellboreName"),
            "well": attributes.get("wlbWell"),
            "status": status,
            "entryDate": entry_date.strftime("%Y-%m-%d") if entry_date else "",
            "rig_name": attributes.get("wlbDrillingFacility") or "UNKNOWN",
            "rig_type": attributes.get("wlbDrillingFacilityFixedOrMove") or "UNKNOWN",
            "operator": attributes.get("wlbDrillingOperator") or "UNKNOWN",
            "well_type": attributes.get("wlbWellType") or "UNKNOWN",
            "field": attributes.get("wlbField") or "UNKNOWN",
            "fact_page_url": attributes.get("wlbFactPageUrl"),
            "lat": geometry["y"],
            "lon": geometry["x"]
        })

    return filtered


def write_json(data: List[Dict[str, Any]], path: Path) -> None:
    """Write JSON data to disk, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# =========================
# Main entry point
# =========================

def main() -> None:
    print("Fetching OBJECTIDs from SODIR...")
    object_ids = fetch_all_object_ids()
    print(f"Found {len(object_ids)} wellbores")

    print("Fetching wellbore features...")
    features = fetch_features_by_objectid_range(object_ids)
    print(f"Total features fetched: {len(features)}")

    print("Filtering features...")
    filtered_wells = filter_features(features)
    print(f"Relevant wells after filtering: {len(filtered_wells)}")

    print(f"Writing output to {OUTPUT_PATH}")
    write_json(filtered_wells, OUTPUT_PATH)

    print("✅ SODIR data fetch complete")


if __name__ == "__main__":
    main()

