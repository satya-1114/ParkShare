"""Integration tests for the ADMIN parking verification workflow."""
import uuid

import pytest

from tests.conftest import (
    _auth,
    _create_admin_token,
    _create_pending_parking,
    _register,
)


# --- listing pending ------------------------------------------------------

async def test_admin_can_list_pending(client):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)

    resp = await client.get("/admin/parkings/pending", headers=_auth(admin))
    assert resp.status_code == 200, resp.text
    ids = [p["id"] for p in resp.json()["data"]]
    assert pid in ids
    assert all(p["status"] == "PENDING" for p in resp.json()["data"])


async def test_owner_forbidden_on_pending(client):
    owner = await _register(client, "OWNER")
    resp = await client.get("/admin/parkings/pending", headers=_auth(owner))
    assert resp.status_code == 403


async def test_driver_forbidden_on_pending(client):
    driver = await _register(client, "DRIVER")
    resp = await client.get("/admin/parkings/pending", headers=_auth(driver))
    assert resp.status_code == 403


async def test_unauthenticated_rejected(client):
    resp = await client.get("/admin/parkings/pending")
    assert resp.status_code == 401


# --- approve --------------------------------------------------------------

async def test_admin_can_approve_and_status_verified(client):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)

    resp = await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(admin))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "VERIFIED"


async def test_verified_parking_appears_in_public_search(client):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    city = f"City{uuid.uuid4().hex[:8]}"
    pid = await _create_pending_parking(client, owner, city=city)

    # Not searchable while pending.
    pre = await client.get("/parkings", params={"city": city})
    assert pid not in [p["id"] for p in pre.json()["data"]["items"]]

    await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(admin))

    post = await client.get("/parkings", params={"city": city})
    assert pid in [p["id"] for p in post.json()["data"]["items"]]


# --- reject ---------------------------------------------------------------

async def test_admin_can_reject_and_status_rejected(client):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)

    resp = await client.patch(f"/admin/parkings/{pid}/reject", headers=_auth(admin))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "REJECTED"


# --- role enforcement on mutations ---------------------------------------

@pytest.mark.parametrize("role", ["OWNER", "DRIVER"])
async def test_non_admin_cannot_approve(client, role):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)
    actor = await _register(client, role)
    resp = await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(actor))
    assert resp.status_code == 403


@pytest.mark.parametrize("role", ["OWNER", "DRIVER"])
async def test_non_admin_cannot_reject(client, role):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)
    actor = await _register(client, role)
    resp = await client.patch(f"/admin/parkings/{pid}/reject", headers=_auth(actor))
    assert resp.status_code == 403


# --- not found & invalid transitions -------------------------------------

async def test_invalid_uuid_returns_404(client):
    admin = await _create_admin_token(client)
    missing = uuid.uuid4()
    resp = await client.patch(f"/admin/parkings/{missing}/approve", headers=_auth(admin))
    assert resp.status_code == 404


async def test_approve_already_verified_rejected(client):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)
    await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(admin))
    resp = await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(admin))
    assert resp.status_code == 409


async def test_approve_rejected_parking_rejected(client):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)
    await client.patch(f"/admin/parkings/{pid}/reject", headers=_auth(admin))
    resp = await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(admin))
    assert resp.status_code == 409


async def test_reject_verified_parking_rejected(client):
    admin = await _create_admin_token(client)
    owner = await _register(client, "OWNER")
    pid = await _create_pending_parking(client, owner)
    await client.patch(f"/admin/parkings/{pid}/approve", headers=_auth(admin))
    resp = await client.patch(f"/admin/parkings/{pid}/reject", headers=_auth(admin))
    assert resp.status_code == 409
