from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, recommendations, reviews, trips

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(trips.router)
api_router.include_router(chat.router)
api_router.include_router(recommendations.router)
api_router.include_router(reviews.router)