from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.parking import ParkingSpace, ParkingStatus
from app.models.user import User, UserRole
from app.repositories.booking import BookingRepository
from app.repositories.parking import ParkingRepository
from app.schemas.booking import BookingCreate
from app.utils.reference import generate_booking_reference


def _q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Statuses that consume parking capacity for overlap calculations.
# CANCELLED and COMPLETED bookings do NOT consume capacity.
CAPACITY_CONSUMING_STATUSES: tuple[BookingStatus, ...] = (
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
)


def is_capacity_consuming(status_: BookingStatus) -> bool:
    return status_ in CAPACITY_CONSUMING_STATUSES


class BookingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BookingRepository(session)
        self.parkings = ParkingRepository(session)

    async def create(self, driver: User, payload: BookingCreate) -> Booking:
        if driver.role != UserRole.DRIVER:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only drivers can create bookings")

        now = datetime.now(timezone.utc)
        start = payload.start_time
        end = payload.end_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if start < now:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot book in the past")

        parking = await self.parkings.get(payload.parking_id)
        if not parking:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parking not found")
        if parking.status != ParkingStatus.VERIFIED:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parking not available")

        duration_minutes = int((end - start).total_seconds() // 60)
        if duration_minutes <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid duration")

        # Transactional capacity check with row-level lock to prevent races.
        async with self.session.begin_nested():
            locked: ParkingSpace | None = await self.session.get(
                ParkingSpace, parking.id, with_for_update=True
            )
            if not locked:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Parking not found")

            overlapping = await self.repo.count_overlapping_bookings(
                parking_id=locked.id,
                start_time=start,
                end_time=end,
                statuses=CAPACITY_CONSUMING_STATUSES,
            )
            # MVP: one booking consumes one slot.
            if overlapping >= locked.total_slots:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Parking is fully booked for the selected interval",
                )

            hours = Decimal(duration_minutes) / Decimal(60)
            total = _q2(hours * Decimal(locked.hourly_price))

            booking = Booking(
                driver_id=driver.id,
                parking_id=locked.id,
                booking_reference=generate_booking_reference(),
                booking_date=start,
                start_time=start,
                end_time=end,
                duration_minutes=duration_minutes,
                total_amount=total,
                status=BookingStatus.CONFIRMED,
            )
            self.session.add(booking)

        await self.session.commit()
        return await self.repo.get(booking.id)  # type: ignore[return-value]

    async def list_mine(self, driver: User) -> list[Booking]:
        return await self.repo.list_by_driver(driver.id)

    async def get_for_driver(self, booking_id: UUID, driver: User) -> Booking:
        booking = await self.repo.get(booking_id)
        if not booking or booking.driver_id != driver.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
        return booking

    async def cancel(self, booking_id: UUID, driver: User) -> Booking:
        booking = await self.get_for_driver(booking_id, driver)
        if booking.status in (BookingStatus.CANCELLED, BookingStatus.COMPLETED):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking cannot be cancelled")

        booking.status = BookingStatus.CANCELLED
        await self.session.commit()
        return await self.repo.get(booking.id)  # type: ignore[return-value]
