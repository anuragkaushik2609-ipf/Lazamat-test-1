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

flask_app = Flask(__name__)

# Global state to hold bot instances
class BotState:
    admin_app = None
    friend_app = None
    loop = None

state = BotState()

@flask_app.route("/")
def health():
    return "🚀 SERVER IS LIVE! (Python 3.11)"

@flask_app.route("/test")
def trigger_test():
    if not state.admin_app or not state.loop:
        return jsonify({"status": "error", "message": "Bots starting... wait 10s and refresh."})

    try:
        # Task ko thread-safe tarike se async loop mein daalna
        state.loop.call_soon_threadsafe(
            lambda: asyncio.run_coroutine_threadsafe(
                process_test_video(state.admin_app.bot, state.friend_app.bot, TEST_VIDEO_URL),
                state.loop
            )
        )
        return jsonify({"status": "success", "message": "Test triggered! Check Telegram."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

async def start_bots_async():
    print("🤖 Starting Bots on Stable Python...")
    state.admin_app = create_admin_app()
    state.friend_app = create_friend_app()
    state.loop = asyncio.get_running_loop()

    await state.admin_app.initialize()
    await state.friend_app.initialize()
    await state.admin_app.start()
    await state.friend_app.start()
    
    await state.admin_app.updater.start_polling()
    await state.friend_app.updater.start_polling()
    
    print("✅ BOTS ONLINE!")
    while True:
        await asyncio.sleep(3600)

def bot_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bots_async())

# Start bots background thread
threading.Thread(target=bot_worker, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
