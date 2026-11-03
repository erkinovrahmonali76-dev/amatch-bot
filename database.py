
import sqlite3
from datetime import datetime, timedelta, timezone

from config import DB_PATH


def now():
    return datetime.now(timezone.utc).isoformat()


def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode = WAL")

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
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            created_at TEXT,
            PRIMARY KEY(from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS skips(
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
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

        columns = {
            row["name"]
            for row in c.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "adult_verified" not in columns:
            c.execute("""
                ALTER TABLE users
                ADD COLUMN adult_verified INTEGER DEFAULT 0
            """)

        if "is_active" not in columns:
            c.execute("""
                ALTER TABLE users
                ADD COLUMN is_active INTEGER DEFAULT 1
            """)

        c.executescript("""
        CREATE INDEX IF NOT EXISTS idx_users_search
        ON users(approved, is_active, age);

        CREATE INDEX IF NOT EXISTS idx_likes_to
        ON likes(to_id);

        CREATE INDEX IF NOT EXISTS idx_skips_from
        ON skips(from_id);

        CREATE INDEX IF NOT EXISTS idx_payments_status
        ON payments(status);
        """)


def save_user(user_id, **kw):
    allowed = {
        "age", "city", "name", "gender", "bio",
        "photo_id", "username", "approved", "created_at"
    }

    updates = {
        key: value
        for key, value in kw.items()
        if key in allowed and value is not None
    }

    with conn() as c:
        existing = c.execute(
            "SELECT user_id FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if existing:
            if updates:
                sql = ", ".join(
                    f"{key}=?" for key in updates
                )
                c.execute(
                    f"UPDATE users SET {sql} WHERE user_id=?",
                    list(updates.values()) + [user_id]
                )
        else:
            fields = ["user_id"] + list(updates.keys())
            values = [user_id] + list(updates.values())

            placeholders = ",".join("?" for _ in fields)
            c.execute(
                f"""
                INSERT INTO users ({",".join(fields)})
                VALUES ({placeholders})
                """,
                values
            )


def get_user(uid):
    with conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE user_id=?",
            (uid,)
        ).fetchone()


def count_users():
    with conn() as c:
        return c.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE approved=1 AND is_active=1
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
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


def activate_premium(uid, days):
    if days not in (7, 30):
        return False

    current = datetime.now(timezone.utc)

    with conn() as c:
        row = c.execute(
            "SELECT expires_at FROM subscriptions WHERE user_id=?",
            (uid,)
        ).fetchone()

        if row:
            try:
                old_expiry = datetime.fromisoformat(
                    row["expires_at"]
                )
                if old_expiry.tzinfo is None:
                    old_expiry = old_expiry.replace(
                        tzinfo=timezone.utc
                    )
                if old_expiry > current:
                    current = old_expiry
            except (ValueError, TypeError):
                pass

        until = current + timedelta(days=days)

        c.execute("""
            INSERT INTO subscriptions(user_id, expires_at)
            VALUES(?,?)
            ON CONFLICT(user_id)
            DO UPDATE SET expires_at=excluded.expires_at
        """, (uid, until.isoformat()))

    return True


def create_payment(uid, days, amount, receipt_file_id):
    if days not in (7, 30):
        raise ValueError("Noto‘g‘ri tarif")

    expected = {7: 25000, 30: 50000}

    if amount != expected[days]:
        raise ValueError("To‘lov summasi mos emas")

    with conn() as c:
        cur = c.execute("""
            INSERT INTO payments(
                user_id, plan_days, amount,
                receipt_file_id, created_at
            )
            VALUES(?,?,?,?,?)
        """, (uid, days, amount, receipt_file_id, now()))

        return cur.lastrowid


def get_payment(payment_id):
    with conn() as c:
        return c.execute(
            "SELECT * FROM payments WHERE id=?",
            (payment_id,)
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

        cur = c.execute("""
            UPDATE payments
            SET status=?, reviewed_at=?, reviewed_by=?
            WHERE id=? AND status='pending'
        """, (
            status, now(), admin_id, payment_id
        ))

        if cur.rowcount != 1:
            return False

        if approved:
            uid = row["user_id"]
            days = row["plan_days"]
            current = datetime.now(timezone.utc)

            old = c.execute(
                "SELECT expires_at FROM subscriptions WHERE user_id=?",
                (uid,)
            ).fetchone()

            if old:
                try:
                    expiry = datetime.fromisoformat(old["expires_at"])
                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)
                    if expiry > current:
                        current = expiry
                except (ValueError, TypeError):
                    pass

            until = current + timedelta(days=days)

            c.execute("""
                INSERT INTO subscriptions(user_id, expires_at)
                VALUES(?,?)
                ON CONFLICT(user_id)
                DO UPDATE SET expires_at=excluded.expires_at
            """, (uid, until.isoformat()))

        return True


def _age_group(age):
    if age is None:
        return None

    if 15 <= age <= 17:
        return (15, 17)

    if 18 <= age <= 100:
        return (18, 100)

    return None


def next_profile(uid, age=None):
    user = get_user(uid)

    if not user or not user["approved"] or not user["is_active"]:
        return None

    # Yosh faqat foydalanuvchi kiritgan ma'lumot.
    # Bu mustaqil yosh tasdig'i hisoblanmaydi.
    group = _age_group(user["age"])

    if not group:
        return None

    min_age, max_age = group

    with conn() as c:
        return c.execute("""
            SELECT * FROM users
            WHERE approved=1
              AND is_active=1
              AND age BETWEEN ? AND ?
              AND user_id != ?
              AND photo_id IS NOT NULL

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
        """, (
            min_age, max_age, uid,
            uid, uid, uid, uid
        )).fetchone()


def add_skip(a, b):
    if a == b:
        return False

    with conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO skips(
                from_id, to_id, created_at
            )
            VALUES(?,?,?)
        """, (a, b, now()))

    return True


def add_like(a, b):
    if a == b:
        return False

    with conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO likes(
                from_id, to_id, created_at
            )
            VALUES(?,?,?)
        """, (a, b, now()))

        return c.execute("""
            SELECT 1 FROM likes
            WHERE from_id=? AND to_id=?
        """, (b, a)).fetchone() is not None


def received_likes(uid):
    with conn() as c:
        return c.execute("""
            SELECT u.*
            FROM likes l
            JOIN users u ON u.user_id=l.from_id
            WHERE l.to_id=?
              AND u.approved=1
              AND u.is_active=1
            ORDER BY l.created_at DESC
        """, (uid,)).fetchall()


def create_contact_request(a, b):
    if a == b:
        return None

    with conn() as c:
        cur = c.execute("""
            INSERT INTO contact_requests(
                from_id, to_id, created_at
            )
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
        return False

    with conn() as c:
        cur = c.execute("""
            UPDATE contact_requests
            SET status=?
            WHERE id=? AND status='pending'
        """, (status, rid))

        return cur.rowcount > 0


def create_chat_invite(a, b):
    # Bu funksiya hozircha o‘chirilgan.
    # Voyaga yetmaganlar uchun nazoratsiz shaxsiy chat yo‘q.
    return False


def review_chat_invite(invite_id, accepted):
    return False


def block_user(uid, blocked_uid):
    if uid == blocked_uid:
        return False

    with conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO blocks(
                user_id, blocked_id, created_at
            )
            VALUES(?,?,?)
        """, (uid, blocked_uid, now()))

        # Bloklanganda avvalgi layklarni ham bekor qilamiz.
        c.execute("""
            DELETE FROM likes
            WHERE (from_id=? AND to_id=?)
               OR (from_id=? AND to_id=?)
        """, (uid, blocked_uid, blocked_uid, uid))

    return True


def report_user(uid, reported_uid, reason=""):
    if uid == reported_uid:
        return None

    with conn() as c:
        cur = c.execute("""
            INSERT INTO reports(
                from_id, to_id, reason, created_at
            )
            VALUES(?,?,?,?)
        """, (uid, reported_uid, reason[:300], now()))

        return cur.lastrowid
