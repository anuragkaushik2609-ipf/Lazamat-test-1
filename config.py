import os

# Telegram
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
FRIEND_BOT_TOKEN = os.getenv("FRIEND_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Validation
def check_config():
    errors = []

    if not ADMIN_BOT_TOKEN:
        errors.append("ADMIN_BOT_TOKEN missing")
    if not FRIEND_BOT_TOKEN:
        errors.append("FRIEND_BOT_TOKEN missing")
    if not ADMIN_CHAT_ID:
        errors.append("ADMIN_CHAT_ID missing")
    if not GOOGLE_SHEET_ID:
        errors.append("GOOGLE_SHEET_ID missing")
    if not GOOGLE_CREDENTIALS:
        errors.append("GOOGLE_CREDENTIALS missing")
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY missing")

    return errors
