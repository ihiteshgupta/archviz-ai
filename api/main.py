"""ArchViz AI FastAPI Application"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
load_dotenv()  # Load .env file

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .routes import projects, render, materials, health, chat, notifications

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded-Proto for HTTPS redirects behind a reverse proxy."""

    async def dispatch(self, request: Request, call_next):
        # Trust the X-Forwarded-Proto header from Azure Container Apps
        if request.headers.get("x-forwarded-proto") == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler."""
    logger.info("Starting ArchViz AI API...")
    yield
    logger.info("Shutting down ArchViz AI API...")


app = FastAPI(
    title="ArchViz AI",
    description="AI-powered architectural visualization API",
    version="0.1.0",
    lifespan=lifespan,
)

# Proxy headers middleware (must be added first)
app.add_middleware(ProxyHeadersMiddleware)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://archviz-frontend.gentleground-d7f4772e.eastus.azurecontainerapps.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(render.router, prefix="/api/render", tags=["Render"])
app.include_router(materials.router, prefix="/api/materials", tags=["Materials"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])

# Serve static files (uploads and outputs)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ArchViz AI",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }
