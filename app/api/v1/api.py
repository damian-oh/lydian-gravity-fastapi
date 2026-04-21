from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, songs, suggestions, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(songs.router, prefix="/songs", tags=["songs"])
api_router.include_router(
    suggestions.router, prefix="/suggestions", tags=["suggestions"]
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
