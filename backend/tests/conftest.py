"""Shared fixtures for DB-backed integration tests (admin workflow).

These tests run against the configured Postgres database (DATABASE_URL) using
the real application stack via an in-process ASGI transport. Each helper uses
unique emails so tests are independent and can run against a shared database.
"""
import uuid
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.main import app
from app.models.user import User, UserRole


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c


async def _register(client: AsyncClient, role: str) -> str:
    """Register a DRIVER/OWNER via the public API and return the bearer token."""
    resp = await client.post(
        "/auth/register",
        json={
            "full_name": f"Test {role}",
            "email": _email(role.lower()),
            "phone": "9998887777",
            "password": "supersecret123",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["access_token"]


async def _create_admin_token(client: AsyncClient) -> str:
    """Create an ADMIN directly in the DB (public registration is blocked) and
    return a valid bearer token by logging in."""
    email = _email("admin")
    password = "adminsecret123"
    async with AsyncSessionLocal() as session:
        admin = User(
            full_name="Test Admin",
            email=email,
            phone="9990001111",
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _parking_payload(city: str = "TestCity") -> dict:
    return {
        "name": "Downtown Garage",
        "description": "A safe covered spot",
        "property_type": "COMMERCIAL_BUILDING",
        "address": "12 Market Street",
        "city": city,
        "state": "TestState",
        "pin_code": "560001",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "total_slots": 5,
        "available_slots": 5,
        "parking_type": "COVERED",
        "hourly_price": 40,
        "daily_price": 300,
        "is_24x7": True,
        "vehicle_types": ["CAR", "BIKE"],
        "amenities": ["CCTV", "SECURITY"],
        "image_urls": [],
    }


async def _create_pending_parking(client: AsyncClient, owner_token: str, city: str = "TestCity") -> str:
    resp = await client.post("/parkings", json=_parking_payload(city), headers=_auth(owner_token))
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["status"] == "PENDING"
    return data["id"]
