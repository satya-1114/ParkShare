from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.parking import (
    Amenity,
    ParkingAmenity,
    ParkingSpace,
    ParkingStatus,
    ParkingVehicleType,
    VehicleType,
)


class ParkingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_relations(self, stmt, *, include_owner: bool = False):
        stmt = stmt.options(
            selectinload(ParkingSpace.vehicle_types),
            selectinload(ParkingSpace.amenities),
            selectinload(ParkingSpace.images),
        )
        if include_owner:
            from app.models.user import User  # local import to avoid circular
            stmt = stmt.options(selectinload(ParkingSpace.owner))
        return stmt

    async def get(self, parking_id: UUID) -> ParkingSpace | None:
        stmt = self._with_relations(select(ParkingSpace).where(ParkingSpace.id == parking_id))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_public_verified(self, parking_id: UUID) -> ParkingSpace | None:
        """Return a parking space only if it is publicly visible (VERIFIED)."""
        stmt = self._with_relations(
            select(ParkingSpace).where(
                ParkingSpace.id == parking_id,
                ParkingSpace.status == ParkingStatus.VERIFIED,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_owned(self, parking_id: UUID, owner_id: UUID) -> ParkingSpace | None:
        stmt = self._with_relations(
            select(ParkingSpace).where(
                ParkingSpace.id == parking_id,
                ParkingSpace.owner_id == owner_id,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_by_owner(self, owner_id: UUID) -> list[ParkingSpace]:
        stmt = self._with_relations(
            select(ParkingSpace)
            .where(ParkingSpace.owner_id == owner_id)
            .order_by(ParkingSpace.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_status(self, status: ParkingStatus) -> list[ParkingSpace]:
        stmt = self._with_relations(
            select(ParkingSpace)
            .where(ParkingSpace.status == status)
            .order_by(ParkingSpace.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())



    async def add(self, space: ParkingSpace) -> ParkingSpace:
        self.session.add(space)
        await self.session.commit()
        return await self.get(space.id)  # type: ignore[return-value]

    async def delete(self, space: ParkingSpace) -> None:
        await self.session.delete(space)
        await self.session.commit()

    async def commit_refresh(self, space: ParkingSpace) -> ParkingSpace:
        await self.session.commit()
        return await self.get(space.id)  # type: ignore[return-value]

    async def search(
        self,
        *,
        city: Optional[str] = None,
        vehicle_type: Optional[VehicleType] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        amenity: Optional[Amenity] = None,
        page: int = 1,
        page_size: int = 20,
        include_owner: bool = False,
    ) -> tuple[list[ParkingSpace], int]:
        stmt = select(ParkingSpace).where(ParkingSpace.status == ParkingStatus.VERIFIED)

        if city:
            stmt = stmt.where(func.lower(ParkingSpace.city) == city.lower())
        if min_price is not None:
            stmt = stmt.where(ParkingSpace.hourly_price >= min_price)
        if max_price is not None:
            stmt = stmt.where(ParkingSpace.hourly_price <= max_price)
        # NOTE: Real-time availability is time-interval based (see booking
        # repository). The legacy `available_slots` column is non-authoritative
        # and MUST NOT be used as a search-time availability filter. To filter
        # by availability, the search API needs to accept a requested
        # start/end time and perform overlap counting — not implemented yet.
        if vehicle_type is not None:
            stmt = stmt.join(ParkingVehicleType).where(ParkingVehicleType.vehicle_type == vehicle_type)
        if amenity is not None:
            stmt = stmt.join(ParkingAmenity).where(ParkingAmenity.amenity == amenity)

        stmt = stmt.distinct()

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = self._with_relations(
            stmt.order_by(ParkingSpace.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size),
            include_owner=include_owner,
        )
        items = list((await self.session.execute(stmt)).scalars().unique().all())
        return items, int(total)
