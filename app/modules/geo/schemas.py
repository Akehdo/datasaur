from pydantic import BaseModel

class AddressRequest(BaseModel):
    address: str

class OfficeResponse(BaseModel):
    city: str
    address: str
    distance_km: float