from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import init_db, SessionLocal
from app.db.seeders.seed_offices import seed_offices
from app.db.seeders.seed_managers import seed_managers

from app.modules.tickets.api import router as tickets_router
from app.modules.geo.api import router as geo_router

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🔥 STARTUP
    init_db()

    db = SessionLocal()
    try:
        seed_offices(db)
        seed_managers(db)
        db.commit()
    finally:
        db.close()

    yield  # приложение работает


app = FastAPI(
    title="F.I.R.E. Challenge API",
    lifespan=lifespan  # ← ВОТ ЭТО ГЛАВНОЕ
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def dashboard():
    return FileResponse("static/index.html")
app.include_router(tickets_router)
app.include_router(geo_router)