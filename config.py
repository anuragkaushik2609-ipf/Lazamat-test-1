import os

# ── Telegram ──
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
FRIEND_BOT_TOKEN = os.getenv("FRIEND_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
FRIEND_CHAT_ID = os.getenv("FRIEND_CHAT_ID")

# ── Google Sheets ──
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# ── Groq ──
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Eprolo ──
EPROLO_EMAIL    = os.getenv("EPROLO_EMAIL")
EPROLO_PASSWORD = os.getenv("EPROLO_PASSWORD")

# ── Test Video ──
TEST_VIDEO_URL = os.getenv(
    "TEST_VIDEO_URL",
    "https://www.instagram.com/reel/DWOnG3hFGMV/?igsh=MTF1b2E0dHgwdzY3Ng=="
)

# ── Validation ──
def check_config():
    errors = []
    if not ADMIN_BOT_TOKEN:    errors.append("ADMIN_BOT_TOKEN missing")
    if not FRIEND_BOT_TOKEN:   errors.append("FRIEND_BOT_TOKEN missing")
    if not ADMIN_CHAT_ID:      errors.append("ADMIN_CHAT_ID missing")
    if not FRIEND_CHAT_ID:     errors.append("FRIEND_CHAT_ID missing")
    if not GOOGLE_SHEET_ID:    errors.append("GOOGLE_SHEET_ID missing")
    if not GOOGLE_CREDENTIALS: errors.append("GOOGLE_CREDENTIALS missing")
    if not GROQ_API_KEY:       errors.append("GROQ_API_KEY missing")
    if not EPROLO_EMAIL:       errors.append("EPROLO_EMAIL missing")
    if not EPROLO_PASSWORD:    errors.append("EPROLO_PASSWORD missing")
    return errors
