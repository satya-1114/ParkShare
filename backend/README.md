# ParkShare Backend

FastAPI + SQLAlchemy 2 (async) + PostgreSQL backend for ParkShare, with IBM Granite AI integration.

## Requirements

- Python 3.12+
- PostgreSQL 14+

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Postgres URL, SECRET_KEY, and IBM watsonx credentials

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

## Architecture

```
Router  ->  Service  ->  Repository  ->  SQLAlchemy  ->  PostgreSQL
                \
                 AI module  ->  watsonx.ai (IBM Granite)
```

## AI Module (`app/ai/`)

The AI module integrates IBM Granite via watsonx.ai REST API.

| File | Purpose |
|---|---|
| `client.py` | Async HTTP client for watsonx.ai with IAM token caching (1-hour TTL) |
| `schemas.py` | Pydantic I/O models for all three AI endpoints |
| `prompts.py` | Prompt builder functions (recommendation, pricing, trust) |
| `exceptions.py` | `AIServiceUnavailableError`, `AIInvalidOutputError` |
| `services/trust.py` | Deterministic trust score + Granite explanation |
| `services/recommendation.py` | Granite-ranked parking recommendations |
| `services/pricing.py` | Granite price suggestion with floor/ceiling clamp |
| `router.py` | FastAPI router at `/api/v1/ai` |

### Trust score formula

All new `phone_verified`, `id_verified` (users) and `photos_verified` (parking_spaces)
columns default to `false`. They are set by admins during the verification workflow.

| Factor | Weight |
|---|---|
| Listing verified | 30 |
| Photos verified | 20 |
| Owner ID verified | 20 |
| Owner phone verified | 15 |
| Has completed bookings | 15 |

The trust score is computed **before** Granite is called. Granite only generates
the human-readable explanation. If Granite is unavailable the score is returned
with a deterministic text explanation — the endpoint never fails.

### Graceful degradation

All three AI endpoints respond with `ai_generated: false` when watsonx is unreachable
or returns unparseable output. No HTTP 5xx is raised to the client.

## Environment variables

See `.env.example`. IBM watsonx credentials:

```
WATSONX_API_KEY=...       # SecretStr — never logged
WATSONX_PROJECT_ID=...
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-3-8b-instruct
WATSONX_TIMEOUT_SECONDS=20
WATSONX_MAX_NEW_TOKENS=512
```

## Running tests

```bash
python -m pytest backend/tests/ -v
```

Routers only validate input, call services, and shape responses. Business
rules live in services. Only repositories talk to the database.

## Notes

- Passwords are hashed with Argon2 via `pwdlib`.
- Tokens are HS256 JWTs signed with `SECRET_KEY`.
- All monetary values are `Numeric(10, 2)` — never floats.
- Owners cannot self-verify their listings.
- Public parking search AND public parking detail return only `VERIFIED`
  listings. PENDING / REJECTED / INACTIVE listings return 404 on the public
  detail endpoint so their existence is not exposed. Owners manage their own
  listings through `GET /parkings/mine` and `PATCH /parkings/{id}`.
- Booking availability is **time-interval based**. Capacity is computed from
  bookings whose interval overlaps the requested `[start_time, end_time)` and
  whose status is `CONFIRMED` or `ACTIVE`. `CANCELLED` and `COMPLETED`
  bookings do not consume capacity, and back-to-back bookings (one ends
  exactly when the next starts) do not overlap. A new booking is accepted
  only when overlapping capacity-consuming bookings `< parking.total_slots`;
  otherwise the API returns **HTTP 409**. The capacity check runs inside a
  transaction with `SELECT ... FOR UPDATE` on the parking row to prevent
  overselling under concurrency.
- The legacy `parking.available_slots` column is retained for migration
  compatibility but is **not authoritative** — it is not mutated on booking
  create or cancel, and should not be treated as real-time availability for
  a future interval. Use `total_slots` as capacity.
- Partial `PATCH /parkings/{id}` updates are validated against the merged
  candidate state before the persisted entity is mutated; invalid patches
  return 400 and leave the record unchanged.
