from src.api.routers.auth import router as auth_router
from src.api.routers.notes import router as notes_router
from src.api.routers.search import router as search_router
from src.api.routers.shares import router as shares_router
from src.api.routers.tags import router as tags_router

__all__ = [
    "auth_router",
    "notes_router",
    "tags_router",
    "search_router",
    "shares_router",
]
