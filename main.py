import asyncio
import threading
import os
from flask import Flask
from admin_bot import create_admin_app
from friend_bot import create_friend_app
from config import check_config
from sheets import log_action

# ─────────────────────────────────────────
# FLASK — Render ke liye port chahiye
# ─────────────────────────────────────────

flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "🚀 LAMAZAT CANVAS — Running!"

@flask_app.route("/health")
def health_check():
    return {"status": "ok", "bots": "running"}

# ─────────────────────────────────────────
# DONO BOTS EK HI ASYNCIO LOOP MEIN
# ─────────────────────────────────────────

async def run_bots():
    admin_app = create_admin_app()
    friend_app = create_friend_app()

    async with admin_app, friend_app:
        await admin_app.updater.start_polling()
        await admin_app.start()
        print("✅ Admin Bot chal raha hai!")

        await friend_app.updater.start_polling()
        await friend_app.start()
        print("✅ Friend Bot chal raha hai!")

        log_action("Main", "Both bots started successfully", "Success")
        print("✅ Dono bots chal rahe hain!")
        print("─" * 40)

        await asyncio.Event().wait()

def start_bots():
    try:
        asyncio.run(run_bots())
    except Exception as e:
        print(f"❌ Bots Error: {e}")
        log_action("Main", f"Bots crashed: {str(e)}", "Error")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 LAMAZAT CANVAS — Starting...")
    print("─" * 40)

    errors = check_config()
    if errors:
        print("❌ Environment Variables missing hain:")
        for e in errors:
            print(f"   - {e}")
        print("\nRender ke Environment Variables mein sab daalo!")
        exit(1)

    print("✅ Saari environment variables set hain!")
    print("─" * 40)

    bot_thread = threading.Thread(target=start_bots, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask server port {port} pe chal raha hai...")
    flask_app.run(host="0.0.0.0", port=port)
