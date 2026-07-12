# ParkShare API Reference

Base URL: `http://localhost:8000/api/v1`

All responses follow one envelope:

```json
{ "success": true, "message": "…", "data": { … } }
{ "success": false, "message": "…", "details": null }
```

Authenticate with `Authorization: Bearer <access_token>`.

---

## Health

### GET /health
- **Auth:** none
- **200** `{ status, app, version }`

---

## Authentication

### POST /auth/register
- **Auth:** none
- **Body:** `{ full_name, email, phone, password, role }`  (`role` ∈ `DRIVER`, `OWNER`)
- **201** `{ access_token, token_type, user }`
- **409** email already registered

### POST /auth/login
- **Auth:** none
- **Body:** `{ email, password }`
- **200** `{ access_token, token_type, user }`
- **401** invalid credentials

### GET /auth/me
- **Auth:** bearer
- **200** current `user`
- **401** not authenticated

---

## Parking

### POST /parkings
- **Auth:** bearer, role `OWNER`
- **Body:** `ParkingCreate` (name, address, city, state, pin_code, latitude, longitude, total_slots, hourly_price, vehicle_types[], amenities[], …)
- **201** created listing (`status = PENDING`)

### GET /parkings/mine
- **Auth:** bearer, role `OWNER`
- **200** listings owned by the caller

### GET /parkings
- **Auth:** none
- **Query:** `city, vehicle_type, min_price, max_price, amenity, page, page_size`
  - Note: there is no `available_only` filter. Real-time availability is
    time-interval based and requires a requested start/end time (see
    Bookings). Once the search API accepts an interval it can filter by
    overlap-based capacity; until then availability is checked at booking
    creation time. The legacy `parking.available_slots` column is
    non-authoritative and is not used for search filtering.
- **200** `{ items[], page, page_size, total }`  (VERIFIED listings only)

### GET /parkings/{parking_id}
- **Auth:** none
- **200** parking details (VERIFIED listings only)
- **404** not found — also returned for PENDING / REJECTED / INACTIVE listings so
  their existence is not exposed publicly. Owners retrieve and manage their own
  listings through `GET /parkings/mine` and `PATCH /parkings/{parking_id}`.

### PATCH /parkings/{parking_id}
- **Auth:** bearer, role `OWNER`, owner of the listing
- **Body:** partial `ParkingUpdate` (cannot set `status`)
- Validation is applied to the merged candidate state (existing values +
  patched fields) before mutating the persisted entity. Invalid patches return
  **400** with a descriptive message and leave the record unchanged.
- **200** updated listing

### DELETE /parkings/{parking_id}
- **Auth:** bearer, role `OWNER`, owner of the listing
- **200** deleted

---

## Bookings

Booking availability is **time-interval based**. The stored
`parking.available_slots` column is legacy and is NOT mutated when bookings are
created or cancelled — treat it as non-authoritative.

For a requested interval `[start_time, end_time)` on a parking space, the
backend counts existing bookings whose interval overlaps it and whose status is
capacity-consuming (`CONFIRMED` or `ACTIVE`). An existing booking overlaps
when:

```
existing.start_time < requested.end_time
AND existing.end_time > requested.start_time
```

Back-to-back bookings (one ends exactly when the next starts) do NOT overlap.
`CANCELLED` and `COMPLETED` bookings do NOT consume capacity.

A new booking is accepted only when
`overlapping_capacity_consuming_bookings < parking.total_slots`. For the MVP
one booking consumes one slot. The capacity check and insert run in the same
transaction with a `SELECT ... FOR UPDATE` row lock on the parking row to
prevent overselling under concurrency.

### POST /bookings
- **Auth:** bearer, role `DRIVER`
- **Body:** `{ parking_id, start_time, end_time }` (ISO 8601, must be in the future)
- Backend computes `duration_minutes` and `total_amount` from parking's `hourly_price`.
- **201** booking (`status = CONFIRMED`, unique `booking_reference` like `PS-2026-A7K92M`)
- **400** invalid times / cannot book in the past
- **409** parking is fully booked for the selected interval

### GET /bookings/mine
- **Auth:** bearer, role `DRIVER`
- **200** `{ items[] }`

### GET /bookings/{booking_id}
- **Auth:** bearer, role `DRIVER`, must be booking owner
- **200** booking
- **404** not found

