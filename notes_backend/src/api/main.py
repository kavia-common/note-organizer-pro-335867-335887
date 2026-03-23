from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.errors import AppError, app_error_handler
from src.api.routers import auth_router, notes_router, search_router, shares_router, tags_router
from src.core.config import get_settings
from src.db.session import init_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)

openapi_tags = [
    {"name": "meta", "description": "Health and service metadata."},
    {"name": "notes", "description": "CRUD for notes, pin/favorite, and soft-delete."},
    {"name": "tags", "description": "CRUD for tags."},
    {"name": "search", "description": "Full-text search endpoints."},
    {"name": "sharing", "description": "Sharing endpoints for notes."},
    {"name": "auth", "description": "Optional authentication endpoints (JWT)."},
]

app = FastAPI(
    title="Notes Backend API",
    description=(
        "REST API for a notes application (notes, tags, pin/favorite, full-text search, sharing, sync).\n\n"
        "Auth is optional and controlled via AUTH_ENABLED.\n"
        "If auth is disabled, resources are stored with user_id = NULL."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

settings = get_settings()
init_engine(settings)

app.add_exception_handler(AppError, app_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes_router)
app.include_router(tags_router)
app.include_router(search_router)
app.include_router(shares_router)
app.include_router(auth_router)


@app.get(
    "/",
    tags=["meta"],
    summary="Health check",
    description="Returns a simple health status payload.",
    operation_id="healthCheck",
)
def health_check() -> dict:
    """Health check endpoint."""
    return {"message": "Healthy"}
