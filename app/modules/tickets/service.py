from sqlalchemy.orm import Session
from app.modules.tickets import repository


# -----------------------------
# CSV
# -----------------------------

def process_csv(contents: bytes, db: Session):
    import pandas as pd
    import io
    import uuid
    from app.infrastructure.rabbit.publisher import publish_ticket

    df = pd.read_csv(io.StringIO(contents.decode("utf-8")), sep=",")
    df.columns = df.columns.str.strip()

    created = 0
    ticket_ids = []

    for _, row in df.iterrows():
        try:
            ticket_guid = uuid.UUID(str(row["GUID клиента"]))
        except Exception:
            continue

        if repository.exists_by_guid(db, ticket_guid):
            continue

        ticket_data = {
            "guid": ticket_guid,
            "gender": clean(row.get("Пол клиента")),
            "birth_date": clean(row.get("Дата рождения")),
            "description": clean(row.get("Описание")),
            "attachment": clean(row.get("Вложения")),
            "segment": clean(row.get("Сегмент клиента")),
            "country": clean(row.get("Страна")),
            "region": clean(row.get("Область")),
            "city": clean(row.get("Населённый пункт")),
            "street": clean(row.get("Улица")),
            "house": clean(row.get("Дом")),
        }

        ticket = repository.create_ticket(db, ticket_data)
        ticket_ids.append(ticket.id)
        created += 1

    db.commit()

    for tid in ticket_ids:
        publish_ticket(tid)

    return created


def clean(value):
    import pandas as pd
    if pd.isna(value):
        return None
    value = str(value).strip()
    if value.lower() == "nan":
        return None
    return value.replace(".0", "")


# -----------------------------
# LIST
# -----------------------------

def list_tickets_service(db: Session, **filters):
    total, items = repository.get_tickets(db, **filters)
    return {
        "total": total,
        "items": [ticket_to_short(t) for t in items],
    }


# -----------------------------
# DETAIL
# -----------------------------

def ticket_detail_service(db: Session, ticket_id: str):
    ticket = repository.get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    return ticket_to_full(ticket)


# -----------------------------
# STATS
# -----------------------------

def stats_service(db: Session):
    return repository.get_stats(db)


# -----------------------------
# DTO
# -----------------------------

def ticket_to_short(t):
    return {
        "id": str(t.id),
        "guid": str(t.guid),
        "segment": t.segment,
        "type": t.ticket_type,
        "tone": t.tone,
        "priority": t.priority,
        "language": t.language,
        "office": t.assigned_office.city if t.assigned_office else None,
        "manager": t.manager.name if t.manager else None,
    }


def ticket_to_full(t):
    return {
        "id": str(t.id),
        "guid": str(t.guid),
        "segment": t.segment,
        "type": t.ticket_type,
        "tone": t.tone,
        "priority": t.priority,
        "language": t.language,
        "city": t.city,
        "country": t.country,
        "office": t.assigned_office.city if t.assigned_office else None,
        "manager": t.manager.name if t.manager else None,
        "manager_position": t.manager.position if t.manager else None,
        "manager_skills": t.manager.skills if t.manager else None,
        "processed_at": t.processed_at.isoformat() if t.processed_at else None,
        "description": t.description,
        "summary": t.summary,
        "recommendation": t.recommendation,
    }