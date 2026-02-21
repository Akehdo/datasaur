from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.modules.tickets.models import Ticket, Office


# -----------------------------
# CREATE / EXISTS
# -----------------------------

def exists_by_guid(db: Session, guid) -> bool:
    stmt = select(Ticket.id).where(Ticket.guid == guid)
    return db.execute(stmt).scalar_one_or_none() is not None


def create_ticket(db: Session, ticket_data: dict) -> Ticket:
    ticket = Ticket(**ticket_data)
    db.add(ticket)
    db.flush()
    return ticket


# -----------------------------
# SINGLE
# -----------------------------

def get_ticket_by_id(db: Session, ticket_id: str) -> Optional[Ticket]:
    return db.get(Ticket, ticket_id)


# -----------------------------
# LIST
# -----------------------------

def get_tickets(
    db: Session,
    office: Optional[str] = None,
    type: Optional[str] = None,
    language: Optional[str] = None,
    priority_min: int = 1,
    priority_max: int = 10,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[int, List[Ticket]]:

    stmt = select(Ticket)

    if office:
        stmt = (
            stmt.join(Office, Ticket.assigned_office_id == Office.id)
                .where(Office.city == office)
        )

    if type:
        stmt = stmt.where(Ticket.ticket_type == type)

    if language:
        stmt = stmt.where(Ticket.language == language)

    stmt = stmt.where(
        Ticket.priority >= priority_min,
        Ticket.priority <= priority_max
    )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(total_stmt).scalar()

    stmt = (
        stmt.order_by(Ticket.priority.desc())
            .offset(offset)
            .limit(limit)
    )

    items = db.execute(stmt).scalars().all()

    return total, items


# -----------------------------
# STATS
# -----------------------------

def get_stats(db: Session):

    def agg(column):
        stmt = select(column, func.count()).group_by(column)
        return {
            value: count
            for value, count in db.execute(stmt).all()
            if value
        }

    office_stmt = (
        select(Office.city, func.count(Ticket.id))
        .join(Ticket, Ticket.assigned_office_id == Office.id)
        .group_by(Office.city)
    )

    by_office = {
        city: count
        for city, count in db.execute(office_stmt).all()
    }

    return {
        "total": db.scalar(select(func.count(Ticket.id))),
        "by_type": agg(Ticket.ticket_type),
        "by_office": by_office,
        "by_language": agg(Ticket.language),
        "by_tone": agg(Ticket.tone),
        "by_segment": agg(Ticket.segment),
        "priority_avg": db.scalar(select(func.avg(Ticket.priority))),
        "offices": db.scalars(select(Office.city)).all(),
    }