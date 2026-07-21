import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import ADMIN_IDS, CHANNEL_URL
from database.db import create_application, has_pending_application, update_user_activity
from keyboards.admin_kb import get_application_admin_keyboard
from keyboards.user_kb import (
    get_application_preview_keyboard,
    get_cancel_keyboard,
    get_main_menu_keyboard,
)
from states.states import ApplicationForm
from utils.helpers import now_str, profile_link, username_str

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "fill_application")
async def start_application(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    await update_user_activity(user_id)

    if await has_pending_application(user_id):
        await callback.message.answer(
            "⏳ <b>У вас уже есть анкета на рассмотрении.</b>\n\n"
            "Пожалуйста, дождитесь ответа администрации.\n"
            "Повторно подать анкету можно через 24 часа.",
            parse_mode="HTML",
        )
        return

    await state.set_state(ApplicationForm.name)
    await callback.message.answer(
        "📝 <b>Заполнение анкеты</b>\n\n"
        "<b>Шаг 1 из 6</b>\n\n"
        "Как вас зовут или какой у вас псевдоним?",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 1: имя ──────────────────────────────────────────────────────────────

@router.message(StateFilter(ApplicationForm.name))
async def process_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(
            "Пожалуйста, введите ваше имя текстом.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(ApplicationForm.age)
    await message.answer(
        "<b>Шаг 2 из 6</b>\n\nСколько вам лет?",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 2: возраст ──────────────────────────────────────────────────────────

@router.message(StateFilter(ApplicationForm.age))
async def process_age(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer(
            "❌ Возраст должен быть числом. Попробуйте ещё раз.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    age = int(message.text.strip())
    if age < 10:
        await state.clear()
        await message.answer(
            "❌ <b>К сожалению, мы принимаем участников от 10 лет.</b>\n\n"
            "Вы не можете подать анкету.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )
        await message.answer(
            WELCOME_TEXT_SHORT,
            reply_markup=get_main_menu_keyboard(CHANNEL_URL),
            parse_mode="HTML",
        )
        return
    if age > 100:
        await message.answer(
            "Пожалуйста, введите реальный возраст.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(age=age)
    await state.set_state(ApplicationForm.roblox_nick)
    await message.answer(
        "<b>Шаг 3 из 6</b>\n\nНапишите ваш никнейм в Roblox.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 3: никнейм Roblox ───────────────────────────────────────────────────

@router.message(StateFilter(ApplicationForm.roblox_nick))
async def process_roblox_nick(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(
            "Пожалуйста, введите никнейм текстом.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    await state.update_data(roblox_nick=message.text.strip())
    await state.set_state(ApplicationForm.activity)
    await message.answer(
        "<b>Шаг 4 из 6</b>\n\n"
        "Насколько вы активны?\n\n"
        "<i>Например: каждый день, несколько раз в неделю или редко.</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 4: активность ───────────────────────────────────────────────────────

@router.message(StateFilter(ApplicationForm.activity))
async def process_activity(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(
            "Пожалуйста, опишите активность текстом.",
            reply_markup=get_cancel_keyboard(),
        )
        return
    await state.update_data(activity=message.text.strip())
    await state.set_state(ApplicationForm.tiktok_photo)
    await message.answer(
        "<b>Шаг 5 из 6</b>\n\n"
        "Отправьте скриншот вашего аккаунта в TikTok.\n\n"
        "<i>Принимаются только фотографии.</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 5: скрин TikTok ─────────────────────────────────────────────────────

@router.message(StateFilter(ApplicationForm.tiktok_photo))
async def process_tiktok_photo(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer(
            "❌ Пожалуйста, отправьте именно <b>фотографию</b> скриншота TikTok.\n"
            "<i>Другие типы файлов не принимаются.</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        return
    await state.update_data(tiktok_photo_id=message.photo[-1].file_id)
    await state.set_state(ApplicationForm.roblox_photo)
    await message.answer(
        "<b>Шаг 6 из 6</b>\n\n"
        "Отправьте скриншот вашего скина в Roblox.\n\n"
        "<i>Принимаются только фотографии.</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 6: скрин скина ──────────────────────────────────────────────────────

@router.message(StateFilter(ApplicationForm.roblox_photo))
async def process_roblox_photo(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer(
            "❌ Пожалуйста, отправьте именно <b>фотографию</b> скриншота скина.\n"
            "<i>Другие типы файлов не принимаются.</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        return
    await state.update_data(roblox_photo_id=message.photo[-1].file_id)
    await state.set_state(ApplicationForm.preview)

    data = await state.get_data()
    preview = (
        "📋 <b>Предварительный просмотр анкеты</b>\n\n"
        f"1. <b>Имя/псевдоним:</b> {data['name']}\n"
        f"2. <b>Возраст:</b> {data['age']}\n"
        f"3. <b>Никнейм Roblox:</b> {data['roblox_nick']}\n"
        f"4. <b>Активность:</b> {data['activity']}\n"
        "5. <b>Скриншот TikTok:</b> ✅ прикреплён\n"
        "6. <b>Скриншот скина:</b> ✅ прикреплён\n\n"
        "Проверьте данные и выберите действие."
    )
    await message.answer(preview, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await message.answer("Выберите действие:", reply_markup=get_application_preview_keyboard())


# ─── Отправить ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "app_submit", StateFilter(ApplicationForm.preview))
async def submit_application(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    data = await state.get_data()
    user = callback.from_user

    app_id = await create_application(
        user_id=user.id,
        name=data["name"],
        age=data["age"],
        roblox_nick=data["roblox_nick"],
        activity=data["activity"],
        tiktok_photo_id=data["tiktok_photo_id"],
        roblox_photo_id=data["roblox_photo_id"],
    )
    await state.clear()

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        "✅ <b>Ваша анкета успешно отправлена!</b>\n\n"
        "Администрация рассмотрит её в ближайшее время.\n\n"
        "Если вы подойдёте, владелец или администратор напишет вам и отправит ссылку на хаус.\n\n"
        "Если в течение 24 часов вам не написали, значит, анкета не была принята.",
        reply_markup=get_main_menu_keyboard(CHANNEL_URL),
        parse_mode="HTML",
    )

    # ─── Уведомление администраторов ────────────────────────────────────────
    admin_text = (
        f"📝 <b>Новая анкета #{app_id}</b>\n\n"
        f"👤 <b>Имя/псевдоним:</b> {data['name']}\n"
        f"🎂 <b>Возраст:</b> {data['age']}\n"
        f"🎮 <b>Никнейм Roblox:</b> {data['roblox_nick']}\n"
        f"⚡ <b>Активность:</b> {data['activity']}\n\n"
        f"📱 <b>Username:</b> {username_str(user.username)}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"🔗 <b>Профиль:</b> {profile_link(user.id, user.first_name)}\n"
        f"🕐 <b>Дата подачи:</b> {now_str()}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
            await bot.send_photo(admin_id, data["tiktok_photo_id"], caption="📸 Скриншот TikTok")
            await bot.send_photo(
                admin_id,
                data["roblox_photo_id"],
                caption="🎮 Скриншот скина Roblox",
                reply_markup=get_application_admin_keyboard(app_id, user.id),
            )
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", admin_id, e)


# ─── Заново ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "app_restart", StateFilter(ApplicationForm.preview))
async def restart_application(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(ApplicationForm.name)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "📝 <b>Начинаем заново.</b>\n\n"
        "<b>Шаг 1 из 6</b>\n\n"
        "Как вас зовут или какой у вас псевдоним?",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Отменить (inline) ───────────────────────────────────────────────────────

@router.callback_query(F.data == "app_cancel")
async def cancel_application_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "❌ Заполнение анкеты отменено.",
        reply_markup=get_main_menu_keyboard(CHANNEL_URL),
        parse_mode="HTML",
    )


# Short welcome used when user is rejected by age
WELCOME_TEXT_SHORT = (
    "Вернитесь в главное меню, когда будете готовы."
)
