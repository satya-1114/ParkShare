from datetime import time, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.parking import (
    Amenity,
    ParkingStatus,
    ParkingType,
    PropertyType,
    VehicleType,
)


PIN_CODE_LENGTH = 6


class ParkingImageOut(BaseModel):
    id: UUID
    image_url: str
    display_order: int

    model_config = {"from_attributes": True}


class ParkingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    property_type: PropertyType

    address: str = Field(min_length=3, max_length=500)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=120)
    pin_code: str = Field(min_length=6, max_length=6)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)

    total_slots: int = Field(gt=0, le=10000)
    available_slots: Optional[int] = Field(default=None, ge=0, le=10000)

    parking_type: ParkingType = ParkingType.OPEN

    hourly_price: Decimal = Field(ge=0)
    daily_price: Optional[Decimal] = Field(default=None, ge=0)

    is_24x7: bool = False
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None

    vehicle_types: List[VehicleType] = Field(default_factory=list)
    amenities: List[Amenity] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("pin_code")
    @classmethod
    def _pin(cls, v: str) -> str:
        if not v.isdigit() or len(v) != PIN_CODE_LENGTH:
            raise ValueError("PIN code must be exactly 6 digits")
        return v

    @model_validator(mode="after")
    def _validate(self):
        if self.available_slots is None:
            self.available_slots = self.total_slots
        if self.available_slots > self.total_slots:
            raise ValueError("available_slots cannot exceed total_slots")
        if not self.is_24x7:
            if self.opening_time is None or self.closing_time is None:
                raise ValueError("opening_time and closing_time are required when not 24x7")
            if self.opening_time >= self.closing_time:
                raise ValueError("opening_time must be earlier than closing_time")
        return self


class ParkingUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    property_type: Optional[PropertyType] = None
    address: Optional[str] = Field(default=None, min_length=3, max_length=500)
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    total_slots: Optional[int] = Field(default=None, gt=0, le=10000)
    available_slots: Optional[int] = Field(default=None, ge=0, le=10000)
    parking_type: Optional[ParkingType] = None
    hourly_price: Optional[Decimal] = Field(default=None, ge=0)
    daily_price: Optional[Decimal] = Field(default=None, ge=0)
    is_24x7: Optional[bool] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    vehicle_types: Optional[List[VehicleType]] = None
    amenities: Optional[List[Amenity]] = None

    @field_validator("pin_code")
    @classmethod
    def _pin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.isdigit() or len(v) != PIN_CODE_LENGTH:
            raise ValueError("PIN code must be exactly 6 digits")
        return v


class ParkingOut(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    description: Optional[str]
    property_type: PropertyType
    address: str
    city: str
    state: str
    pin_code: str
    latitude: float
    longitude: float
    total_slots: int
    available_slots: int
    parking_type: ParkingType
    hourly_price: Decimal
    daily_price: Optional[Decimal]
    is_24x7: bool
    opening_time: Optional[time]
    closing_time: Optional[time]
    status: ParkingStatus
    vehicle_types: List[VehicleType] = Field(default_factory=list)
    amenities: List[Amenity] = Field(default_factory=list)
    images: List[ParkingImageOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ParkingSearchQuery(BaseModel):
    city: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    min_price: Optional[Decimal] = Field(default=None, ge=0)
    max_price: Optional[Decimal] = Field(default=None, ge=0)
    amenity: Optional[Amenity] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ParkingListOut(BaseModel):
    items: List[ParkingOut]
    page: int
    page_size: int
    total: int
