from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, booking_id: UUID) -> Booking | None:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.parking))
            .where(Booking.id == booking_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_by_driver(self, driver_id: UUID) -> list[Booking]:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.parking))
            .where(Booking.driver_id == driver_id)
            .order_by(Booking.start_time.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def add(self, booking: Booking) -> Booking:
        self.session.add(booking)
        return booking

    async def count_overlapping_bookings(
        self,
        parking_id: UUID,
        start_time: datetime,
        end_time: datetime,
        statuses: Iterable[BookingStatus],
    ) -> int:
        """Count bookings for a parking space whose interval overlaps [start_time, end_time).

        Two intervals overlap when: existing.start_time < requested.end_time
        AND existing.end_time > requested.start_time.
        Back-to-back bookings (existing.end_time == requested.start_time) do NOT overlap.
        Only bookings in one of ``statuses`` are counted.
        """
        status_list = list(statuses)
        stmt = (
            select(func.count(Booking.id))
            .where(Booking.parking_id == parking_id)
            .where(Booking.status.in_(status_list))
            .where(Booking.start_time < end_time)
            .where(Booking.end_time > start_time)
        )
        return int((await self.session.execute(stmt)).scalar_one())
