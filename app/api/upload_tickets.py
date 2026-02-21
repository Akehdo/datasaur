from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
import pandas as pd
import io
import uuid

from app.mq.rabbit import publish_ticket
from app.core.db import get_db
from app.db.models import Ticket

router = APIRouter()


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    contents = await file.read()

    df = pd.read_csv(
        io.StringIO(contents.decode("utf-8")),
        sep=","
    )

    df.columns = df.columns.str.strip()

    ticket_ids = []
    created_count = 0

    for _, row in df.iterrows():

        # --- GUID обработка ---
        try:
            ticket_guid = uuid.UUID(str(row["GUID клиента"]))
        except Exception:
            continue  # пропускаем некорректные GUID

        # --- Проверка на дубликат ---
        existing_ticket = db.execute(
            select(Ticket).where(Ticket.guid == ticket_guid)
        ).scalar_one_or_none()

        if existing_ticket:
            continue  # если уже есть — пропускаем

        # --- Очистка значений ---
        attachment = None if pd.isna(row.get("Вложения")) else row.get("Вложения")
        house = None if pd.isna(row.get("Дом")) else str(row.get("Дом"))

        ticket = Ticket(
            guid=ticket_guid,
            gender=clean(row.get("Пол клиента")),
            birth_date=clean(row.get("Дата рождения")),
            description=clean(row.get("Описание")),
            attachment=clean(row.get("Вложения")),
            segment=clean(row.get("Сегмент клиента")),
            country=clean(row.get("Страна")),
            region=clean(row.get("Область")),
            city=clean(row.get("Населённый пункт")),
            street=clean(row.get("Улица")),
            house=clean(row.get("Дом"))
        )

        db.add(ticket)
        db.flush()

        ticket_ids.append(ticket.id)
        created_count += 1

    db.commit()

    # --- Отправка в Rabbit ---
    for ticket_id in ticket_ids:
        publish_ticket(ticket_id)

    return {
        "status": "ok",
        "created": created_count
    }


def clean(value):
    import pandas as pd
    if pd.isna(value):
        return None
    value = str(value).strip()
    if value.lower() == "nan":
        return None
    return value.replace(".0", "")