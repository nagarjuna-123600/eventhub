from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.exceptions import register_exception_handlers
from app.routers import events, registrations


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="EventHub API",
    description="Create events and RSVP for them, with capacity enforcement.",
    version="1.0.0",
    lifespan=lifespan,
)
register_exception_handlers(app)
app.include_router(events.router)
app.include_router(registrations.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
