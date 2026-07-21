import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import ADMIN_IDS, CHANNEL_URL
from database.db import add_message, create_ticket, update_user_activity
from keyboards.admin_kb import get_ticket_admin_keyboard
from keyboards.user_kb import get_cancel_keyboard, get_main_menu_keyboard
from states.states import SupportForm
from utils.helpers import forward_any_message, get_message_info, now_str, profile_link, username_str

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "open_support")
async def open_support(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(SupportForm.waiting_for_message)
    await callback.message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Опишите вашу проблему или задайте вопрос одним сообщением.\n\n"
        "Можно отправить текст, фотографию, видео, документ, "
        "голосовое сообщение или стикер.\n\n"
        "Модераторы проверят ваше сообщение и ответят вам через этого бота.\n\n"
        "Для отмены нажмите кнопку «❌ Отменить».",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(SupportForm.waiting_for_message))
async def handle_support_message(message: Message, state: FSMContext, bot: Bot) -> None:
    user = message.from_user
    await state.clear()
    await update_user_activity(user.id)

    ticket_id = await create_ticket(user.id, "support")
    msg_type, content, file_id = get_message_info(message)
    await add_message(ticket_id, user.id, "user_to_admin", msg_type, content, file_id)

    await message.answer(
        "✅ <b>Ваше сообщение передано модераторам.</b>\n\nОжидайте ответ через этого бота.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await message.answer(
        "Возврат в главное меню:",
        reply_markup=get_main_menu_keyboard(CHANNEL_URL),
        parse_mode="HTML",
    )

    header = (
        f"💬 <b>Обращение в поддержку #{ticket_id}</b>\n\n"
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
            logger.error("Failed to forward support msg to admin %s: %s", admin_id, e)
