# ParkShare

A community marketplace for trusted private parking spaces, enhanced by IBM Granite-powered decision assistance.

ParkShare connects drivers who need parking with owners who have unused private parking spaces. IBM Granite provides three intelligent capabilities that improve discovery, pricing accuracy, and marketplace trust — while all deterministic business rules remain backend-controlled.

---

## Features

| Capability | Description | AI Role |
|---|---|---|
| **Smart Parking Recommendation** | Ranks VERIFIED parking spaces by price, amenity match, and vehicle compatibility | Granite re-ranks a pre-filtered candidate list and explains why each space fits the driver's needs |
| **Smart Price Suggestion** | Suggests a fair hourly rate for new owner listings | Granite analyses comparable verified listings in the same city and proposes a price within backend-enforced bounds |
| **Trust Score Explanation** | Scores a parking space from 0–100 based on verifiable facts | Granite explains the score in plain language; it cannot change the numeric value |

**All three features degrade gracefully** — if IBM watsonx.ai is unreachable, the marketplace continues to work with deterministic fallback logic and `ai_generated: false` responses.

---

## Architecture

```
Browser (React + TypeScript)
      |
      |  HTTPS / Bearer JWT
      ↓
FastAPI backend  ──→  PostgreSQL (parking, bookings, users)
      |
      ├── /api/v1/auth        JWT authentication
      ├── /api/v1/parkings    Listing CRUD + public search
      ├── /api/v1/bookings    Driver booking + cancellation
      └── /api/v1/ai          IBM Granite AI (recommendation, pricing, trust)
                |
                └──→ IBM watsonx.ai  (ibm/granite-3-3-8b-instruct)
```

**IBM credentials are server-side only.** `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` are read from environment variables in the FastAPI backend and are never sent to the browser, included in API responses, or written to logs.

---

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, and IBM watsonx credentials

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

### Frontend

```bash
# From repository root
bun install
bun dev
```

App: http://localhost:5173

---

## AI Integration

### How it works

1. The frontend sends a standard authenticated request to `/api/v1/ai/*`.
2. The FastAPI backend fetches real data from PostgreSQL (parking spaces, owner records, booking counts).
3. Structured data is sent to IBM watsonx.ai via a direct REST call using `ibm/granite-4-h-small`.
4. The backend validates Granite's output — invented parking IDs are rejected, prices are clamped, and scores are never overridden.
5. The response is returned to the browser with an `ai_generated` flag.

### Trust Score Formula

The trust score is **always deterministic** — computed before Granite is called. Granite only generates the explanation text.

| Factor | Weight | Source |
|---|---|---|
| Listing VERIFIED | 30 | `parking_spaces.status` |
| Photos verified | 20 | `parking_spaces.photos_verified` |
| Owner ID verified | 20 | `users.id_verified` |
| Owner phone verified | 15 | `users.phone_verified` |
| Has completed bookings | 15 | `COUNT(bookings WHERE status=COMPLETED)` |
| **Total** | **100** | |

All three verification columns (`phone_verified`, `id_verified`, `photos_verified`) default to `false` and are set only by an admin verification workflow.

### Environment Variables (Backend)

```env
WATSONX_API_KEY=your-ibm-cloud-api-key        # SecretStr — never logged
WATSONX_PROJECT_ID=your-watsonx-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-3-8b-instruct
WATSONX_TIMEOUT_SECONDS=20
WATSONX_MAX_NEW_TOKENS=512
```

---

## Booking Capacity

Booking availability is **time-interval based**. The stored `available_slots` column is a legacy field and is not used for real-time capacity decisions. When a driver books `[start_time, end_time)`, the backend counts existing `CONFIRMED` or `ACTIVE` bookings that overlap that interval. A new booking is accepted only when overlapping bookings `< parking.total_slots`. The check runs inside a transaction with `SELECT ... FOR UPDATE` to prevent overselling.

---

## Running Tests

```bash
# Backend unit tests (no live DB, no live IBM calls required)
cd backend
python -m pytest tests/ -v

# Frontend TypeScript check
bun run build
```

---

## Project Layout

```
ParkShare/
├── backend/                FastAPI + SQLAlchemy backend
│   ├── app/
│   │   ├── ai/             IBM Granite AI module
│   │   │   ├── client.py           watsonx.ai HTTP client + IAM token cache
│   │   │   ├── prompts.py          Prompt builders
│   │   │   ├── schemas.py          Pydantic I/O models
│   │   │   ├── exceptions.py       AIServiceUnavailableError, AIInvalidOutputError
│   │   │   ├── services/
│   │   │   │   ├── trust.py        Deterministic scorer + Granite explanation
│   │   │   │   ├── recommendation.py  Granite-ranked recommendations
│   │   │   │   └── pricing.py      Granite price suggestion + clamp
│   │   │   └── router.py           /api/v1/ai endpoints
│   │   ├── api/v1/         REST endpoints (auth, parkings, bookings)
│   │   ├── models/         SQLAlchemy ORM models
│   │   ├── repositories/   Database access layer
│   │   ├── services/       Business logic
│   │   └── core/           Config, security, responses
│   ├── alembic/            Database migrations
│   └── tests/              Unit tests
└── src/                    React + TypeScript frontend
    ├── routes/             Page components
    ├── services/
    │   ├── aiService.ts    Typed AI API client
    │   └── parkingService.ts
    └── types/              Shared TypeScript types
```
