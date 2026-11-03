import sqlite3
from datetime import datetime, timedelta, timezone
from config import DB_PATH

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          user_id INTEGER PRIMARY KEY, age INTEGER, city TEXT, name TEXT,
          gender TEXT, bio TEXT, photo_id TEXT, username TEXT,
          approved INTEGER DEFAULT 0, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS likes(
          from_id INTEGER, to_id INTEGER, created_at TEXT,
          PRIMARY KEY(from_id,to_id)
        );
        CREATE TABLE IF NOT EXISTS subscriptions(
          user_id INTEGER PRIMARY KEY, expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS contact_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT, from_id INTEGER, to_id INTEGER,
          status TEXT DEFAULT 'pending', created_at TEXT
        );
        """)

def save_user(user_id, **kw):
    fields = ["age","city","name","gender","bio","photo_id","username","approved","created_at"]
    vals = [kw.get(k) for k in fields]
    with conn() as c:
        c.execute("""INSERT INTO users(user_id,age,city,name,gender,bio,photo_id,username,approved,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
        age=excluded.age, city=excluded.city, name=excluded.name, gender=excluded.gender,
        bio=excluded.bio, photo_id=excluded.photo_id, username=excluded.username,
        approved=excluded.approved""", [user_id]+vals)

def get_user(uid):
    with conn() as c: return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def count_users():
    with conn() as c: return c.execute("SELECT COUNT(*) FROM users WHERE approved=1").fetchone()[0]

def is_premium(uid):
    with conn() as c:
        row=c.execute("SELECT expires_at FROM subscriptions WHERE user_id=?", (uid,)).fetchone()
    if not row: return False
    try: return datetime.fromisoformat(row["expires_at"]) > datetime.now(timezone.utc)
    except Exception: return False

def activate_premium(uid, days):
    until=datetime.now(timezone.utc)+timedelta(days=days)
    with conn() as c:
        c.execute("""INSERT INTO subscriptions(user_id,expires_at) VALUES(?,?)
        ON CONFLICT(user_id) DO UPDATE SET expires_at=excluded.expires_at""",
        (uid, until.isoformat()))

def next_profile(uid, gender):
    with conn() as c:
        return c.execute("""SELECT * FROM users
        WHERE approved=1 AND user_id != ? AND gender != ?
        AND user_id NOT IN (SELECT to_id FROM likes WHERE from_id=?)
        ORDER BY RANDOM() LIMIT 1""", (uid, gender, uid)).fetchone()

def add_like(a,b):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO likes VALUES(?,?,?)",
                  (a,b,datetime.now(timezone.utc).isoformat()))
        return c.execute("SELECT 1 FROM likes WHERE from_id=? AND to_id=?", (b,a)).fetchone() is not None

def received_likes(uid):
    with conn() as c:
        return c.execute("""SELECT u.* FROM likes l JOIN users u ON u.user_id=l.from_id
        WHERE l.to_id=? ORDER BY l.created_at DESC""", (uid,)).fetchall()

def create_contact_request(a,b):
    with conn() as c:
        cur=c.execute("INSERT INTO contact_requests(from_id,to_id,created_at) VALUES(?,?,?)",
          (a,b,datetime.now(timezone.utc).isoformat()))
        return cur.lastrowid

def get_request(rid):
    with conn() as c:
        return c.execute("""SELECT r.*, a.name AS from_name, b.name AS to_name,
        a.username AS from_username, b.username AS to_username
        FROM contact_requests r JOIN users a ON a.user_id=r.from_id
        JOIN users b ON b.user_id=r.to_id WHERE r.id=?""",(rid,)).fetchone()

def set_request_status(rid,status):
    with conn() as c: c.execute("UPDATE contact_requests SET status=? WHERE id=?",(status,rid))
