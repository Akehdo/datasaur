from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.tickets import service

router = APIRouter(prefix="/api", tags=["tickets"])


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    created = service.process_csv(contents, db)
    return {"status": "ok", "created": created}


@router.get("/tickets")
def list_tickets(
    office: str | None = Query(None),
    type: str | None = Query(None),
    language: str | None = Query(None),
    priority_min: int = Query(1, ge=1, le=10),
    priority_max: int = Query(10, ge=1, le=10),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    return service.list_tickets_service(
        db,
        office=office,
        type=type,
        language=language,
        priority_min=priority_min,
        priority_max=priority_max,
        limit=limit,
        offset=offset,
    )


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str, db: Session = Depends(get_db)):
    data = service.ticket_detail_service(db, ticket_id)
    if not data:
        raise HTTPException(404, "Ticket not found")
    return data


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return service.stats_service(db)