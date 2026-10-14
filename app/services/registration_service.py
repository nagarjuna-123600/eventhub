from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Event, Registration, RegistrationStatus
from app.schemas import RegistrationCreate
from app.utils import utcnow


def _count_confirmed(db: Session, event_id: int) -> int:
    return db.scalar(
        select(func.count(Registration.id)).where(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.CONFIRMED,
        )
    ) or 0


def register(db: Session, event_id: int, data: RegistrationCreate) -> Registration:
    """Register a user. The capacity check and write happen in one transaction.

    Overbooking is prevented by locking the event row (SELECT ... FOR UPDATE on
    Postgres/MySQL; BEGIN IMMEDIATE write lock on SQLite) before counting.
    """
    event = db.execute(
        select(Event).where(Event.id == event_id).with_for_update()
    ).scalar_one_or_none()
    if event is None:
        raise NotFoundError(f"Event {event_id} not found.")
    if event.date <= utcnow():
        raise BadRequestError("This event has already taken place.")

    email = data.email.lower()
    existing = db.execute(
        select(Registration).where(
            Registration.event_id == event_id, Registration.email == email
        )
    ).scalar_one_or_none()

    if existing and existing.status == RegistrationStatus.CONFIRMED:
        raise ConflictError("This email is already registered for this event.")

    if _count_confirmed(db, event_id) >= event.capacity:
        raise BadRequestError("Event is full. No spots are available.")

    if existing:  # previously cancelled -> re-activate the same row
        existing.status = RegistrationStatus.CONFIRMED
        existing.name = data.name
        registration = existing
    else:
        registration = Registration(
            event_id=event_id, email=email, name=data.name,
            status=RegistrationStatus.CONFIRMED,
        )
        db.add(registration)

    db.commit()
    return registration


def cancel(db: Session, registration_id: int) -> Registration:
    registration = db.get(Registration, registration_id)
    if registration is None:
        raise NotFoundError(f"Registration {registration_id} not found.")
    if registration.status == RegistrationStatus.CANCELLED:
        raise ConflictError("Registration is already cancelled.")
    registration.status = RegistrationStatus.CANCELLED  # frees up a spot
    db.commit()
    return registration


def list_for_event(db: Session, event_id: int) -> list[Registration]:
    if db.get(Event, event_id) is None:
        raise NotFoundError(f"Event {event_id} not found.")
    return list(
        db.scalars(
            select(Registration)
            .where(Registration.event_id == event_id)
            .order_by(Registration.id)
        )
    )
