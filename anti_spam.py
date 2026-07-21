import time
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from config import ADMIN_IDS, SPAM_LIMIT, SPAM_WINDOW

logger = logging.getLogger(__name__)


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._history: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        if user is None:
            return await handler(event, data)

        # Admins are exempt from spam protection
        if user.id in ADMIN_IDS:
            return await handler(event, data)

        now = time.monotonic()
        self._history[user.id] = [
            t for t in self._history[user.id] if now - t < SPAM_WINDOW
        ]

        if len(self._history[user.id]) >= SPAM_LIMIT:
            logger.warning("Spam detected from user %s", user.id)
            try:
                await event.answer(
                    "⏳ Вы отправляете сообщения слишком быстро. "
                    "Подождите немного и попробуйте снова."
                )
            except Exception:
                pass
            return  # drop message

        self._history[user.id].append(now)
        return await handler(event, data)
