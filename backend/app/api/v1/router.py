from fastapi import APIRouter

from app.ai.router import router as ai_router
from app.api.v1 import admin, auth, bookings, health, parkings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(parkings.router)
api_router.include_router(bookings.router)
api_router.include_router(admin.router)
api_router.include_router(ai_router)
