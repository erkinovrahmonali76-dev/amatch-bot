
import sqlite3
from datetime import datetime, timedelta, timezone
from config import DB_PATH


def now():
    return datetime.now(timezone.utc).isoformat()


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def table_columns(c, table):
    return {
        row["name"]
        for row in c.execute(f"PRAGMA table_info({table})").fetchall()
    }


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            age INTEGER,
            city TEXT,
            name TEXT,
            gender TEXT,
            bio TEXT,
            photo_id TEXT,
            username TEXT,
            approved INTEGER DEFAULT 0,
            created_at TEXT,
            adult_verified INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS likes(
            from_id INTEGER,
            to_id INTEGER,
            created_at TEXT,
            PRIMARY KEY(from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS skips(
            from_id INTEGER,
            to_id INTEGER,
            created_at TEXT,
            PRIMARY KEY(from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS subscriptions(
            user_id INTEGER PRIMARY KEY,
            expires_at TEXT
        );

        CREATE TABLE IF NOT EXISTS contact_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER,
            to_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_days INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            receipt_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            reviewed_at TEXT,
            reviewed_by INTEGER
        );

        CREATE TABLE IF NOT EXISTS chat_invites(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            UNIQUE(from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS blocks(
            user_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TEXT,
            PRIMARY KEY(user_id, blocked_id)
        );

        CREATE TABLE IF NOT EXISTS reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT
        );
        """)

        # Eski bazaga yangi ustunlarni xavfsiz qo‘shish.
        columns = table_columns(c, "users")

        if "adult_verified" not in columns:
            c.execute(
                "ALTER TABLE users ADD COLUMN adult_verified INTEGER DEFAULT 0"
            )

        if "is_active" not in columns:
            c.execute(
                "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"
            )


def save_user(user_id, **kw):
    fields = [
        "age", "city", "name", "gender", "bio",
        "photo_id", "username", "approved", "created_at"
    ]

    with conn() as c:
        existing = c.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)
        ).fetchone()

        if existing:
            updates = {
                key: value
                for key, value in kw.items()
                if key in fields and value is not None
            }

            if updates:
                sql = ", ".join(f"{key}=?" for key in updates)
                c.execute(
                    f"UPDATE users SET {sql} WHERE user_id=?",
                    list(updates.values()) + [user_id]
                )
        else:
            values = [kw.get(key) for key in fields]
            c.execute("""
                INSERT INTO users(
                    user_id, age, city, name, gender, bio,
                    photo_id, username, approved, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """, [user_id] + values)


def get_user(uid):
    with conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE user_id=?", (uid,)
        ).fetchone()


def count_users():
    with conn() as c:
        return c.execute("""
            SELECT COUNT(*) FROM users
            WHERE approved=1 AND adult_verified=1 AND is_active=1
        """).fetchone()[0]


def is_premium(uid):
    with conn() as c:
        row = c.execute(
            "SELECT expires_at FROM subscriptions WHERE user_id=?",
            (uid,)
        ).fetchone()

    if not row:
        return False

    try:
        expiry = datetime.fromisoformat(row["expires_at"])
        return expiry > datetime.now(timezone.utc)
    except Exception:
        return False


def activate_premium(uid, days):
    until = datetime.now(timezone.utc) + timedelta(days=days)

    with conn() as c:
        c.execute("""
            INSERT INTO subscriptions(user_id, expires_at)
            VALUES(?,?)
            ON CONFLICT(user_id)
            DO UPDATE SET expires_at=excluded.expires_at
        """, (uid, until.isoformat()))


def create_payment(uid, days, amount, receipt_file_id):
    with conn() as c:
        cur = c.execute("""
            INSERT INTO payments(
                user_id, plan_days, amount, receipt_file_id, created_at
            ) VALUES(?,?,?,?,?)
        """, (uid, days, amount, receipt_file_id, now()))

        return cur.lastrowid


def get_payment(payment_id):
    with conn() as c:
        return c.execute(
            "SELECT * FROM payments WHERE id=?", (payment_id,)
        ).fetchone()


def pending_payments():
    with conn() as c:
        return c.execute("""
            SELECT * FROM payments
            WHERE status='pending'
            ORDER BY created_at ASC
        """).fetchall()


def review_payment(payment_id, admin_id, approved):
    status = "approved" if approved else "rejected"

    with conn() as c:
        row = c.execute("""
            SELECT * FROM payments
            WHERE id=? AND status='pending'
        """, (payment_id,)).fetchone()

        if not row:
            return False

        c.execute("""
            UPDATE payments
            SET status=?, reviewed_at=?, reviewed_by=?
            WHERE id=? AND status='pending'
        """, (status, now(), admin_id, payment_id))

        if approved:
            until = datetime.now(timezone.utc) + timedelta(
                days=row["plan_days"]
            )
            c.execute("""
                INSERT INTO subscriptions(user_id, expires_at)
                VALUES(?,?)
                ON CONFLICT(user_id)
                DO UPDATE SET expires_at=excluded.expires_at
            """, (row["user_id"], until.isoformat()))

        return True


def next_profile(uid, gender):
    with conn() as c:
        return c.execute("""
            SELECT * FROM users
            WHERE approved=1
              AND adult_verified=1
              AND is_active=1
              AND user_id != ?
              AND gender != ?
              AND user_id NOT IN (
                  SELECT to_id FROM likes WHERE from_id=?
              )
              AND user_id NOT IN (
                  SELECT to_id FROM skips WHERE from_id=?
              )
              AND user_id NOT IN (
                  SELECT blocked_id FROM blocks WHERE user_id=?
              )
              AND user_id NOT IN (
                  SELECT user_id FROM blocks WHERE blocked_id=?
              )
            ORDER BY RANDOM()
            LIMIT 1
        """, (uid, gender, uid, uid, uid, uid)).fetchone()


def add_skip(a, b):
    with conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO skips(from_id, to_id, created_at)
            VALUES(?,?,?)
        """, (a, b, now()))


def add_like(a, b):
    with conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO likes(from_id, to_id, created_at)
            VALUES(?,?,?)
        """, (a, b, now()))

        return c.execute("""
            SELECT 1 FROM likes
            WHERE from_id=? AND to_id=?
        """, (b, a)).fetchone() is not None


def received_likes(uid):
    with conn() as c:
        return c.execute("""
            SELECT u.* FROM likes l
            JOIN users u ON u.user_id=l.from_id
            WHERE l.to_id=?
              AND u.approved=1
              AND u.adult_verified=1
              AND u.is_active=1
            ORDER BY l.created_at DESC
        """, (uid,)).fetchall()


def create_contact_request(a, b):
    with conn() as c:
        cur = c.execute("""
            INSERT INTO contact_requests(from_id, to_id, created_at)
            VALUES(?,?,?)
        """, (a, b, now()))

        return cur.lastrowid


def get_request(rid):
    with conn() as c:
        return c.execute("""
            SELECT r.*,
                   a.name AS from_name,
                   b.name AS to_name
            FROM contact_requests r
            JOIN users a ON a.user_id=r.from_id
            JOIN users b ON b.user_id=r.to_id
            WHERE r.id=?
        """, (rid,)).fetchone()


def set_request_status(rid, status):
    if status not in ("pending", "accepted", "rejected"):
        return

    with conn() as c:
        c.execute(
            "UPDATE contact_requests SET status=? WHERE id=?",
            (status, rid)
        )


def create_chat_invite(a, b):
    if a == b:
        return False

    with conn() as c:
        if not is_premium(a):
            return False

        used = c.execute("""
            SELECT COUNT(*) FROM chat_invites
            WHERE from_id=? AND status IN ('pending','accepted')
        """, (a,)).fetchone()[0]

        if used >= 5:
            return False

        try:
            c.execute("""
                INSERT INTO chat_invites(from_id, to_id, created_at)
                VALUES(?,?,?)
            """, (a, b, now()))
            return True
        except sqlite3.IntegrityError:
            return False


def review_chat_invite(invite_id, accepted):
    status = "accepted" if accepted else "rejected"

    with conn() as c:
        cur = c.execute("""
            UPDATE chat_invites
            SET status=?
            WHERE id=? AND status='pending'
        """, (status, invite_id))

        return cur.rowcount > 0


def block_user(uid, blocked_uid):
    with conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO blocks(user_id, blocked_id, created_at)
            VALUES(?,?,?)
        """, (uid, blocked_uid, now()))


def report_user(uid, reported_uid, reason=""):
    with conn() as c:
        cur = c.execute("""
            INSERT INTO reports(from_id, to_id, reason, created_at)
            VALUES(?,?,?,?)
        """, (uid, reported_uid, reason[:300], now()))

        return cur.lastrowid
