import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import CHANNEL_URL
from database.db import register_user, update_user_activity
from keyboards.user_kb import get_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "<b>// ФРИЗИ //</b>\n\n"
    "Приветаа 👋\n\n"
    "Набор у нас открыт, людей набираем массово!\n\n"
    "Чтобы попасть к нам, необходимо заполнить анкету.\n\n"
    "<b>ПРИМЕР АНКЕТЫ:</b>\n\n"
    "1. Ваше имя или псевдоним\n"
    "2. Возраст — принимаем от 10 лет\n"
    "3. Никнейм в Roblox\n"
    "4. Насколько вы активны?\n"
    "5. Скриншот аккаунта в TikTok\n"
    "6. Скриншот вашего скина в Roblox\n\n"
    "<i>Важно: беконы не принимаются.</i>\n\n"
    "Если вы прошли отбор, вам напишет владелец или администратор "
    "и отправит ссылку на хаус.\n\n"
    "Если в течение 24 часов вам не отправили ссылку, значит, анкета не была принята."
)

INFO_TEXT = (
    "ℹ️ <b>Информация о наборе</b>\n\n"
    "• Минимальный возраст: 10 лет\n"
    "• Для участия необходимо иметь аккаунт Roblox\n"
    "• Необходимо отправить скрин TikTok и скрин скина\n"
    "• Беконы не принимаются\n"
    "• Ответ по анкете может занять до 24 часов\n"
    f'• Официальный канал: <a href="{CHANNEL_URL}">{CHANNEL_URL}</a>\n\n'
    "Если у вас остались вопросы, нажмите кнопку «Поддержка»."
)

HELP_TEXT = (
    "ℹ️ <b>Помощь</b>\n\n"
    "<b>Доступные команды:</b>\n\n"
    "/start — главное меню\n"
    "/menu — вернуться в главное меню\n"
    "/cancel — отменить текущее действие\n"
    "/help — эта справка\n\n"
    "<b>Что можно делать в боте:</b>\n\n"
    "📝 <b>Заполнить анкету</b> — подайте заявку на вступление в команду ФРИЗИ\n"
    "💬 <b>Поддержка</b> — задайте вопрос или сообщите о проблеме\n"
    "📢 <b>Наш канал</b> — перейдите на официальный канал\n"
    "ℹ️ <b>Информация</b> — подробности о наборе"
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    u = message.from_user
    await register_user(u.id, u.username, u.first_name, u.last_name)
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu_keyboard(CHANNEL_URL),
        parse_mode="HTML",
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await update_user_activity(message.from_user.id)
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu_keyboard(CHANNEL_URL),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await update_user_activity(message.from_user.id)
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current is None:
        await message.answer(
            "Нет активных действий для отмены.",
            reply_markup=get_main_menu_keyboard(CHANNEL_URL),
            parse_mode="HTML",
        )
        return
    await message.answer("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu_keyboard(CHANNEL_URL),
        parse_mode="HTML",
    )


# Cancel reply-keyboard button — must be registered BEFORE FSM handlers
@router.message(F.text == "❌ Отменить")
async def cancel_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu_keyboard(CHANNEL_URL),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "show_info")
async def show_info(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(INFO_TEXT, parse_mode="HTML")
