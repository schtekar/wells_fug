
"""
fetch_bwdata.py

Henter AIS-posisjoner fra BarentsWatch Live AIS API
Filtrerer på rigg-MMSI
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

from rig_registry import RIG_MMSI

TOKEN_URL = "https://id.barentswatch.no/connect/token"
AIS_URL = "https://live.ais.barentswatch.no/live/v1/latest/ais"

CLIENT_ID = os.getenv("BWAPI_CLIENTID_URLENCODED")
CLIENT_SECRET = os.getenv("BWAPI_PWSECRET")

OUT_PATH = "docs/bwdata.json"

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("❌ Mangler BWAPI secrets")

# -----------------------------
# 1️⃣ Hent access token
# -----------------------------
print("🔐 Henter BarentsWatch access token...")

token_body = (
    f"grant_type=client_credentials"
    f"&client_id={CLIENT_ID}"
    f"&client_secret={CLIENT_SECRET}"
    f"&scope=ais"
)

token_resp = requests.post(
    TOKEN_URL,
    headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    },
    data=token_body,
    timeout=30,
)

token_resp.raise_for_status()
token_data = token_resp.json()
access_token = token_data["access_token"]

print("✅ Access token mottatt")

# -----------------------------
# 2️⃣ Hent AIS-data (siste 10 min)
# -----------------------------
since_time = (
    datetime.now(timezone.utc) - timedelta(minutes=10)
).strftime("%Y-%m-%dT%H:%M:%SZ")

print(f"📡 Henter AIS-meldinger siden {since_time}")

resp = requests.get(
    AIS_URL,
    headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    },
    params={"since": since_time},
    timeout=60,
)

resp.raise_for_status()
messages = resp.json()

print(f"📦 Mottok {len(messages)} AIS-meldinger totalt")

# -----------------------------
# 3️⃣ Filtrer på rigg-MMSI
# -----------------------------
rig_mmsi_set = set(RIG_MMSI.values())
latest_by_mmsi = {}

for msg in messages:
    mmsi = msg.get("mmsi")
    lat = msg.get("latitude")
    lon = msg.get("longitude")
    msgtime = msg.get("msgtime")

    if mmsi not in rig_mmsi_set:
        continue

    if lat is None or lon is None or msgtime is None:
        continue

    # behold nyeste punkt per MMSI
    prev = latest_by_mmsi.get(mmsi)
    if not prev or msgtime > prev["msgtime"]:
        latest_by_mmsi[mmsi] = {
            "mmsi": mmsi,
            "latitude": lat,
            "longitude": lon,
            "msgtime": msgtime,
            "source": "barentswatch",
        }

print(f"🛢️ Fant {len(latest_by_mmsi)} rigger med gyldig posisjon")

# -----------------------------
# 4️⃣ Skriv til fil
# -----------------------------
os.makedirs("docs", exist_ok=True)

with open(OUT_PATH, "w") as f:
    json.dump(list(latest_by_mmsi.values()), f, indent=2)

print(f"✅ Lagret {OUT_PATH}")
