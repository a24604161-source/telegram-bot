import aiosqlite
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                last_name   TEXT,
                created_at  TEXT DEFAULT (datetime('now', 'localtime')),
                last_active TEXT DEFAULT (datetime('now', 'localtime')),
                is_blocked  INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS applications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                name            TEXT NOT NULL,
                age             INTEGER NOT NULL,
                roblox_nick     TEXT NOT NULL,
                activity        TEXT NOT NULL,
                tiktok_photo_id TEXT NOT NULL,
                roblox_photo_id TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                created_at      TEXT DEFAULT (datetime('now', 'localtime')),
                processed_by    INTEGER,
                processed_at    TEXT,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS support_tickets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                ticket_type TEXT DEFAULT 'support',
                status      TEXT DEFAULT 'open',
                created_at  TEXT DEFAULT (datetime('now', 'localtime')),
                closed_at   TEXT,
                closed_by   INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id    INTEGER,
                user_id      INTEGER NOT NULL,
                direction    TEXT NOT NULL,
                message_type TEXT NOT NULL,
                content      TEXT,
                file_id      TEXT,
                created_at   TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS admin_actions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id    INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_id   INTEGER,
                details     TEXT,
                created_at  TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id    INTEGER PRIMARY KEY,
                blocked_by INTEGER NOT NULL,
                blocked_at TEXT DEFAULT (datetime('now', 'localtime')),
                reason     TEXT,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            );
        """)
        await db.commit()
    logger.info("База данных инициализирована")


# ─── Пользователи ────────────────────────────────────────────────────────────

async def register_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username    = excluded.username,
                first_name  = excluded.first_name,
                last_name   = excluded.last_name,
                last_active = datetime('now', 'localtime')
            """,
            (telegram_id, username, first_name, last_name),
        )
        await db.commit()


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_user_activity(telegram_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_active = datetime('now', 'localtime') WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()


async def get_all_users(limit: int = 50, offset: int = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT telegram_id FROM users WHERE is_blocked = 0"
        ) as cur:
            return [r[0] for r in await cur.fetchall()]


# ─── Анкеты ──────────────────────────────────────────────────────────────────

async def create_application(
    user_id: int,
    name: str,
    age: int,
    roblox_nick: str,
    activity: str,
    tiktok_photo_id: str,
    roblox_photo_id: str,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO applications
                (user_id, name, age, roblox_nick, activity, tiktok_photo_id, roblox_photo_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, name, age, roblox_nick, activity, tiktok_photo_id, roblox_photo_id),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def get_application(app_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_pending_applications() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM applications WHERE status = 'pending' ORDER BY created_at ASC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def update_application_status(
    app_id: int, status: str, processed_by: int
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE applications
            SET status = ?, processed_by = ?, processed_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (status, processed_by, app_id),
        )
        await db.commit()


async def has_pending_application(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT COUNT(*) FROM applications
            WHERE user_id = ? AND status = 'pending'
              AND created_at > datetime('now', 'localtime', '-24 hours')
            """,
            (user_id,),
        ) as cur:
            count = (await cur.fetchone())[0]
            return count > 0


# ─── Обращения (тикеты) ──────────────────────────────────────────────────────

async def create_ticket(user_id: int, ticket_type: str = "support") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO support_tickets (user_id, ticket_type) VALUES (?, ?)",
            (user_id, ticket_type),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def get_ticket(ticket_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_open_tickets() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE status = 'open' ORDER BY created_at ASC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def close_ticket(ticket_id: int, closed_by: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE support_tickets
            SET status = 'closed', closed_by = ?, closed_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (closed_by, ticket_id),
        )
        await db.commit()


async def add_message(
    ticket_id: int,
    user_id: int,
    direction: str,
    message_type: str,
    content: str | None,
    file_id: str | None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO messages (ticket_id, user_id, direction, message_type, content, file_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, user_id, direction, message_type, content, file_id),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


# ─── Блокировки ──────────────────────────────────────────────────────────────

async def block_user(
    user_id: int, blocked_by: int, reason: str | None = None
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO blocked_users (user_id, blocked_by, reason) VALUES (?, ?, ?)",
            (user_id, blocked_by, reason),
        )
        await db.execute(
            "UPDATE users SET is_blocked = 1 WHERE telegram_id = ?", (user_id,)
        )
        await db.commit()


async def unblock_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
        await db.execute(
            "UPDATE users SET is_blocked = 0 WHERE telegram_id = ?", (user_id,)
        )
        await db.commit()


async def is_blocked(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM blocked_users WHERE user_id = ?", (user_id,)
        ) as cur:
            return (await cur.fetchone())[0] > 0


async def get_blocked_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT b.*, u.username, u.first_name
            FROM blocked_users b
            LEFT JOIN users u ON b.user_id = u.telegram_id
            ORDER BY b.blocked_at DESC
            """
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ─── Действия администраторов ────────────────────────────────────────────────

async def log_admin_action(
    admin_id: int,
    action_type: str,
    target_id: int | None = None,
    details: str | None = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO admin_actions (admin_id, action_type, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (admin_id, action_type, target_id, details),
        )
        await db.commit()


# ─── Статистика ──────────────────────────────────────────────────────────────

async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        stats: dict = {}

        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            stats["total_users"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at > datetime('now','localtime','-1 day')"
        ) as cur:
            stats["new_users_today"] = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM applications") as cur:
            stats["total_applications"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'accepted'"
        ) as cur:
            stats["accepted_applications"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'rejected'"
        ) as cur:
            stats["rejected_applications"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM support_tickets WHERE status = 'open'"
        ) as cur:
            stats["open_tickets"] = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM blocked_users") as cur:
            stats["blocked_users"] = (await cur.fetchone())[0]

        return stats
