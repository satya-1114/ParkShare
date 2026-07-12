import enum
import uuid

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    DRIVER = "DRIVER"
    OWNER = "OWNER"
    ADMIN = "ADMIN"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.DRIVER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    id_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    parkings = relationship("ParkingSpace", back_populates="owner", cascade="all,delete")
    bookings = relationship("Booking", back_populates="driver", cascade="all,delete")
