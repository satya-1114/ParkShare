from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    parking_id: UUID
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def _times(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class BookingOut(BaseModel):
    id: UUID
    driver_id: UUID
    parking_id: UUID
    booking_reference: str
    booking_date: datetime
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    total_amount: Decimal
    status: BookingStatus
    parking_name: str = Field(default="")
    parking_city: str = Field(default="")

    model_config = {"from_attributes": True}


class BookingListOut(BaseModel):
    items: List[BookingOut]
