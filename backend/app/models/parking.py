import enum
import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class ParkingStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    INACTIVE = "INACTIVE"


class ParkingType(str, enum.Enum):
    COVERED = "COVERED"
    OPEN = "OPEN"


class PropertyType(str, enum.Enum):
    INDIVIDUAL_HOUSE = "INDIVIDUAL_HOUSE"
    APARTMENT = "APARTMENT"
    COMMERCIAL_BUILDING = "COMMERCIAL_BUILDING"
    HOTEL = "HOTEL"
    OFFICE = "OFFICE"
    EMPTY_LAND = "EMPTY_LAND"


class VehicleType(str, enum.Enum):
    BIKE = "BIKE"
    CAR = "CAR"
    EV = "EV"
    TRUCK = "TRUCK"
    BICYCLE = "BICYCLE"


class Amenity(str, enum.Enum):
    CCTV = "CCTV"
    COVERED = "COVERED"
    SECURITY = "SECURITY"
    EV_CHARGING = "EV_CHARGING"
    ACCESS_24X7 = "ACCESS_24X7"


class ParkingSpace(Base, TimestampMixin):
    __tablename__ = "parking_spaces"
    __table_args__ = (
        Index("ix_parking_status_city", "status", "city"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType, name="property_type"), nullable=False
    )

    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    pin_code: Mapped[str] = mapped_column(String(10), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)

    total_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    available_slots: Mapped[int] = mapped_column(Integer, nullable=False)

    parking_type: Mapped[ParkingType] = mapped_column(
        Enum(ParkingType, name="parking_type"), nullable=False, default=ParkingType.OPEN
    )

    hourly_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    daily_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    is_24x7: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opening_time = mapped_column(Time, nullable=True)
    closing_time = mapped_column(Time, nullable=True)
    photos_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[ParkingStatus] = mapped_column(
        Enum(ParkingStatus, name="parking_status"),
        nullable=False,
        default=ParkingStatus.PENDING,
        index=True,
    )

    owner = relationship("User", back_populates="parkings")
    vehicle_types = relationship(
        "ParkingVehicleType", back_populates="parking", cascade="all,delete-orphan"
    )
    amenities = relationship(
        "ParkingAmenity", back_populates="parking", cascade="all,delete-orphan"
    )
    images = relationship(
        "ParkingImage", back_populates="parking", cascade="all,delete-orphan",
        order_by="ParkingImage.display_order",
    )
    bookings = relationship("Booking", back_populates="parking", cascade="all,delete")


class ParkingVehicleType(Base):
    __tablename__ = "parking_vehicle_types"
    __table_args__ = (
        UniqueConstraint("parking_id", "vehicle_type", name="uq_parking_vehicle"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_spaces.id", ondelete="CASCADE"), nullable=False
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(Enum(VehicleType, name="vehicle_type"), nullable=False)

    parking = relationship("ParkingSpace", back_populates="vehicle_types")


class ParkingAmenity(Base):
    __tablename__ = "parking_amenities"
    __table_args__ = (
        UniqueConstraint("parking_id", "amenity", name="uq_parking_amenity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_spaces.id", ondelete="CASCADE"), nullable=False
    )
    amenity: Mapped[Amenity] = mapped_column(Enum(Amenity, name="amenity"), nullable=False)

    parking = relationship("ParkingSpace", back_populates="amenities")


class ParkingImage(Base):
    __tablename__ = "parking_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    from datetime import datetime as _dt
    from sqlalchemy import DateTime, func
    created_at: Mapped[_dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    parking = relationship("ParkingSpace", back_populates="images")
