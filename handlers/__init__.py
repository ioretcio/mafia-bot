from .start import router as start_router
from .profile import router as profile_router
from .events import router as events_router
from .settings import router as settings_router

__all__ = [
    "start_router",
    "profile_router",
    "events_router",
    "settings_router"
]