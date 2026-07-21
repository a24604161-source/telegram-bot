from aiogram.fsm.state import State, StatesGroup


class ApplicationForm(StatesGroup):
    name        = State()
    age         = State()
    roblox_nick = State()
    activity    = State()
    tiktok_photo = State()
    roblox_photo = State()
    preview     = State()


class SupportForm(StatesGroup):
    waiting_for_message = State()


class AdminReply(StatesGroup):
    waiting_for_reply = State()


class AdminBroadcast(StatesGroup):
    waiting_for_message = State()
    confirm             = State()


class AdminWriteToUser(StatesGroup):
    waiting_for_message = State()
