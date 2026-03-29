from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)


@app.get("/")
async def root():
    return {
        "message": "Lydian Gravity FastAPI is online",
        "project": settings.PROJECT_NAME,
    }