### PATCH /bookings/{booking_id}/cancel
- **Auth:** bearer, role `DRIVER`, must be booking owner
- **200** cancelled booking (removes it from future capacity calculations via status filtering)
- **400** already completed or cancelled

---

---

## AI (IBM Granite)

All AI endpoints return the standard response envelope:
`{ "success": true, "message": "...", "data": { ... } }`

The `ai_generated` boolean indicates whether the response was enriched by Granite
or produced by the deterministic fallback.

> **watsonx.ai endpoint note:**
> The current client calls the watsonx.ai **text generation** REST endpoint:
> `POST {WATSONX_URL}/ml/v1/text/generation?version=2023-05-29`
> IBM has documented a deprecation and removal timeline for this endpoint in favour of
> the watsonx.ai **chat / inference** API. Migration to the chat API is tracked as
> future technical work and is **not** implemented in this release.

### POST /ai/recommendations
- **Auth:** bearer, role `DRIVER`
- **Body:**
  ```json
  {
    "city": "Bengaluru",
    "vehicle_type": "CAR",
    "max_hourly_price": 100,
    "preferred_amenities": ["CCTV", "EV_CHARGING"],
    "preference_context": "need overnight parking near metro"
  }
  ```
  All fields are optional.
- **200:**
  ```json
  {
    "recommendations": [
      { "parking_id": "<uuid>", "rank": 1, "match_score": 85, "reason": "..." }
    ],
    "total_candidates": 12,
    "ai_generated": true,
    "model_id": "ibm/granite-3-3-8b-instruct"
  }
  ```
- **Notes:**
  - Up to 15 candidates are fetched and pre-ranked deterministically before Granite is called.
  - Parking IDs not in the candidate set are rejected (Granite cannot invent IDs).
  - Falls back to deterministic ranking when Granite is unavailable.

### POST /ai/price-suggestion
- **Auth:** bearer, role `OWNER`
- **Body:**
  ```json
  {
    "city": "Mumbai",
    "state": "Maharashtra",
    "parking_type": "COVERED",
    "amenities": ["CCTV", "EV_CHARGING"],
    "vehicle_types": ["CAR", "EV"],
    "total_slots": 4,
    "is_24x7": true
  }
  ```
- **200:**
  ```json
  {
    "suggested_hourly_price": "75.00",
    "price_range": { "min": 40, "max": 120, "median": 70 },
    "explanation": "Based on 8 comparable listings...",
    "comparable_count": 8,
    "ai_generated": true,
    "model_id": "ibm/granite-3-3-8b-instruct"
  }
  ```
- **Notes:**
  - Comparables are selected from VERIFIED same-city listings, preferring matching
    parking type, vehicle type, and amenity overlap.
  - Dynamic allowed bounds are computed from the comparable median:
    `lower = max(₹5, median × 0.5)`, `upper = min(₹5000, median × 1.5)`.
  - Granite is told to stay within these bounds. If it returns a price outside them,
    the response falls back to deterministic with `ai_generated: false`.
  - Absolute safety bounds are ₹5 (floor) and ₹5000 (ceiling).
  - Returns `suggested_hourly_price: null` when no comparables exist in the city.

### GET /ai/trust/{parking_id}
- **Auth:** none (public endpoint)
- **200:**
  ```json
  {
    "parking_id": "<uuid>",
    "trust_score": 65,
    "factors": {
      "listing_verified": true,
      "owner_phone_verified": false,
      "owner_id_verified": true,
      "photos_verified": false,
      "completed_bookings": 3,
      "has_completed_bookings": true
    },
    "explanation": "This parking has a trust score of 65/100...",
    "ai_generated": true,
    "model_id": "ibm/granite-3-3-8b-instruct"
  }
  ```
- **404** if parking not found or not VERIFIED
- **Notes:**
  - The `trust_score` is **deterministic** and cannot be changed by Granite.
  - Granite generates only the `explanation` text.
  - If Granite is unavailable, a plain-text deterministic explanation is returned.

---

## Roadmap

- Admin verification workflow and admin dashboard APIs
- File / image uploads (S3 / object storage) — currently `image_urls` only
- Google Maps / distance calculations
- Payments (Razorpay / Stripe)
- QR / OTP / camera / IoT entry
