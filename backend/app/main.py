import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.api import api_router
from app.core.config import parse_cors_origins, settings
from app.core.init_db import init_db

init_db()

app = FastAPI(title="AI Private Tutor Backend", version="3.0")

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(settings.BACKEND_CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {
        "status": "running",
        "message": "AI Private Tutor backend service is running.",
        "version": "3.0",
    }
