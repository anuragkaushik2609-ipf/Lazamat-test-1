"""
video_handler.py
────────────────────────────────────────────────
Abhi ka kaam (Test Phase):
  1. Groq AI se unique code banao
  2. Admin Bot par info bhejo
  3. Channel par sirf URL + Code bhejo (video nahi)

Future mein: yt-dlp se video download add hoga
"""

import os
from groq import Groq
from config import GROQ_API_KEY
from sheets import log_action

# ─────────────────────────────────────────
# IN-MEMORY STORE
# Format: { "LMZT-A3K9": { "url": "...", "used": False } }
# ─────────────────────────────────────────
VALID_CODES = {}


# ─────────────────────────────────────────
# UNIQUE CODE GENERATE — GROQ AI
# ─────────────────────────────────────────

def generate_unique_code() -> str:
    try:
        client = Groq(api_key=GROQ_API_KEY)

        used_codes = list(VALID_CODES.keys())
        used_str = ", ".join(used_codes) if used_codes else "none"

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a unique code in format: LMZT-XXXX "
                        "(4 uppercase letters/numbers). Only output code."
                    )
                },
                {
                    "role": "user",
                    "content": f"Used codes: {used_str}"
                }
            ],
            max_tokens=20,
            temperature=1.0
        )

        code = response.choices[0].message.content.strip().upper()

        if code.startswith("LMZT-") and len(code) == 9:
            log_action("VideoHandler", f"Code generated: {code}", "Success")
            return code
        else:
            return _fallback_code()

    except Exception as e:
        log_action("VideoHandler", f"Groq error: {str(e)}", "Warning")
        return _fallback_code()


def _fallback_code() -> str:
    import random, string
    chars = string.ascii_uppercase + string.digits
    while True:
        code = f"LMZT-{''.join(random.choices(chars, k=4))}"
        if code not in VALID_CODES:
            return code


# ─────────────────────────────────────────
# CODE VALIDATION
# ─────────────────────────────────────────

def is_valid_code(code: str) -> bool:
    return code.upper().strip() in VALID_CODES


def get_code_info(code: str):
    return VALID_CODES.get(code.upper().strip())


def mark_code_used(code: str):
    code = code.upper().strip()
    if code in VALID_CODES:
        VALID_CODES[code]["used"] = True


# ─────────────────────────────────────────
# MAIN FUNCTION — /test endpoint se call hoga
# ─────────────────────────────────────────

async def process_test_video(admin_bot, friend_bot, video_url) -> dict:
    """
    Test trigger hone par:
    1. Groq se unique code banao
    2. Admin ko info bhejo
    3. Channel par sirf URL + Code bhejo (video nahi)
    """
    result = {"success": False, "code": None, "error": None}

    try:
        from config import ADMIN_CHAT_ID, FRIEND_CHAT_ID

        print("🚀 Test processing shuru...")
        print(f"📎 URL: {video_url}")

        # ── 1. Unique code banao ──
        code = generate_unique_code()
        result["code"] = code

        # Code store karo
        VALID_CODES[code] = {
            "url": video_url,
            "used": False
        }
        print(f"✅ Code ready: {code}")

        # ── 2. Admin ko info bhejo ──
        await admin_bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                "✅ *Test Trigger Successful!*\n\n"
                f"🔗 URL: `{video_url}`\n"
                f"🔑 Unique Code: `{code}`\n\n"
                "📤 Channel par URL + Code bhej diya!"
            ),
            parse_mode="Markdown"
        )
        print("✅ Admin ko message bheja")

        # ── 3. Channel par sirf URL + Code bhejo ──
        await friend_bot.send_message(
            chat_id=FRIEND_CHAT_ID,
            text=(
                "🎬 *Naya Video URL Aaya!*\n\n"
                f"🔗 URL:\n`{video_url}`\n\n"
                f"🔑 Unique Code: `{code}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📌 Ye code yaad rakhna!\n"
                "Edited MP4 bhejte waqt caption mein likho:\n"
                f"`{code}`\n\n"
                "✅ Sahi code = post schedule hoga\n"
                "❌ Galat code = post nahi hoga"
            ),
            parse_mode="Markdown"
        )
        print("✅ Channel par URL + Code bheja")

        result["success"] = True
        log_action("VideoHandler", f"Test complete — Code: {code}", "Success")
        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        result["error"] = str(e)
        log_action("VideoHandler", f"Test error: {str(e)}", "Error")
        return result


# ─────────────────────────────────────────
# FUTURE — Yahan add hoga:
# async def process_with_video_download(...):
#     """yt-dlp se video download karke channel par bhejo"""
#     pass
# ─────────────────────────────────────────

