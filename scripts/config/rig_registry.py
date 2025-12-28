"""
Rig registry - single source of truth for rig → MMSI + type

Includes helper functions for lookup and filtering.
"""

from typing import Dict, Optional

# -----------------------------
# Main rig registry
# -----------------------------
# Normalized rig_name (uppercased) → metadata
RIG_REGISTRY: Dict[str, Dict[str, str | int]] = {
    "MÆRSK GUARDIAN": {"mmsi": 577494000, "type": "JACK-UP"},
    "WEST LINUS": {"mmsi": 257095000, "type": "JACK-UP"},
    "LINUS": {"mmsi": 257095000, "type": "JACK-UP"},  # alias
    "WEST ELARA": {"mmsi": 259783000, "type": "JACK-UP"},
    "WEST EPSILON": {"mmsi": 351635000, "type": "JACK-UP"},
    "VALARIS VIKING": {"mmsi": 538004075, "type": "JACK-UP"},
    "SCARABEO 8": {"mmsi": 308928000, "type": "SEMISUB"},
    "DEEPSEA ABERDEEN": {"mmsi": 310713000, "type": "SEMISUB"},
    "ASKEPOTT": {"mmsi": 257459000, "type": "JACK-UP"},
    "TRANSOCEAN ENDURANCE": {"mmsi": 538010768, "type": "SEMISUB"},
    "COSLPROMOTER": {"mmsi": 565798000, "type": "SEMISUB"},
    "TRANSOCEAN EQUINOX": {"mmsi": 538010767, "type": "SEMISUB"},
    "COSLINNOVATOR": {"mmsi": 566391000, "type": "SEMISUB"},
    "NOBLE INTEGRATOR": {"mmsi": 538010630, "type": "JACK-UP"},
    "DEEPSEA NORDKAPP": {"mmsi": 310776000, "type": "SEMISUB"},
    "NOBLE INVINCIBLE": {"mmsi": 538010632, "type": "JACK-UP"},
    "TRANSOCEAN ENABLER": {"mmsi": 258615000, "type": "SEMISUB"},
    "DEEPSEA YANTAI": {"mmsi": 311000483, "type": "SEMISUB"},
    "SHELF DRILLING BARSK": {"mmsi": 636016111, "type": "JACK-UP"},
    "ASKELADDEN": {"mmsi": 257452000, "type": "JACK-UP"},
    "COSLPIONEER": {"mmsi": 563050900, "type": "SEMISUB"},
    "TRANSOCEAN SPITSBERGEN": {"mmsi": 538004905, "type": "SEMISUB"},
    "COSLPROSPECTOR": {"mmsi": 565369000, "type": "SEMISUB"},
    "DEEPSEA STAVANGER": {"mmsi": 310767000, "type": "SEMISUB"},
    "TRANSOCEAN ENCOURAGE": {"mmsi": 258627000, "type": "SEMISUB"},
    "DEEPSEA ATLANTIC": {"mmsi": 310766000, "type": "SEMISUB"},
    "DEEPSEA BOLLSTA": {"mmsi": 257440000, "type": "SEMISUB"},
}

# -----------------------------
# Derived dictionaries
# -----------------------------
RIG_MMSI: Dict[str, int] = {name: data["mmsi"] for name, data in RIG_REGISTRY.items()}
RIG_TYPE: Dict[str, str] = {name: data["type"] for name, data in RIG_REGISTRY.items()}

# -----------------------------
# Helper functions
# -----------------------------

def normalize_rig_name(name: str) -> str:
    """Normalize rig name to uppercase stripped string."""
    if not name:
        return ""
    return name.strip().upper()


def get_mmsi_for_rig(rig_name: str) -> Optional[int]:
    """Return MMSI for a given rig name, or None if unknown."""
    key = normalize_rig_name(rig_name)
    rig = RIG_REGISTRY.get(key)
    return rig["mmsi"] if rig else None


def get_type_for_rig(rig_name: str) -> Optional[str]:
    """Return rig type (JACK-UP / SEMISUB) for a given rig name, or None if unknown."""
    key = normalize_rig_name(rig_name)
    rig = RIG_REGISTRY.get(key)
    return rig["type"] if rig else None


def list_known_rigs() -> list[str]:
    """Return a sorted list of all known rig names."""
    return sorted(RIG_REGISTRY.keys())


def list_rigs_by_type(rig_type: str) -> list[str]:
    """Return all rigs of a given type (SEMISUB / JACK-UP)."""
    rig_type = rig_type.strip().upper()
    return sorted(
        name for name, data in RIG_REGISTRY.items() if data["type"] == rig_type
    )
