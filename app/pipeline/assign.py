from app.db.models import RoundRobinState, Manager, Office


_FOREIGN_OFFICES = ['Астана', 'Алматы']
_foreign_slot = 0


def _next_foreign_office() -> str:
    global _foreign_slot
    office = _FOREIGN_OFFICES[_foreign_slot % 2]
    _foreign_slot += 1
    return office


def get_candidates(session, office_obj: Office,
                   ticket_type: str,
                   segment: str,
                   language: str) -> list:

    all_managers = (
        session.query(Manager)
        .filter(Manager.office_id == office_obj.id)
        .all()
    )

    candidates = all_managers[:]

    if segment in ('VIP', 'Priority'):
        vip_candidates = [m for m in candidates if m.has_skill('VIP')]
        if vip_candidates:
            candidates = vip_candidates

    if ticket_type == 'Смена данных':
        chief_candidates = [m for m in candidates if m.position == 'Главный специалист']
        if chief_candidates:
            candidates = chief_candidates

    if language == 'KZ':
        lang_candidates = [m for m in candidates if m.has_skill('KZ')]
        if lang_candidates:
            candidates = lang_candidates
    elif language == 'ENG':
        lang_candidates = [m for m in candidates if m.has_skill('ENG')]
        if lang_candidates:
            candidates = lang_candidates

    if not candidates:
        candidates = all_managers

    return candidates


def round_robin_pick(session, office_obj: Office, candidates: list) -> Manager:

    top2 = sorted(candidates, key=lambda m: m.workload)[:2]

    rr = (
        session.query(RoundRobinState)
        .filter(RoundRobinState.office_id == office_obj.id)
        .first()
    )

    if rr is None:
        rr = RoundRobinState(office_id=office_obj.id, slot=0)
        session.add(rr)

    slot = rr.slot % len(top2)
    chosen = top2[slot]
    rr.slot = (rr.slot + 1) % len(top2)

    return chosen


def assign_ticket(session, ticket, forced_office: str):

    office_obj = (
        session.query(Office)
        .filter(Office.city == forced_office)
        .first()
    )

    if not office_obj:
        raise Exception(f"Office not found: {forced_office}")

    candidates = get_candidates(
        session,
        office_obj,
        ticket.ticket_type,
        ticket.segment,
        ticket.language
    )

    if not candidates:
        candidates = session.query(Manager).all()
        candidates = sorted(candidates, key=lambda m: m.workload)

    chosen = round_robin_pick(session, office_obj, candidates)
    chosen.workload += 1

    return chosen, office_obj