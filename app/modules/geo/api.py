from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.modules.geo import service
from app.modules.geo.schemas import AddressRequest, OfficeResponse

router = APIRouter()

@router.post("/nearest-office", response_model=OfficeResponse)
def nearest_office(data: AddressRequest, db: Session = Depends(get_db)):
    office = service.get_nearest_office(db, data.address)

    if not office:
        raise HTTPException(404, "No office found")

    return {
        "city": office[0],
        "address": office[1],
        "distance_km": round(float(office[2]), 2),
    }