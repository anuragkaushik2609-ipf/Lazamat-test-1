import asyncio
import threading
import os
from flask import Flask, jsonify
from admin_bot import create_admin_app
from friend_bot import create_friend_app
from config import check_config
from sheets import log_action

# ─────────────────────────────────────────
# GLOBAL BOT REFERENCES
# /test endpoint inhe use karega
# ─────────────────────────────────────────

_admin_app = None
_friend_app = None
_bot_loop = None  # Bots wala asyncio loop


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
# /test — Manually test trigger karo
# Hit karo: https://your-app.onrender.com/test
# ─────────────────────────────────────────

@flask_app.route("/test")
def trigger_test():
    """
    Is URL ko hit karo aur test shuru ho jayega:
    1. Instagram video download (yt-dlp)
    2. Groq se unique code generate
    3. Admin Bot par info
    4. Friend Bot par video + code
    """
    global _admin_app, _friend_app, _bot_loop

    # Bots ready hain?
    if not _admin_app or not _friend_app or not _bot_loop:
        return jsonify({
            "status": "error",
            "message": "Bots abhi start nahi hue — thoda wait karo aur dobara try karo"
        }), 503

    try:
        from video_handler import process_test_video

        # Bot loop mein async task submit karo (thread-safe)
        future = asyncio.run_coroutine_threadsafe(
            process_test_video(_admin_app.bot, _friend_app.bot),
            _bot_loop
        )

        # 180 seconds tak wait karo (video download time)
        result = future.result(timeout=180)

        if result["success"]:
            return jsonify({
                "status": "success",
                "message": "Test complete! Admin + Friend Bot pe messages gaye.",
                "unique_code": result["code"]
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Test failed: {result.get('error', 'Unknown error')}"
            }), 500

    except TimeoutError:
        return jsonify({
            "status": "error",
            "message": "Timeout — video download bahut time le raha hai (>3 min)"
        }), 504
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ─────────────────────────────────────────
# DONO BOTS EK HI ASYNCIO LOOP MEIN
# ─────────────────────────────────────────

async def run_bots():
    global _admin_app, _friend_app, _bot_loop

    _admin_app = create_admin_app()
    _friend_app = create_friend_app()

    # Current loop save karo — Flask thread use karega
    _bot_loop = asyncio.get_event_loop()

    # Dono apps initialize karo
    await _admin_app.initialize()
    await _friend_app.initialize()

    # Dono apps start karo
    await _admin_app.start()
    await _friend_app.start()

    # Polling start karo
    await _admin_app.updater.start_polling()
    await _friend_app.updater.start_polling()

    print("✅ Admin Bot chal raha hai!")
    print("✅ Friend Bot chal raha hai!")
    log_action("Main", "Both bots started successfully", "Success")
    print("✅ Dono bots chal rahe hain!")
    print("─" * 40)
    print("🌐 Test karne ke liye hit karo: /test")
    print("─" * 40)

    # Jab tak cancel na ho chalate raho
    stop_event = asyncio.Event()
    await stop_event.wait()


def start_bots():
    """Bots ko alag thread pe asyncio loop mein chalao"""
    try:
        asyncio.run(run_bots())
    except Exception as e:
        print(f"❌ Bots Error: {e}")
        import traceback
        traceback.print_exc()
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
