import asyncio
import threading
import os
import time
from flask import Flask, jsonify
from admin_bot import create_admin_app
from friend_bot import create_friend_app
from config import check_config, TEST_VIDEO_URL
from sheets import log_action
from video_handler import process_test_video

# Flask App setup
flask_app = Flask(__name__)

# Global state
class BotState:
    admin_app = None
    friend_app = None
    loop = None

state = BotState()

@flask_app.route("/")
def health():
    return "🚀 SERVER IS LIVE!"

@flask_app.route("/test")
def trigger_test():
    # Agar bot abhi tak start nahi hua, toh hum thoda wait karenge
    for _ in range(5): 
        if state.admin_app and state.loop:
            break
        time.sleep(2)

    if not state.admin_app:
        return jsonify({"status": "error", "message": "Bot initialization failure. Check Render Logs."})

    try:
        # Loop mein task daal do
        state.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                process_test_video(state.admin_app.bot, state.friend_app.bot, TEST_VIDEO_URL)
            )
        )
        return jsonify({"status": "success", "message": "Test process started! Check Telegram."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

async def start_async_bots():
    state.admin_app = create_admin_app()
    state.friend_app = create_friend_app()
    state.loop = asyncio.get_running_loop()

    await state.admin_app.initialize()
    await state.friend_app.initialize()
    await state.admin_app.start()
    await state.friend_app.start()
    
    await state.admin_app.updater.start_polling()
    await state.friend_app.updater.start_polling()
    
    print("✅ BOTS ARE NOW ONLINE")
    # Keep alive
    while True:
        await asyncio.sleep(3600)

def run_bots_forever():
    asyncio.run(start_async_bots())

# Render startup ke liye direct call (Bahut Important)
print("🚀 Starting background threads...")
t = threading.Thread(target=run_bots_forever, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
