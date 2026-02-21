import requests
from sqlalchemy.orm import Session
from app.core.config import DGIS_KEY
from app.modules.geo import repository

DGIS_URL = "https://catalog.api.2gis.com/3.0/items/geocode"


def geocode_address(address: str):
    r = requests.get(
        DGIS_URL,
        params={
            "q": address,
            "fields": "items.point",
            "key": DGIS_KEY
        },
        timeout=10
    )

    data = r.json()
    result = data.get("result")

    if not result or result.get("total", 0) == 0:
        return None

    items = result.get("items", [])
    if not items:
        return None

    point = items[0].get("point")
    if not point:
        return None

    return float(point["lat"]), float(point["lon"])


def get_nearest_office(db: Session, address: str):
    coords = geocode_address(address)
    if not coords:
        return None

    lat, lon = coords
    return repository.find_nearest_office(db, lat, lon)