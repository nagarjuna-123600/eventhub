from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    EventCreate, EventFilters, EventList, EventOut,
    RegistrationCreate, RegistrationOut,
)
from app.services import event_service, registration_service

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    return event_service.create_event(db, payload)


@router.get("", response_model=EventList)
def list_events(filters: EventFilters = Depends(), db: Session = Depends(get_db)):
    return event_service.list_events(db, filters)


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    return event_service.get_event(db, event_id)


@router.post(
    "/{event_id}/register",
    response_model=RegistrationOut,
    status_code=status.HTTP_201_CREATED,
)
def register(event_id: int, payload: RegistrationCreate, db: Session = Depends(get_db)):
    return registration_service.register(db, event_id, payload)


@router.get("/{event_id}/registrations", response_model=list[RegistrationOut])
def list_registrations(event_id: int, db: Session = Depends(get_db)):
    return registration_service.list_for_event(db, event_id)
