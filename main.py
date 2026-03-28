import asyncio
import threading
import os
import time
import traceback
from flask import Flask, jsonify
from admin_bot import create_admin_app
from friend_bot import create_friend_app
from config import check_config, TEST_VIDEO_URL, ADMIN_BOT_TOKEN
from sheets import log_action
from automation1 import start_automation1, run_product_test


flask_app = Flask(__name__)

class BotState:
    admin_app = None
    friend_app = None
    loop = None
    bots_ready = False

state = BotState()

@flask_app.route("/")
def health():
    status = "✅ BOTS READY" if state.bots_ready else "⏳ BOTS STARTING"
    return f"🚀 LAMAZAT CANVAS — SERVER LIVE! | {status}"

@flask_app.route("/test")
def trigger_test():
    if not state.bots_ready or not state.loop:
        return jsonify({
            "status": "error",
            "message": "Bots abhi ready nahi hain. 15 second baad try karo."
        })
    try:
        def run_test_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_product_test(ADMIN_BOT_TOKEN))

        import threading
        threading.Thread(target=run_test_in_thread, daemon=True).start()
        return jsonify({
            "status": "success",
            "message": "✅ Product test shuru ho gaya! ~45-60 sec mein Telegram pe result aayega."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@flask_app.route("/automation1/status")
def auto1_status():
    try:
        from sheets import get_early_pool_count, get_automation_flag
        count = get_early_pool_count()
        flag  = get_automation_flag("Automation1")
        return jsonify({
            "bots_ready": state.bots_ready,
            "automation_status": flag.get("status") if flag else "Unknown",
            "pool": count
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# ─────────────────────────────────────────
# BOT WORKER
# ─────────────────────────────────────────

async def start_bots_async():
    try:
        print("🤖 [Bots] Initializing Admin Bot...")
        state.admin_app = create_admin_app()

        print("🤖 [Bots] Initializing Friend Bot...")
        state.friend_app = create_friend_app()

        state.loop = asyncio.get_running_loop()

        print("🤖 [Bots] Starting Admin Bot...")
        await state.admin_app.initialize()
        await state.admin_app.start()

        print("🤖 [Bots] Starting Friend Bot...")
        await state.friend_app.initialize()
        await state.friend_app.start()

        print("🤖 [Bots] Starting polling...")
        # run_polling ke bajaye manually start karo — zyada control milta hai
        await state.admin_app.updater.start_polling(drop_pending_updates=True)
        await state.friend_app.updater.start_polling(drop_pending_updates=True)

        state.bots_ready = True
        print("✅ [Bots] BOTS ONLINE! Polling started.")
        log_action("Main", "Both bots online and polling", "Success")

        # Forever alive rakho
        while True:
            await asyncio.sleep(60)

    except Exception as e:
        print(f"❌ [Bots] FATAL ERROR: {e}")
        print(traceback.format_exc())
        log_action("Main", f"Bot startup failed: {e}", "Error")

def bot_worker():
    print("🔧 [BotThread] Starting event loop...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_bots_async())
    except Exception as e:
        print(f"❌ [BotThread] Thread crashed: {e}")
        print(traceback.format_exc())

# ─────────────────────────────────────────
# AUTOMATION 1 WORKER
# ─────────────────────────────────────────

def automation1_worker():
    print("🔍 [Auto1] Starting Automation 1...")
    try:
        start_automation1(ADMIN_BOT_TOKEN)
    except Exception as e:
        print(f"❌ [Auto1] CRASHED: {e}")
        print(traceback.format_exc())
        log_action("Auto1", f"Crashed: {e}", "Error")

def delayed_auto1():
    print("⏳ [Auto1] Waiting 20s for bots to start...")
    time.sleep(20)
    # Bots ready hone tak wait karo
    for i in range(30):  # Max 5 min wait
        if state.bots_ready:
            print("✅ [Auto1] Bots ready — starting Automation 1")
            break
        print(f"⏳ [Auto1] Bots not ready yet... ({i+1}/30)")
        time.sleep(10)
    automation1_worker()

# ─────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────

print("🚀 [Main] Server starting...")
print(f"🔑 [Main] ADMIN_BOT_TOKEN: {'SET ✅' if ADMIN_BOT_TOKEN else 'MISSING ❌'}")

# Config check
errors = check_config()
if errors:
    print(f"⚠️ [Main] Config warnings: {errors}")
else:
    print("✅ [Main] All config variables present")

# Threads start karo
bot_thread = threading.Thread(target=bot_worker, daemon=False)  # daemon=False — crash pe log dikhega
bot_thread.start()
print("🔧 [Main] Bot thread started")

auto1_thread = threading.Thread(target=delayed_auto1, daemon=False)
auto1_thread.start()
print("🔧 [Main] Automation 1 thread started")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 [Main] Flask starting on port {port}")
    flask_app.run(host="0.0.0.0", port=port)
