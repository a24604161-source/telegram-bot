import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан. Добавьте BOT_TOKEN в переменные окружения.")

_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [
    int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()
]

CHANNEL_URL: str = os.getenv("CHANNEL_URL", "https://t.me/wh1sp3r_team")
DB_PATH: str = os.getenv("DB_PATH", "bot.db")

SPAM_LIMIT: int = 5
SPAM_WINDOW: int = 60       # секунд
APPLICATION_COOLDOWN: int = 86400  # 24 часа
