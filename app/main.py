import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request


from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import requests as http_requests

from app.core.db import get_db, init_db, SessionLocal
from app.db.seeders.seed_managers import seed_managers
from app.db.seeders.seed_offices import seed_offices

from app.schemas.geo import AddressRequest, OfficeResponse
from app.services.geocoding import geocode_address
from app.services.geo import find_nearest_office

from app.db.models import Ticket, Office, Manager

from app.api.upload_tickets import router as upload_router


templates = Jinja2Templates(directory="templates")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")


# =====================================================
# Lifespan
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    db = SessionLocal()
    try:
        if not db.query(Office).first():
            seed_offices(db)

        if not db.query(Manager).first():
            seed_managers(db)

    finally:
        db.close()

    yield



app = FastAPI(title="LLM Dashboard + Geo", lifespan=lifespan)


app.include_router(upload_router)

# =====================================================
# UI
# =====================================================

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# =====================================================
# Tickets API
# =====================================================

@app.get("/api/tickets")
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
    q = db.query(Ticket)

    if office:
        q = (
            q.join(Office, Ticket.assigned_office_id == Office.id)
             .filter(Office.city == office)
        )

    if type:
        q = q.filter(Ticket.ticket_type == type)

    if language:
        q = q.filter(Ticket.language == language)

    q = q.filter(
        Ticket.priority >= priority_min,
        Ticket.priority <= priority_max,
    )

    total = q.count()
    tickets = (
        q.order_by(Ticket.priority.desc())
         .offset(offset)
         .limit(limit)
         .all()
    )

    return {"total": total, "items": [_ticket_short(t) for t in tickets]}


@app.get("/api/tickets/{ticket_id}")
def ticket_detail(ticket_id: str, db: Session = Depends(get_db)):
    t = db.query(Ticket).get(ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    return _ticket_full(t)


# =====================================================
# Stats
# =====================================================

@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):

    def agg(col):
        return {
            v: c
            for v, c in db.query(col, func.count())
                          .group_by(col)
                          .all()
            if v
        }

    by_office = {
        city: count
        for city, count in (
            db.query(Office.city, func.count(Ticket.id))
              .join(Ticket, Ticket.assigned_office_id == Office.id)
              .group_by(Office.city)
              .all()
        )
    }

    return {
        "total": db.query(Ticket).count(),
        "by_type": agg(Ticket.ticket_type),
        "by_office": by_office,
        "by_language": agg(Ticket.language),
        "by_tone": agg(Ticket.tone),
        "by_segment": agg(Ticket.segment),
        "priority_avg": db.query(func.avg(Ticket.priority)).scalar(),
        "offices": [o.city for o in db.query(Office).all()],
    }


# =====================================================
# AI Assistant
# =====================================================

class AskRequest(BaseModel):
    question: str


@app.post("/api/ask")
def ask(body: AskRequest, db: Session = Depends(get_db)):
    try:
        by_type = agg_query(db, Ticket.ticket_type)
        by_office = {
            city: count
            for city, count in (
                db.query(Office.city, func.count(Ticket.id))
                  .join(Ticket, Ticket.assigned_office_id == Office.id)
                  .group_by(Office.city)
                  .all()
            )
        }
        by_lang = agg_query(db, Ticket.language)
        by_tone = agg_query(db, Ticket.tone)

        data_context = (
            "Данные системы:\n"
            f"По типу обращений: {json.dumps(by_type, ensure_ascii=False)}\n"
            f"По офисам: {json.dumps(by_office, ensure_ascii=False)}\n"
            f"По языкам: {json.dumps(by_lang, ensure_ascii=False)}\n"
            f"По тональности: {json.dumps(by_tone, ensure_ascii=False)}\n"
        )

        prompt = (
            "Ты аналитик данных. На основе предоставленных данных создай Chart.js конфигурацию.\n"
            'Верни ТОЛЬКО валидный JSON с полем "config".\n\n'
            f"{data_context}\n"
            f"Запрос пользователя: {body.question}\n\n"
            '{"title": "заголовок графика", "config": {}}'
        )

        resp = http_requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=30,
        )

        resp.raise_for_status()
        return json.loads(resp.json()["response"].strip())

    except Exception as e:
        return {"error": str(e), "title": "Ошибка", "config": {}}


# =====================================================
# Geo Endpoint
# =====================================================

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


# =====================================================
# Helpers
# =====================================================

def agg_query(db, col):
    return {
        v: c
        for v, c in db.query(col, func.count())
                      .group_by(col)
                      .all()
        if v
    }


def _ticket_short(t: Ticket) -> dict:
    return {
        "id": str(t.id),
        "guid": str(t.guid),
        "segment": t.segment,
        "city": t.city,
        "type": t.ticket_type,
        "tone": t.tone,
        "priority": t.priority,
        "language": t.language,
        "office": t.assigned_office.city if t.assigned_office else None,
        "manager": t.manager.name if t.manager else None,
    }


def _ticket_full(t: Ticket) -> dict:
    d = _ticket_short(t)
    d.update(
        {
            "description": t.description,
            "summary": t.summary,
            "recommendation": t.recommendation,
            "country": t.country,
            "region": t.region,
            "street": t.street,
            "house": t.house,
            "lat": t.lat,
            "lon": t.lon,
            "manager_position": t.manager.position if t.manager else None,
            "manager_skills": t.manager.skills if t.manager else None,
            "processed_at": t.processed_at.isoformat() if t.processed_at else None,
        }
    )
    return d