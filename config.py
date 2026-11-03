import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "sara_match.db")

PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

PREMIUM_WEEK_DAYS = 7
PREMIUM_MONTH_DAYS = 30
PREMIUM_WEEK_PRICE = 25000
PREMIUM_MONTH_PRICE = 50000

PREMIUM_CHAT_LIMIT = 5
