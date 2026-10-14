from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import RegistrationStatus
from app.utils import to_naive_utc, utcnow


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    date: datetime
    capacity: int = Field(gt=0, strict=True, description="Max attendees (positive integer)")
    location: str = Field(min_length=1, max_length=200)

    @field_validator("title", "location")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("date")
    @classmethod
    def date_in_future(cls, v: datetime) -> datetime:
        v = to_naive_utc(v)
        if v <= utcnow():
            raise ValueError("date must be in the future")
        return v


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    date: datetime
    capacity: int
    location: str
    registered_count: int
    available_spots: int


class EventList(BaseModel):
    items: list[EventOut]
    total: int
    page: int
    limit: int
    pages: int


class EventFilters(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)
    timeframe: Literal["upcoming", "past"] | None = None
    location: str | None = None


class RegistrationCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    email: str
    name: str
    status: RegistrationStatus
    created_at: datetime
