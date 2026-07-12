from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ok
from app.database.session import get_session
from app.dependencies.auth import require_driver
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingListOut, BookingOut
from app.services.booking import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def _serialize(b: Booking) -> dict:
    return BookingOut(
        id=b.id,
        driver_id=b.driver_id,
        parking_id=b.parking_id,
        booking_reference=b.booking_reference,
        booking_date=b.booking_date,
        start_time=b.start_time,
        end_time=b.end_time,
        duration_minutes=b.duration_minutes,
        total_amount=b.total_amount,
        status=b.status,
        parking_name=b.parking.name if b.parking else "",
        parking_city=b.parking.city if b.parking else "",
    ).model_dump(mode="json")


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a booking (driver)")
async def create_booking(
    payload: BookingCreate,
    driver: User = Depends(require_driver),
    session: AsyncSession = Depends(get_session),
) -> dict:
    booking = await BookingService(session).create(driver, payload)
    return ok(_serialize(booking), message="Booking confirmed")


@router.get("/mine", summary="List current driver's bookings")
async def list_my_bookings(
    driver: User = Depends(require_driver),
    session: AsyncSession = Depends(get_session),
) -> dict:
    items = await BookingService(session).list_mine(driver)
    body = BookingListOut(items=[BookingOut(**_serialize(b)) for b in items])
    return ok(body.model_dump(mode="json"))


@router.get("/{booking_id}", summary="Get a specific booking")
async def get_booking(
    booking_id: UUID,
    driver: User = Depends(require_driver),
    session: AsyncSession = Depends(get_session),
) -> dict:
    booking = await BookingService(session).get_for_driver(booking_id, driver)
    return ok(_serialize(booking))


@router.patch("/{booking_id}/cancel", summary="Cancel a booking")
async def cancel_booking(
    booking_id: UUID,
    driver: User = Depends(require_driver),
    session: AsyncSession = Depends(get_session),
) -> dict:
    booking = await BookingService(session).cancel(booking_id, driver)
    return ok(_serialize(booking), message="Booking cancelled")
