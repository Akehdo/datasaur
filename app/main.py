from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from app.core.db import get_db, SessionLocal
from app.schemas.geo import AddressRequest, OfficeResponse
from app.services.geocoding import geocode_address
from app.services.geo import find_nearest_office
from app.db.seed_offices import seed_offices


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_offices(db)
    finally:
        db.close()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/nearest-office", response_model=OfficeResponse)
def nearest_office(data: AddressRequest, db: Session = Depends(get_db)):
    coords = geocode_address(data.address)
    if not coords:
        raise HTTPException(status_code=404, detail="Address not found")


    lat, lon = coords
    office = find_nearest_office(db, lat, lon)
    if not office:
        raise HTTPException(status_code=404, detail="No offices found")

    if float(office[2]) > 500:
        raise HTTPException(status_code=404, detail="Address not valid")

    return {
        "city": office[0],
        "address": office[1],
        "distance_km": round(float(office[2]), 2),
    }