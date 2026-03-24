import asyncio
import threading
import os
from flask import Flask, jsonify
from admin_bot import create_admin_app
from friend_bot import create_friend_app
from config import check_config, TEST_VIDEO_URL
from sheets import log_action
from video_handler import process_test_video

# ─────────────────────────────────────────
# GLOBAL BOT REFERENCES
# ─────────────────────────────────────────

_admin_app = None
_friend_app = None
_bot_loop = None  # Bots wala asyncio loop


# ─────────────────────────────────────────
# FLASK SERVER
# ─────────────────────────────────────────

flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "🚀 LAMAZAT CANVAS — Running!"

@flask_app.route("/health")
def health_check():
    # Check if bots are initialized
    status = "running" if (_admin_app and _friend_app) else "initializing"
    return {"status": "ok", "bots": status}


# ─────────────────────────────────────────
# /test — Manual Trigger Logic
# ─────────────────────────────────────────

@flask_app.route("/test")
def trigger_test():
    global _admin_app, _friend_app, _bot_loop

    # 1. Check if bots are ready
    if not _admin_app or not _friend_app or not _bot_loop:
        return jsonify({
            "status": "error",
            "message": "Bots abhi start nahi hue — thoda wait karo aur dobara try karo"
        })

    # 2. Async function ko existing loop mein run karo
    try:
        asyncio.run_coroutine_threadsafe(
            process_test_video(_admin_app.bot, _friend_app.bot, TEST_VIDEO_URL),
            _bot_loop
        )
        
        return jsonify({
            "status": "success",
            "message": "Test process shuru ho gaya hai! Telegram check karo."
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Test trigger fail: {str(e)}"
        })


# ─────────────────────────────────────────
# BOT STARTUP LOGIC (Async)
# ─────────────────────────────────────────

async def run_bots():
    global _admin_app, _friend_app, _bot_loop

    _admin_app = create_admin_app()
    _friend_app = create_friend_app()

    # Loop save karo taaki Flask isse use kar sake
    _bot_loop = asyncio.get_running_loop()

    # Apps initialize aur start karo
    await _admin_app.initialize()
    await _friend_app.initialize()
    await _admin_app.start()
    await _friend_app.start()

    # Polling start karo
    await _admin_app.updater.start_polling()
    await _friend_app.updater.start_polling()

    print("✅ Bots start ho gaye hain!")
    log_action("Main", "Both bots started successfully", "Success")
    
    # Infinite loop taaki thread chalta rahe
    stop_event = asyncio.Event()
    await stop_event.wait()


def start_bots_thread():
    """Naya asyncio loop create karke bots chalao"""
    try:
        asyncio.run(run_bots())
    except Exception as e:
        print(f"❌ Bots Error: {e}")
        log_action("Main", f"Bots crashed: {str(e)}", "Error")


# ─────────────────────────────────────────
# AUTO-START (Render/Gunicorn compatibility)
# ─────────────────────────────────────────

print("🚀 LAMAZAT CANVAS — Initializing...")

# Environment variables check karo
errors = check_config()
if errors:
    print("❌ Configuration Error!")
else:
    # GLOBAL START: Ye block Render pe file load hote hi chal jayega
    print("✅ Starting background bot thread...")
    bot_thread = threading.Thread(target=start_bots_thread, daemon=True)
    bot_thread.start()


# ─────────────────────────────────────────
# LOCAL RUN (Sirf PC pe chalate waqt)
# ─────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask server running on port {port}...")
    flask_app.run(host="0.0.0.0", port=port)
