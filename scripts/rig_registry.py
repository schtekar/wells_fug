"""
rig_registry.py
"""

# -----------------------------
# Rigg-register
# -----------------------------
# rig_name (NORMALISERT) → metadata
# -----------------------------

RIG_REGISTRY = {
    "MÆRSK GUARDIAN": {
        "mmsi": 577494000,
        "type": "JACK-UP",
    },
    "WEST LINUS": {
        "mmsi": 257095000,
        "type": "JACK-UP",
    },
    "LINUS": {  # alias
        "mmsi": 257095000,
        "type": "JACK-UP",
    },
    "WEST ELARA": {
        "mmsi": 259783000,
        "type": "JACK-UP",
    },
    "WEST EPSILON": {
        "mmsi": 351635000,
        "type": "JACK-UP",
    },
    "VALARIS VIKING": {
        "mmsi": 538004075,
        "type": "JACK-UP",
    },
    "SCARABEO 8": {
        "mmsi": 308928000,
        "type": "SEMISUB",
    },
    "DEEPSEA ABERDEEN": {
        "mmsi": 310713000,
        "type": "SEMISUB",
    },
    "ASKEPOTT": {
        "mmsi": 257459000,
        "type": "JACK-UP",
    },
    "TRANSOCEAN ENDURANCE": {
        "mmsi": 538010768,
        "type": "SEMISUB",
    },
    "COSLPROMOTER": {
        "mmsi": 565798000,
        "type": "SEMISUB",
    },
    "TRANSOCEAN EQUINOX": {
        "mmsi": 538010767,
        "type": "SEMISUB",
    },
    "COSLINNOVATOR": {
        "mmsi": 566391000,
        "type": "SEMISUB",
    },
    "NOBLE INTEGRATOR": {
        "mmsi": 538010630,
        "type": "JACK-UP",
    },
    "DEEPSEA NORDKAPP": {
        "mmsi": 310776000,
        "type": "SEMISUB",
    },
    "NOBLE INVINCIBLE": {
        "mmsi": 538010632,
        "type": "JACK-UP",
    },
    "TRANSOCEAN ENABLER": {
        "mmsi": 258615000,
        "type": "SEMISUB",
    },
    "DEEPSEA YANTAI": {
        "mmsi": 311000483,
        "type": "SEMISUB",
    },
    "SHELF DRILLING BARSK": {
        "mmsi": 636016111,
        "type": "JACK-UP",
    },
    "ASKELADDEN": {
        "mmsi": 257452000,
        "type": "JACK-UP",
    },
    "COSLPIONEER": {
        "mmsi": 563050900,
        "type": "SEMISUB",
    },
    "TRANSOCEAN SPITSBERGEN": {
        "mmsi": 538004905,
        "type": "SEMISUB",
    },
    "COSLPROSPECTOR": {
        "mmsi": 565369000,
        "type": "SEMISUB",
    },
    "DEEPSEA STAVANGER": {
        "mmsi": 310767000,
        "type": "SEMISUB",
    },
    "TRANSOCEAN ENCOURAGE": {
        "mmsi": 258627000,
        "type": "SEMISUB",
    },
    "DEEPSEA ATLANTIC": {
        "mmsi": 310766000,
        "type": "SEMISUB",
    },
    "DEEPSEA BOLLSTA": {
        "mmsi": 257440000,
        "type": "SEMISUB",
    },
}

# -----------------------------
# Avledede oppslag (bakoverkompatibilitet)
# -----------------------------

RIG_MMSI = {name: data["mmsi"] for name, data in RIG_REGISTRY.items()}
RIG_TYPE = {name: data["type"] for name, data in RIG_REGISTRY.items()}

# -----------------------------
# Hjelpefunksjoner
# -----------------------------

def normalize_rig_name(name: str) -> str:
    if not name:
        return ""
    return name.strip().upper()


def get_mmsi_for_rig(rig_name: str) -> int | None:
    key = normalize_rig_name(rig_name)
    rig = RIG_REGISTRY.get(key)
    return rig["mmsi"] if rig else None


def get_type_for_rig(rig_name: str) -> str | None:
    key = normalize_rig_name(rig_name)
    rig = RIG_REGISTRY.get(key)
    return rig["type"] if rig else None


def list_known_rigs() -> list[str]:
    return sorted(RIG_REGISTRY.keys())


def list_rigs_by_type(rig_type: str) -> list[str]:
    """
    Returnerer alle rigger av gitt type (SEMISUB / JACK-UP)
    """
    rig_type = rig_type.strip().upper()
    return sorted(
        name for name, data in RIG_REGISTRY.items()
        if data["type"] == rig_type
    )
