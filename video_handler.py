"""
video_handler.py
────────────────────────────────────────────────
Kaam:
  1. URL se video download karo (yt-dlp)
  2. Groq AI se unique code banao
  3. Admin + Friend Bot par bhejo
"""

import os
import tempfile
import subprocess
from groq import Groq
from config import GROQ_API_KEY
from sheets import log_action

# ─────────────────────────────────────────
# IN-MEMORY STORE
# ─────────────────────────────────────────
VALID_CODES = {}


# ─────────────────────────────────────────
# STEP 1 — UNIQUE CODE
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
# STEP 2 — DOWNLOAD VIDEO
# ─────────────────────────────────────────

def download_video(url: str) -> str | None:
    try:
        temp_dir = tempfile.mkdtemp(prefix="lazamat_")
        output_template = os.path.join(temp_dir, "video.%(ext)s")

        cmd = [
            "yt-dlp",
            "--format", "mp4/best",
            "--output", output_template,
            "--no-playlist",
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            log_action("VideoHandler", f"yt-dlp error: {result.stderr}", "Error")
            return None

        for file in os.listdir(temp_dir):
            if file.endswith(".mp4"):
                return os.path.join(temp_dir, file)

        return None

    except Exception as e:
        log_action("VideoHandler", f"Download error: {str(e)}", "Error")
        return None


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
# MAIN FUNCTION
# ─────────────────────────────────────────

async def process_test_video(admin_bot, friend_bot, video_url) -> dict:
    result = {"success": False, "code": None, "error": None}

    try:
        from config import ADMIN_CHAT_ID, FRIEND_CHAT_ID

        print("🚀 Processing started...")
        print(f"📎 URL: {video_url}")

        # 1. Code
        code = generate_unique_code()
        result["code"] = code

        VALID_CODES[code] = {
            "url": video_url,
            "used": False
        }

        # 2. Download
        video_path = download_video(video_url)

        if not video_path:
            await admin_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"❌ Download failed:\n{video_url}"
            )
            result["error"] = "Download failed"
            return result

        # 3. Admin notify
        await admin_bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"✅ Video Ready\nCode: `{code}`",
            parse_mode="Markdown"
        )

        # 4. Send to friend
        with open(video_path, "rb") as f:
            await friend_bot.send_video(
                chat_id=FRIEND_CHAT_ID,
                video=f,
                caption=f"🎬 Code: `{code}`",
                parse_mode="Markdown"
            )

        # 5. Cleanup
        import shutil
        shutil.rmtree(os.path.dirname(video_path), ignore_errors=True)

        result["success"] = True
        return result

    except Exception as e:
        result["error"] = str(e)
        log_action("VideoHandler", str(e), "Error")
        return result
