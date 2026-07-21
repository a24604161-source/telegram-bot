"""
Handle general messages sent outside of FSM states (not via Поддержка button).
These are forwarded to admins automatically.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import ADMIN_IDS
from database.db import add_message, create_ticket, register_user, update_user_activity
from keyboards.admin_kb import get_ticket_admin_keyboard
from utils.helpers import forward_any_message, get_message_info, now_str, profile_link, username_str

router = Router()
logger = logging.getLogger(__name__)


@router.message(StateFilter(None))
async def handle_general_message(message: Message, state: FSMContext, bot: Bot) -> None:
    user = message.from_user
    if user is None:
        return

    # Skip admins sending messages in no-state (e.g. typing in admin chat)
    if user.id in ADMIN_IDS:
        return

    # Skip commands (unrecognised ones fall through here)
    if message.text and message.text.startswith("/"):
        await message.answer(
            "Неизвестная команда. Используйте /menu для возврата в главное меню."
        )
        return

    await register_user(user.id, user.username, user.first_name, user.last_name)
    await update_user_activity(user.id)

    ticket_id = await create_ticket(user.id, "general")
    msg_type, content, file_id = get_message_info(message)
    await add_message(ticket_id, user.id, "user_to_admin", msg_type, content, file_id)

    await message.answer(
        "✅ <b>Ваше сообщение получено и передано модераторам.</b>\n\n"
        "Они смогут ответить вам через этого бота.",
        parse_mode="HTML",
    )

    header = (
        f"💬 <b>Сообщение от пользователя #{ticket_id}</b>\n\n"
        f"👤 <b>Имя:</b> {profile_link(user.id, user.first_name)}\n"
        f"📱 <b>Username:</b> {username_str(user.username)}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"🕐 <b>Дата:</b> {now_str()}\n\n"
        "📨 <b>Сообщение:</b>"
    )
    kb = get_ticket_admin_keyboard(ticket_id, user.id)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, header, parse_mode="HTML")
            await forward_any_message(bot, admin_id, message, reply_markup=kb)
        except Exception as e:
            logger.error("Failed to forward message to admin %s: %s", admin_id, e)
