import asyncio
import threading
from admin_bot import main as admin_main
from friend_bot import main as friend_main
from config import check_config
from sheets import log_action

# ─────────────────────────────────────────
# CONFIG CHECK
# ─────────────────────────────────────────

def check_before_start():
    errors = check_config()
    if errors:
        print("❌ Environment Variables missing hain:")
        for e in errors:
            print(f"   - {e}")
        print("\nRender ke Environment Variables mein sab daalo!")
        return False
    print("✅ Saari environment variables set hain!")
    return True

# ─────────────────────────────────────────
# DONO BOTS ALAG THREADS PE CHALAO
# ─────────────────────────────────────────

def run_admin_bot():
    print("🤖 Admin Bot start ho raha hai...")
    try:
        admin_main()
    except Exception as e:
        print(f"❌ Admin Bot Error: {e}")
        log_action("Admin Bot", f"Crash: {str(e)}", "Error")

def run_friend_bot():
    print("👥 Friend Bot start ho raha hai...")
    try:
        friend_main()
    except Exception as e:
        print(f"❌ Friend Bot Error: {e}")
        log_action("Friend Bot", f"Crash: {str(e)}", "Error")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 LAMAZAT CANVAS — Starting...")
    print("─" * 40)

    # Config check
    if not check_before_start():
        exit(1)

    print("─" * 40)

    # Dono bots alag threads pe chalao
    admin_thread = threading.Thread(target=run_admin_bot, daemon=True)
    friend_thread = threading.Thread(target=run_friend_bot, daemon=True)

    admin_thread.start()
    friend_thread.start()

    print("✅ Dono bots chal rahe hain!")
    log_action("Main", "Both bots started successfully", "Success")

    # Threads alive rakhna
    admin_thread.join()
    friend_thread.join()
