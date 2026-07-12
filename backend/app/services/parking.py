from datetime import time as time_type
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parking import (
    ParkingAmenity,
    ParkingImage,
    ParkingSpace,
    ParkingStatus,
    ParkingVehicleType,
)
from app.models.user import User, UserRole
from app.repositories.parking import ParkingRepository
from app.schemas.parking import ParkingCreate, ParkingSearchQuery, ParkingUpdate


PIN_CODE_LENGTH = 6


def _validate_merged_parking_state(m: dict[str, Any]) -> None:
    """Validate a merged/candidate parking state before persisting a partial update.

    Raises HTTPException(400) with a descriptive message on failure.
    """
    total_slots = m["total_slots"]
    available_slots = m["available_slots"]
    hourly_price: Decimal = m["hourly_price"]
    daily_price: Decimal | None = m["daily_price"]
    latitude: float = float(m["latitude"])
    longitude: float = float(m["longitude"])
    pin_code: str = m["pin_code"]
    is_24x7: bool = bool(m["is_24x7"])
    opening_time: time_type | None = m["opening_time"]
    closing_time: time_type | None = m["closing_time"]

    if total_slots is None or total_slots <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "total_slots must be greater than 0")
    if available_slots is None or available_slots < 0 or available_slots > total_slots:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "available_slots must be between 0 and total_slots",
        )
    if hourly_price is None or Decimal(hourly_price) < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "hourly_price must be >= 0")
    if daily_price is not None and Decimal(daily_price) < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "daily_price must be >= 0")
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "longitude must be between -180 and 180")
    if not pin_code or not pin_code.isdigit() or len(pin_code) != PIN_CODE_LENGTH:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "PIN code must be exactly 6 digits")
    if not is_24x7:
        if opening_time is None or closing_time is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "opening_time and closing_time are required when not 24x7",
            )
        if opening_time >= closing_time:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "opening_time must be earlier than closing_time",
            )


class ParkingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ParkingRepository(session)

    async def create(self, owner: User, payload: ParkingCreate) -> ParkingSpace:
        if owner.role not in (UserRole.OWNER, UserRole.ADMIN):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners can create parking")

        space = ParkingSpace(
            owner_id=owner.id,
            name=payload.name.strip(),
            description=payload.description,
            property_type=payload.property_type,
            address=payload.address.strip(),
            city=payload.city.strip(),
            state=payload.state.strip(),
            pin_code=payload.pin_code,
            latitude=payload.latitude,
            longitude=payload.longitude,
            total_slots=payload.total_slots,
            available_slots=payload.available_slots or payload.total_slots,
            parking_type=payload.parking_type,
            hourly_price=payload.hourly_price,
            daily_price=payload.daily_price,
            is_24x7=payload.is_24x7,
            opening_time=payload.opening_time,
            closing_time=payload.closing_time,
            status=ParkingStatus.PENDING,
        )
        space.vehicle_types = [ParkingVehicleType(vehicle_type=v) for v in set(payload.vehicle_types)]
        space.amenities = [ParkingAmenity(amenity=a) for a in set(payload.amenities)]
        space.images = [
            ParkingImage(image_url=u, display_order=i)
            for i, u in enumerate(payload.image_urls)
        ]
        return await self.repo.add(space)

    async def list_mine(self, owner: User) -> list[ParkingSpace]:
        return await self.repo.list_by_owner(owner.id)

    async def get_public(self, parking_id: UUID) -> ParkingSpace:
        """Publicly visible detail lookup: only VERIFIED listings are exposed.

        Returns 404 for PENDING / REJECTED / INACTIVE listings to avoid leaking
        their existence.
        """
        space = await self.repo.get_public_verified(parking_id)
        if not space:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parking not found")
        return space

    async def get_owned(self, parking_id: UUID, owner: User) -> ParkingSpace:
        if owner.role == UserRole.ADMIN:
            space = await self.repo.get(parking_id)
        else:
            space = await self.repo.get_owned(parking_id, owner.id)
        if not space:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parking not found")
        return space

    async def update(self, parking_id: UUID, owner: User, payload: ParkingUpdate) -> ParkingSpace:
        space = await self.get_owned(parking_id, owner)
        data = payload.model_dump(exclude_unset=True)

        vt = data.pop("vehicle_types", None)
        am = data.pop("amenities", None)

        # Build merged candidate state without mutating the persisted entity.
        merged: dict[str, Any] = {
            "total_slots": space.total_slots,
            "available_slots": space.available_slots,
            "hourly_price": space.hourly_price,
            "daily_price": space.daily_price,
            "latitude": float(space.latitude),
            "longitude": float(space.longitude),
            "pin_code": space.pin_code,
            "is_24x7": space.is_24x7,
            "opening_time": space.opening_time,
            "closing_time": space.closing_time,
        }
        for k in list(merged.keys()):
            if k in data:
                merged[k] = data[k]

        # If the patch flips is_24x7 -> True and does not explicitly set times,
        # treat times as cleared for validation purposes.
        if data.get("is_24x7") is True:
            if "opening_time" not in data:
                merged["opening_time"] = None
            if "closing_time" not in data:
                merged["closing_time"] = None

        # Validate the merged candidate BEFORE mutating the persisted entity.
        _validate_merged_parking_state(merged)

        # Now safe to apply mutations.
        for k, v in data.items():
            setattr(space, k, v)
        if data.get("is_24x7") is True:
            if "opening_time" not in data:
                space.opening_time = None
            if "closing_time" not in data:
                space.closing_time = None

        if vt is not None:
            space.vehicle_types.clear()
            await self.session.flush()
            for v in set(vt):
                space.vehicle_types.append(ParkingVehicleType(vehicle_type=v))
        if am is not None:
            space.amenities.clear()
            await self.session.flush()
            for a in set(am):
                space.amenities.append(ParkingAmenity(amenity=a))

        return await self.repo.commit_refresh(space)

    async def delete(self, parking_id: UUID, owner: User) -> None:
        space = await self.get_owned(parking_id, owner)
        await self.repo.delete(space)

    async def search(self, query: ParkingSearchQuery) -> tuple[list[ParkingSpace], int]:
        return await self.repo.search(
            city=query.city,
            vehicle_type=query.vehicle_type,
            min_price=query.min_price,
            max_price=query.max_price,
            amenity=query.amenity,
            page=query.page,
            page_size=query.page_size,
        )

    # --- Admin verification workflow -------------------------------------

    async def list_pending(self) -> list[ParkingSpace]:
        """Return all parking listings awaiting admin verification."""
        return await self.repo.list_by_status(ParkingStatus.PENDING)

    async def _get_pending_or_error(self, parking_id: UUID) -> ParkingSpace:
        space = await self.repo.get(parking_id)
        if not space:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parking not found")
        if space.status != ParkingStatus.PENDING:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Parking is not pending verification (current status: {space.status.value})",
            )
        return space

    async def approve(self, parking_id: UUID) -> ParkingSpace:
        """Transition a PENDING parking listing to VERIFIED (admin only)."""
        space = await self._get_pending_or_error(parking_id)
        space.status = ParkingStatus.VERIFIED
        return await self.repo.commit_refresh(space)

    async def reject(self, parking_id: UUID) -> ParkingSpace:
        """Transition a PENDING parking listing to REJECTED (admin only)."""
        space = await self._get_pending_or_error(parking_id)
        space.status = ParkingStatus.REJECTED
        return await self.repo.commit_refresh(space)
