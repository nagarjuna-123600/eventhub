from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone


def future(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def make_event(client, capacity=2, **overrides):
    payload = {
        "title": "PyCon", "description": "Python meetup", "date": future(),
        "capacity": capacity, "location": "Berlin", **overrides,
    }
    r = client.post("/events", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def rsvp(client, event_id, email, name="Test User"):
    return client.post(f"/events/{event_id}/register", json={"email": email, "name": name})


# ---------- validation ----------
def test_event_date_must_be_future(client):
    r = client.post("/events", json={
        "title": "Old", "date": "2000-01-01T10:00:00Z", "capacity": 5, "location": "X"})
    assert r.status_code == 400
    assert r.json()["error"] == "validation_error"


def test_capacity_must_be_positive_integer(client):
    for bad in (0, -3, "ten", 2.5):
        r = client.post("/events", json={
            "title": "E", "date": future(), "capacity": bad, "location": "X"})
        assert r.status_code == 400, bad


def test_invalid_email_rejected(client):
    ev = make_event(client)
    assert rsvp(client, ev["id"], "not-an-email").status_code == 400


# ---------- capacity ----------
def test_cannot_register_when_full(client):
    ev = make_event(client, capacity=2)
    assert rsvp(client, ev["id"], "a@x.com").status_code == 201
    assert rsvp(client, ev["id"], "b@x.com").status_code == 201
    r = rsvp(client, ev["id"], "c@x.com")
    assert r.status_code == 400
    assert "full" in r.json()["message"].lower()


def test_concurrent_registrations_never_overbook(client):
    ev = make_event(client, capacity=3)
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(
            lambda i: rsvp(client, ev["id"], f"user{i}@x.com").status_code, range(10)))
    assert codes.count(201) == 3
    assert codes.count(400) == 7
    assert client.get(f"/events/{ev['id']}").json()["registered_count"] == 3


# ---------- duplicates & cancellation ----------
def test_duplicate_email_returns_409(client):
    ev = make_event(client)
    assert rsvp(client, ev["id"], "a@x.com").status_code == 201
    r = rsvp(client, ev["id"], "A@X.com")  # case-insensitive
    assert r.status_code == 409


def test_cancel_frees_spot(client):
    ev = make_event(client, capacity=1)
    reg = rsvp(client, ev["id"], "a@x.com").json()
    assert rsvp(client, ev["id"], "b@x.com").status_code == 400

    r = client.patch(f"/registrations/{reg['id']}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert client.get(f"/events/{ev['id']}").json()["available_spots"] == 1

    assert rsvp(client, ev["id"], "b@x.com").status_code == 201


def test_cancelled_user_can_reregister(client):
    ev = make_event(client, capacity=1)
    reg = rsvp(client, ev["id"], "a@x.com").json()
    client.patch(f"/registrations/{reg['id']}/cancel")
    r = rsvp(client, ev["id"], "a@x.com")
    assert r.status_code == 201 and r.json()["status"] == "CONFIRMED"


def test_cancel_twice_returns_409(client):
    ev = make_event(client)
    reg = rsvp(client, ev["id"], "a@x.com").json()
    client.patch(f"/registrations/{reg['id']}/cancel")
    assert client.patch(f"/registrations/{reg['id']}/cancel").status_code == 409


# ---------- listing & errors ----------
def test_pagination_and_location_filter(client):
    for i in range(5):
        make_event(client, title=f"E{i}", location="Berlin" if i < 3 else "Paris")
    r = client.get("/events", params={"page": 1, "limit": 2}).json()
    assert len(r["items"]) == 2 and r["total"] == 5 and r["pages"] == 3
    r = client.get("/events", params={"location": "berl"}).json()
    assert r["total"] == 3


def test_upcoming_vs_past_filter(client):
    from app.database import SessionLocal
    from app.models import Event
    from app.utils import utcnow
    make_event(client)
    with SessionLocal() as db:  # past events can't be created via the API
        db.add(Event(title="Old", date=utcnow() - timedelta(days=3), capacity=5, location="X"))
        db.commit()
    assert client.get("/events", params={"timeframe": "upcoming"}).json()["total"] == 1
    assert client.get("/events", params={"timeframe": "past"}).json()["total"] == 1


def test_not_found_returns_404(client):
    assert client.get("/events/999").status_code == 404
    assert rsvp(client, 999, "a@x.com").status_code == 404
    assert client.patch("/registrations/999/cancel").status_code == 404
