import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models import Event, Registration, RegistrationStatus
from app.schemas import EventCreate, EventFilters, EventList, EventOut
from app.utils import utcnow


def _confirmed_count_subquery():
    return (
        select(func.count(Registration.id))
        .where(
            Registration.event_id == Event.id,
            Registration.status == RegistrationStatus.CONFIRMED,
        )
        .correlate(Event)
        .scalar_subquery()
    )


def _to_out(event: Event, registered: int) -> EventOut:
    return EventOut(
        id=event.id,
        title=event.title,
        description=event.description,
        date=event.date,
        capacity=event.capacity,
        location=event.location,
        registered_count=registered,
        available_spots=max(event.capacity - registered, 0),
    )


def create_event(db: Session, data: EventCreate) -> EventOut:
    event = Event(**data.model_dump())
    db.add(event)
    db.commit()
    return _to_out(event, 0)


def get_event(db: Session, event_id: int) -> EventOut:
    count = _confirmed_count_subquery()
    row = db.execute(select(Event, count).where(Event.id == event_id)).first()
    if row is None:
        raise NotFoundError(f"Event {event_id} not found.")
    return _to_out(row[0], row[1])


def list_events(db: Session, f: EventFilters) -> EventList:
    conditions = []
    now = utcnow()
    if f.timeframe == "upcoming":
        conditions.append(Event.date > now)
    elif f.timeframe == "past":
        conditions.append(Event.date <= now)
    if f.location:
        conditions.append(Event.location.ilike(f"%{f.location.strip()}%"))

    total = db.scalar(select(func.count(Event.id)).where(*conditions)) or 0
    order = Event.date.desc() if f.timeframe == "past" else Event.date.asc()
    rows = db.execute(
        select(Event, _confirmed_count_subquery())
        .where(*conditions)
        .order_by(order, Event.id)
        .offset((f.page - 1) * f.limit)
        .limit(f.limit)
    ).all()

    return EventList(
        items=[_to_out(e, c) for e, c in rows],
        total=total,
        page=f.page,
        limit=f.limit,
        pages=math.ceil(total / f.limit) if total else 0,
    )
