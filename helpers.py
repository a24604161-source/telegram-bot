import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)


def now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def username_str(username: str | None) -> str:
    return f"@{username}" if username else "—"


def profile_link(user_id: int, first_name: str | None) -> str:
    name = first_name or f"Пользователь {user_id}"
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def get_message_info(message: Message) -> tuple[str, str | None, str | None]:
    """Returns (type, text_content, file_id)."""
    if message.photo:
        return "photo", message.caption, message.photo[-1].file_id
    if message.video:
        return "video", message.caption, message.video.file_id
    if message.document:
        return "document", message.caption, message.document.file_id
    if message.voice:
        return "voice", None, message.voice.file_id
    if message.sticker:
        return "sticker", None, message.sticker.file_id
    if message.animation:
        return "animation", message.caption, message.animation.file_id
    if message.text:
        return "text", message.text, None
    return "unknown", None, None


async def forward_any_message(
    bot: Bot,
    chat_id: int,
    message: Message,
    reply_markup=None,
) -> bool:
    """Forward any message type to a chat. Returns True on success."""
    try:
        if message.sticker:
            await bot.send_sticker(chat_id, message.sticker.file_id, reply_markup=reply_markup)
        elif message.photo:
            await bot.send_photo(
                chat_id, message.photo[-1].file_id,
                caption=message.caption, reply_markup=reply_markup,
            )
        elif message.video:
            await bot.send_video(
                chat_id, message.video.file_id,
                caption=message.caption, reply_markup=reply_markup,
            )
        elif message.document:
            await bot.send_document(
                chat_id, message.document.file_id,
                caption=message.caption, reply_markup=reply_markup,
            )
        elif message.voice:
            await bot.send_voice(
                chat_id, message.voice.file_id,
                reply_markup=reply_markup,
            )
        elif message.animation:
            await bot.send_animation(
                chat_id, message.animation.file_id,
                caption=message.caption, reply_markup=reply_markup,
            )
        elif message.text:
            await bot.send_message(chat_id, message.text, reply_markup=reply_markup)
        else:
            return False
        return True
    except Exception as exc:
        logger.error("Failed to forward to %s: %s", chat_id, exc)
        return False


async def send_reply_to_user(bot: Bot, user_id: int, message: Message) -> bool:
    """Send admin reply to user with 'Ответ от поддержки' prefix."""
    prefix = "💬 <b>Ответ от поддержки:</b>\n\n"
    try:
        if message.sticker:
            await bot.send_message(user_id, prefix, parse_mode="HTML")
            await bot.send_sticker(user_id, message.sticker.file_id)
        elif message.photo:
            caption = prefix + (message.caption or "")
            await bot.send_photo(
                user_id, message.photo[-1].file_id,
                caption=caption, parse_mode="HTML",
            )
        elif message.video:
            caption = prefix + (message.caption or "")
            await bot.send_video(
                user_id, message.video.file_id,
                caption=caption, parse_mode="HTML",
            )
        elif message.document:
            caption = prefix + (message.caption or "")
            await bot.send_document(
                user_id, message.document.file_id,
                caption=caption, parse_mode="HTML",
            )
        elif message.voice:
            await bot.send_message(user_id, prefix, parse_mode="HTML")
            await bot.send_voice(user_id, message.voice.file_id)
        elif message.text:
            await bot.send_message(user_id, prefix + message.text, parse_mode="HTML")
        else:
            return False
        return True
    except Exception as exc:
        logger.error("Failed to send reply to user %s: %s", user_id, exc)
        return False
