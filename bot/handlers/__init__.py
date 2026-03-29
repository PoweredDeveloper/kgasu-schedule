from aiogram import Router

from . import menu as menu_router
from . import messages as messages_router
from . import start as start_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(start_router.router)
    root.include_router(menu_router.router)
    root.include_router(messages_router.router)
    return root
