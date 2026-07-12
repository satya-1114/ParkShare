from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ok
from app.database.session import get_session
from app.dependencies.auth import get_current_user, require_owner
from app.models.parking import Amenity, ParkingSpace, VehicleType
from app.models.user import User
from app.schemas.parking import (
    ParkingCreate,
    ParkingImageOut,
    ParkingListOut,
    ParkingOut,
    ParkingSearchQuery,
    ParkingUpdate,
)
from app.services.parking import ParkingService

router = APIRouter(prefix="/parkings", tags=["Parking"])


def _serialize(space: ParkingSpace) -> dict:
    out = ParkingOut(
        id=space.id,
        owner_id=space.owner_id,
        name=space.name,
        description=space.description,
        property_type=space.property_type,
        address=space.address,
        city=space.city,
        state=space.state,
        pin_code=space.pin_code,
        latitude=float(space.latitude),
        longitude=float(space.longitude),
        total_slots=space.total_slots,
        available_slots=space.available_slots,
        parking_type=space.parking_type,
        hourly_price=space.hourly_price,
        daily_price=space.daily_price,
        is_24x7=space.is_24x7,
        opening_time=space.opening_time,
        closing_time=space.closing_time,
        status=space.status,
        vehicle_types=[v.vehicle_type for v in space.vehicle_types],
        amenities=[a.amenity for a in space.amenities],
        images=[ParkingImageOut.model_validate(i) for i in space.images],
        created_at=space.created_at,
        updated_at=space.updated_at,
    )
    return out.model_dump(mode="json")


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a parking listing (owner)")
async def create_parking(
    payload: ParkingCreate,
    owner: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    space = await ParkingService(session).create(owner, payload)
    return ok(_serialize(space), message="Parking created, pending verification")


@router.get("/mine", summary="List parkings owned by current user")
async def my_parkings(
    owner: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    spaces = await ParkingService(session).list_mine(owner)
    return ok([_serialize(s) for s in spaces])


@router.get(
    "/mine/{parking_id}",
    summary="Get one parking listing owned by the current user (any status)",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Parking not found or not owned by the current user"},
    },
)
async def my_parking_detail(
    parking_id: UUID,
    owner: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    space = await ParkingService(session).get_owned(parking_id, owner)
    return ok(_serialize(space))





@router.get("", summary="Search verified parking listings")
async def search_parkings(
    city: str | None = Query(None),
    vehicle_type: VehicleType | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    amenity: Amenity | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    query = ParkingSearchQuery(
        city=city,
        vehicle_type=vehicle_type,
        min_price=min_price,
        max_price=max_price,
        amenity=amenity,
        page=page,
        page_size=page_size,
    )
    items, total = await ParkingService(session).search(query)
    body = ParkingListOut(
        items=[ParkingOut(**_serialize(s)) for s in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    return ok(body.model_dump(mode="json"))


@router.get("/{parking_id}", summary="Get a parking listing")
async def get_parking(
    parking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    space = await ParkingService(session).get_public(parking_id)
    return ok(_serialize(space))


@router.patch("/{parking_id}", summary="Update your parking listing (owner)")
async def update_parking(
    parking_id: UUID,
    payload: ParkingUpdate,
    owner: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    space = await ParkingService(session).update(parking_id, owner, payload)
    return ok(_serialize(space), message="Parking updated")


@router.delete(
    "/{parking_id}",
    summary="Delete your parking listing (owner)",
    status_code=status.HTTP_200_OK,
)
async def delete_parking(
    parking_id: UUID,
    owner: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ParkingService(session).delete(parking_id, owner)
    return ok(None, message="Parking deleted")


# Keep symbol referenced for potential future use
_ = get_current_user
