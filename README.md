# EventHub Backend API

FastAPI + SQLAlchemy 2 + SQLite (swap to Postgres via `DATABASE_URL`).
Organizers create events; users RSVP with capacity, duplicate and cancellation rules enforced.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive docs (Swagger): http://127.0.0.1:8000/docs

Optional: `DATABASE_URL=postgresql+psycopg://user:pass@localhost/eventhub` (default: `sqlite:///./eventhub.db`).

## Run tests

```bash
pytest -v
```

Covers validation, capacity limit, **concurrent registrations (no overbooking)**, duplicates, cancel/re-register, pagination and filters, 404s.

## Project structure

```
app/
  main.py            # app, lifespan, router wiring
  database.py        # engine, session, SQLite write-locking
  models.py          # Event, Registration (unique event_id+email)
  schemas.py         # Pydantic request/response validation
  exceptions.py      # custom errors + centralized handlers
  routers/           # thin HTTP layer
  services/          # business logic (capacity, duplicates, cancel)
tests/
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/events` | Create event |
| GET | `/events` | List events (paginated, filtered) |
| GET | `/events/{id}` | Event details incl. `registered_count`, `available_spots` |
| POST | `/events/{id}/register` | RSVP with `email` + `name` |
| GET | `/events/{id}/registrations` | List registrations for an event |
| PATCH | `/registrations/{id}/cancel` | Cancel (frees a spot) |
| GET | `/health` | Health check |

### POST /events
```json
{ "title": "PyCon", "description": "Optional", "date": "2030-05-01T10:00:00Z",
  "capacity": 100, "location": "Berlin" }
```
`date` must be in the future (naive datetimes are treated as UTC); `capacity` must be a positive integer.

### GET /events
Query params: `page` (default 1), `limit` (default 10, max 100), `timeframe` (`upcoming` | `past`), `location` (case-insensitive contains).
```json
{ "items": [ ... ], "total": 25, "page": 1, "limit": 10, "pages": 3 }
```

### POST /events/{id}/register
```json
{ "email": "jane@example.com", "name": "Jane" }
```
Returns `201` with the registration (`status: CONFIRMED`).

## Business rules

- **Capacity:** only `CONFIRMED` registrations count. Full event -> `400 "Event is full..."`.
- **Duplicates:** same email (case-insensitive) already `CONFIRMED` for the event -> `409`. A DB unique constraint backs this up.
- **Cancellation:** `PATCH /registrations/{id}/cancel` sets `CANCELLED`, freeing the spot. Cancelling twice -> `409`. A cancelled user may re-register (the same row is reactivated).
- **Concurrency:** register runs in one transaction that locks the event row (`SELECT ... FOR UPDATE` on Postgres/MySQL; `BEGIN IMMEDIATE` on SQLite) before counting, so parallel requests can't overbook.
- Registering for a past event -> `400`.

## Errors

All errors share one shape:
```json
{ "status": 400, "error": "validation_error", "message": "Invalid request data.",
  "details": [ { "field": "date", "message": "date must be in the future" } ] }
```

| Code | When |
|---|---|
| 400 | Validation failure, event full, past event |
| 404 | Event / registration not found |
| 409 | Duplicate registration, already cancelled, DB conflict |
| 500 | Unexpected error (logged, generic message returned) |
