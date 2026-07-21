import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.db import is_blocked

logger = logging.getLogger(__name__)

_BAN_TEXT = "🚫 Доступ к боту ограничен администрацией."


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        # Admins are never blocked by this check
        if user.id in ADMIN_IDS:
            return await handler(event, data)

        try:
            blocked = await is_blocked(user.id)
        except Exception:
            blocked = False

        if blocked:
            try:
                if isinstance(event, Message):
                    await event.answer(_BAN_TEXT)
                elif isinstance(event, CallbackQuery):
                    await event.answer(_BAN_TEXT, show_alert=True)
            except Exception:
                pass
            return  # stop processing

        return await handler(event, data)
