import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import ADMIN_IDS
from database.db import (
    add_message,
    block_user,
    close_ticket,
    get_all_user_ids,
    get_all_users,
    get_blocked_users,
    get_open_tickets,
    get_pending_applications,
    get_stats,
    log_admin_action,
    unblock_user,
    update_application_status,
)
from keyboards.admin_kb import (
    get_admin_panel_keyboard,
    get_back_to_admin_keyboard,
    get_broadcast_confirm_keyboard,
    get_ticket_admin_keyboard,
)
from keyboards.user_kb import get_cancel_keyboard
from states.states import AdminBroadcast, AdminReply, AdminWriteToUser
from utils.helpers import get_message_info, now_str, send_reply_to_user

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── /admin команда ──────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "⚙️ <b>Административная панель</b>\n\nВыберите раздел:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(
            "⚙️ <b>Административная панель</b>\n\nВыберите раздел:",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "⚙️ <b>Административная панель</b>\n\nВыберите раздел:",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode="HTML",
        )


# ─── Статистика ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    s = await get_stats()
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {s['total_users']}\n"
        f"🆕 <b>Новых сегодня:</b> {s['new_users_today']}\n\n"
        f"📝 <b>Всего анкет:</b> {s['total_applications']}\n"
        f"✅ <b>Принято:</b> {s['accepted_applications']}\n"
        f"❌ <b>Отклонено:</b> {s['rejected_applications']}\n\n"
        f"💬 <b>Открытых обращений:</b> {s['open_tickets']}\n"
        f"🚫 <b>Заблокировано:</b> {s['blocked_users']}"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )


