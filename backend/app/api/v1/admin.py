from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.parkings import _serialize
from app.core.responses import ok
from app.database.session import get_session
from app.dependencies.auth import require_admin
from app.models.user import User
from app.services.parking import ParkingService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/parkings/pending",
    summary="List parking listings awaiting verification (admin)",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
    },
)
async def list_pending_parkings(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    spaces = await ParkingService(session).list_pending()
    return ok([_serialize(s) for s in spaces])


@router.patch(
    "/parkings/{parking_id}/approve",
    summary="Approve a pending parking listing (admin)",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Parking not found"},
        409: {"description": "Parking is not pending verification"},
    },
)
async def approve_parking(
    parking_id: UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    space = await ParkingService(session).approve(parking_id)
    return ok(_serialize(space), message="Parking approved and verified")


@router.patch(
    "/parkings/{parking_id}/reject",
    summary="Reject a pending parking listing (admin)",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Parking not found"},
        409: {"description": "Parking is not pending verification"},
    },
)
async def reject_parking(
    parking_id: UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    space = await ParkingService(session).reject(parking_id)
    return ok(_serialize(space), message="Parking rejected")
