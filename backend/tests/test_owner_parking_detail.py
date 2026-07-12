"""Integration tests for the OWNER-specific single-listing endpoint.

GET /api/v1/parkings/mine/{parking_id} returns an owner's own listing at ANY
status (PENDING/VERIFIED/REJECTED/INACTIVE), unlike the public
GET /api/v1/parkings/{parking_id} which only exposes VERIFIED listings.
"""
import uuid

import pytest

from tests.conftest import (
    _auth,
    _create_admin_token,
    _create_pending_parking,
    _register,
)


async def test_owner_can_get_own_pending_listing(client):
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)

    resp = await client.get(f"/parkings/mine/{pid}", headers=_auth(owner))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["id"] == pid
    assert data["status"] == "PENDING"


async def test_owner_can_get_own_verified_listing(client):
    owner = await _register(client, "OWNER")
    admin = await _create_admin_token(client)
    pid = await _create_pending_parking(client, owner)

    approve = await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(admin))
    assert approve.status_code == 200, approve.text

    resp = await client.get(f"/parkings/mine/{pid}", headers=_auth(owner))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "VERIFIED"


async def test_owner_cannot_get_another_owners_listing(client):
    owner_a = await _register(client, "OWNER")
    owner_b = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner_a)

    resp = await client.get(f"/parkings/mine/{pid}", headers=_auth(owner_b))
    assert resp.status_code == 404, resp.text


async def test_driver_forbidden_on_owner_detail(client):
    owner = await _register(client, "OWNER")
    driver = await _register(client, "DRIVER")
    pid = await _create_pending_parking(client, owner)

    resp = await client.get(f"/parkings/mine/{pid}", headers=_auth(driver))
    assert resp.status_code == 403, resp.text


async def test_unauthenticated_rejected_on_owner_detail(client):
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)

    resp = await client.get(f"/parkings/mine/{pid}")
    assert resp.status_code == 401, resp.text


async def test_owner_detail_missing_returns_404(client):
    owner = await _register(client, "OWNER")
    resp = await client.get(f"/parkings/mine/{uuid.uuid4()}", headers=_auth(owner))
    assert resp.status_code == 404, resp.text


async def test_public_get_still_hides_pending(client):
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)

    # Public detail endpoint must NOT expose a PENDING listing.
    resp = await client.get(f"/parkings/{pid}")
    assert resp.status_code == 404, resp.text