# ─── Новые анкеты ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_applications")
async def cb_applications(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    apps = await get_pending_applications()
    if not apps:
        text = "📝 <b>Новые анкеты</b>\n\nПока нет новых анкет."
    else:
        lines = [f"📝 <b>Новые анкеты</b>\n\nВ очереди: {len(apps)}\n"]
        for a in apps[:15]:
            lines.append(
                f"• Анкета <b>#{a['id']}</b> — пользователь <code>{a['user_id']}</code>"
                f" ({a['created_at'][:16]})"
            )
        text = "\n".join(lines)
        text += "\n\n<i>Анкеты отправлены вам в предыдущих сообщениях.</i>"
    try:
        await callback.message.edit_text(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )


# ─── Открытые обращения ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_tickets")
async def cb_tickets(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    tickets = await get_open_tickets()
    if not tickets:
        text = "💬 <b>Открытые обращения</b>\n\nПока нет открытых обращений."
    else:
        lines = [f"💬 <b>Открытые обращения</b>\n\nВсего: {len(tickets)}\n"]
        for t in tickets[:15]:
            lines.append(
                f"• Обращение <b>#{t['id']}</b> — пользователь <code>{t['user_id']}</code>"
                f" ({t['created_at'][:16]})"
            )
        text = "\n".join(lines)
    try:
        await callback.message.edit_text(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )


# ─── Пользователи ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def cb_users(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    users = await get_all_users(limit=25)
    if not users:
        text = "👥 <b>Пользователи</b>\n\nПока нет пользователей."
    else:
        lines = [f"👥 <b>Пользователи</b> (последние {len(users)})\n"]
        for u in users:
            uname = f"@{u['username']}" if u["username"] else "—"
            name = u["first_name"] or f"ID:{u['telegram_id']}"
            blocked = " 🚫" if u["is_blocked"] else ""
            lines.append(f"• {name} ({uname}) <code>{u['telegram_id']}</code>{blocked}")
        text = "\n".join(lines)
    try:
        await callback.message.edit_text(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )


# ─── Заблокированные ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_blocked")
async def cb_blocked(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    blocked = await get_blocked_users()
    if not blocked:
        text = "🚫 <b>Заблокированные</b>\n\nЗаблокированных пользователей нет."
    else:
        lines = [f"🚫 <b>Заблокированные</b>\n\nВсего: {len(blocked)}\n"]
        for b in blocked:
            uname = f"@{b['username']}" if b.get("username") else "—"
            name = b.get("first_name") or f"ID:{b['user_id']}"
            lines.append(f"• {name} ({uname}) <code>{b['user_id']}</code>")
        text = "\n".join(lines)
    try:
        await callback.message.edit_text(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )


# ─── Настройки ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_settings")
async def cb_settings(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"Кол-во администраторов: {len(ADMIN_IDS)}\n"
        f"ID администраторов: {', '.join(str(a) for a in ADMIN_IDS)}\n\n"
        "Для изменения настроек отредактируйте переменные окружения."
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=get_back_to_admin_keyboard(), parse_mode="HTML"
        )


# ─── Действия с анкетами ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("app_accept:"))
async def cb_app_accept(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, app_id_s, user_id_s = callback.data.split(":")
    app_id, user_id = int(app_id_s), int(user_id_s)

    await callback.answer("✅ Анкета принята")
    await update_application_status(app_id, "accepted", callback.from_user.id)
    await log_admin_action(callback.from_user.id, "accept_application", user_id, f"app_id={app_id}")

    try:
        await bot.send_message(
            user_id,
            "🎉 <b>Поздравляем!</b>\n\n"
            "Ваша анкета была принята. "
            "Скоро владелец или администратор отправит вам ссылку на хаус.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Cannot notify user %s: %s", user_id, e)

    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + "\n\n✅ <b>ПРИНЯТО</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("app_reject:"))
async def cb_app_reject(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, app_id_s, user_id_s = callback.data.split(":")
    app_id, user_id = int(app_id_s), int(user_id_s)

    await callback.answer("❌ Анкета отклонена")
    await update_application_status(app_id, "rejected", callback.from_user.id)
    await log_admin_action(callback.from_user.id, "reject_application", user_id, f"app_id={app_id}")

    try:
        await bot.send_message(
            user_id,
            "К сожалению, ваша анкета не была принята.\n\n"
            "Спасибо за участие! Вы сможете попробовать снова позже.",
        )
    except Exception as e:
        logger.error("Cannot notify user %s: %s", user_id, e)

    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + "\n\n❌ <b>ОТКЛОНЕНО</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("app_write:"))
async def cb_app_write(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, app_id_s, user_id_s = callback.data.split(":")
    user_id = int(user_id_s)

    await callback.answer()
    await state.set_state(AdminWriteToUser.waiting_for_message)
    await state.update_data(target_user_id=user_id)
    await callback.message.answer(
        f"💬 <b>Напишите сообщение пользователю</b> (<code>{user_id}</code>)\n\n"
        "Введите текст или отправьте медиафайл.\n\n"
        "Для отмены нажмите «❌ Отменить».",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("app_block:"))
async def cb_app_block(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, app_id_s, user_id_s = callback.data.split(":")
    app_id, user_id = int(app_id_s), int(user_id_s)

    await callback.answer("🚫 Пользователь заблокирован")
    await block_user(user_id, callback.from_user.id, f"Заблокирован при рассмотрении анкеты #{app_id}")
    await log_admin_action(callback.from_user.id, "block_user", user_id, f"from app_id={app_id}")

    try:
        await bot.send_message(user_id, "🚫 Доступ к боту ограничен администрацией.")
    except Exception:
        pass

    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + "\n\n🚫 <b>ЗАБЛОКИРОВАН</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ─── Действия с тикетами ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ticket_reply:"))
async def cb_ticket_reply(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    parts = callback.data.split(":")
    ticket_id, user_id = int(parts[1]), int(parts[2])

    await callback.answer()
    await state.set_state(AdminReply.waiting_for_reply)
    await state.update_data(ticket_id=ticket_id, target_user_id=user_id)
    await callback.message.answer(
        f"💬 <b>Ответ на обращение #{ticket_id}</b>\n\n"
        "Введите ответ или отправьте медиафайл.\n\n"
        "Для отмены нажмите «❌ Отменить».",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("ticket_close:"))
async def cb_ticket_close(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    parts = callback.data.split(":")
    ticket_id = int(parts[1])

    await callback.answer("✅ Обращение закрыто")
    await close_ticket(ticket_id, callback.from_user.id)
    await log_admin_action(callback.from_user.id, "close_ticket", ticket_id)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(f"✅ Обращение #{ticket_id} закрыто.")


@router.callback_query(F.data.startswith("ticket_block:"))
async def cb_ticket_block(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    parts = callback.data.split(":")
    ticket_id, user_id = int(parts[1]), int(parts[2])

    await callback.answer("🚫 Пользователь заблокирован")
    await block_user(user_id, callback.from_user.id, f"Заблокирован при обращении #{ticket_id}")
    await close_ticket(ticket_id, callback.from_user.id)
    await log_admin_action(callback.from_user.id, "block_user", user_id, f"from ticket_id={ticket_id}")

    try:
        await bot.send_message(user_id, "🚫 Доступ к боту ограничен администрацией.")
    except Exception:
        pass
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(f"🚫 Пользователь <code>{user_id}</code> заблокирован.", parse_mode="HTML")


# ─── Разблокировать ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("unblock:"))
async def cb_unblock(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await callback.answer("✅ Пользователь разблокирован")
    await unblock_user(user_id)
    await log_admin_action(callback.from_user.id, "unblock_user", user_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        f"✅ Пользователь <code>{user_id}</code> разблокирован.", parse_mode="HTML"
    )


# ─── FSM: ответ на обращение ─────────────────────────────────────────────────

@router.message(StateFilter(AdminReply.waiting_for_reply))
async def admin_reply_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    ticket_id: int = data.get("ticket_id", 0)
    user_id: int = data.get("target_user_id", 0)
    await state.clear()

    msg_type, content, file_id = get_message_info(message)
    if ticket_id:
        await add_message(ticket_id, message.from_user.id, "admin_to_user", msg_type, content, file_id)
    await log_admin_action(message.from_user.id, "reply_to_user", user_id, f"ticket_id={ticket_id}")

    success = await send_reply_to_user(bot, user_id, message)
    if success:
        await message.answer("✅ Ответ отправлен пользователю.", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer(
            "❌ Не удалось отправить ответ. Возможно, пользователь заблокировал бота.",
            reply_markup=ReplyKeyboardRemove(),
        )


# ─── FSM: написать пользователю (из анкеты) ──────────────────────────────────

@router.message(StateFilter(AdminWriteToUser.waiting_for_message))
async def admin_write_user_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    user_id: int = data.get("target_user_id", 0)
    await state.clear()
    await log_admin_action(message.from_user.id, "write_to_user", user_id)

    msg_type, content, file_id = get_message_info(message)
    success = False
    try:
        if message.sticker:
            await bot.send_sticker(user_id, message.sticker.file_id)
            success = True
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            success = True
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption=message.caption)
            success = True
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=message.caption)
            success = True
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id)
            success = True
        elif message.text:
            await bot.send_message(user_id, message.text)
            success = True
    except Exception as e:
        logger.error("Cannot write to user %s: %s", user_id, e)

    if success:
        await message.answer("✅ Сообщение отправлено пользователю.", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("❌ Не удалось отправить сообщение.", reply_markup=ReplyKeyboardRemove())


# ─── Рассылка ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminBroadcast.waiting_for_message)
    await callback.message.answer(
        "📣 <b>Рассылка</b>\n\n"
        "Отправьте сообщение для рассылки.\n\n"
        "Поддерживается: текст, фото, видео, документ.\n\n"
        "Для отмены нажмите «❌ Отменить».",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(AdminBroadcast.waiting_for_message))
async def admin_broadcast_message(message: Message, state: FSMContext) -> None:
    msg_type, content, file_id = get_message_info(message)
    await state.update_data(
        broadcast_type=msg_type,
        broadcast_content=content,
        broadcast_file_id=file_id,
    )
    await state.set_state(AdminBroadcast.confirm)
    await message.answer(
        "👁 <b>Предварительный просмотр рассылки:</b>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    # Show preview
    try:
        await message.forward(message.chat.id)
    except Exception:
        await message.answer("<i>(предпросмотр недоступен)</i>", parse_mode="HTML")
    await message.answer("Начать рассылку?", reply_markup=get_broadcast_confirm_keyboard())


@router.callback_query(F.data == "broadcast_confirm", StateFilter(AdminBroadcast.confirm))
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer("⏳ Рассылка начата...")
    data = await state.get_data()
    await state.clear()

    user_ids = await get_all_user_ids()
    sent = blocked_bot = errors = 0

    for uid in user_ids:
        try:
            btype = data.get("broadcast_type")
            content = data.get("broadcast_content")
            file_id = data.get("broadcast_file_id")

            if btype == "text" and content:
                await bot.send_message(uid, content, parse_mode="HTML")
            elif btype == "photo" and file_id:
                await bot.send_photo(uid, file_id, caption=content, parse_mode="HTML")
            elif btype == "video" and file_id:
                await bot.send_video(uid, file_id, caption=content, parse_mode="HTML")
            elif btype == "document" and file_id:
                await bot.send_document(uid, file_id, caption=content, parse_mode="HTML")
            else:
                continue
            sent += 1
        except Exception as e:
            err_lower = str(e).lower()
            if "blocked" in err_lower or "deactivated" in err_lower or "not found" in err_lower:
                blocked_bot += 1
            else:
                errors += 1

    await log_admin_action(
        callback.from_user.id, "broadcast", None,
        f"sent={sent},blocked={blocked_bot},errors={errors}"
    )
    try:
        await callback.message.edit_text(
            "📣 <b>Рассылка завершена!</b>\n\n"
            f"✅ Отправлено: {sent}\n"
            f"🚫 Заблокировали бота: {blocked_bot}\n"
            f"❌ Ошибок: {errors}",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "📣 <b>Рассылка завершена!</b>\n\n"
            f"✅ Отправлено: {sent}\n"
            f"🚫 Заблокировали бота: {blocked_bot}\n"
            f"❌ Ошибок: {errors}",
            parse_mode="HTML",
        )


@router.callback_query(F.data == "broadcast_cancel")
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer("Рассылка отменена")
    await state.clear()
    try:
        await callback.message.edit_text("❌ Рассылка отменена.")
    except Exception:
        await callback.message.answer("❌ Рассылка отменена.")
