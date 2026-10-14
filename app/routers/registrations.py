from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RegistrationOut
from app.services import registration_service

router = APIRouter(prefix="/registrations", tags=["Registrations"])


@router.patch("/{registration_id}/cancel", response_model=RegistrationOut)
def cancel_registration(registration_id: int, db: Session = Depends(get_db)):
    return registration_service.cancel(db, registration_id)
