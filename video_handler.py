"""
video_handler.py
────────────────────────────────────────────────
Kaam:
  1. URL se video download karo (yt-dlp)
  2. Groq AI se unique code banao
  3. Admin + Friend Bot par bhejo

Future mein yahan aur automation add ho sakti hai.
"""

import os
import asyncio
import tempfile
import subprocess
from groq import Groq
from config import GROQ_API_KEY, TEST_VIDEO_URL
from sheets import log_action

# ─────────────────────────────────────────
# IN-MEMORY STORE — Valid codes yahan rahenge
# Format: { "LMZT-7X9K": { "url": "...", "downloaded": True/False } }
# Future mein Google Sheets mein move kar sakte hain
# ─────────────────────────────────────────

VALID_CODES = {}


# ─────────────────────────────────────────
# STEP 1 — GROQ SE UNIQUE CODE BANAO
# ─────────────────────────────────────────

def generate_unique_code() -> str:
    """
    Groq AI se ek unique 8-character code banao.
    Format: LMZT-XXXX (4 letters + dash + 4 alphanumeric)
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)

        # Already used codes bhejo taaki duplicate na ho
        used_codes = list(VALID_CODES.keys())
        used_str = ", ".join(used_codes) if used_codes else "none"

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a unique code generator. "
                        "Generate a single unique code in the format: LMZT-XXXX "
                        "where XXXX is exactly 4 random uppercase alphanumeric characters (A-Z, 0-9). "
                        "Reply with ONLY the code, nothing else. No explanation, no punctuation."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Generate a new unique code. "
                        f"These codes are already used (do NOT repeat them): {used_str}. "
                        f"Reply with ONLY the code like: LMZT-A3K9"
                    )
                }
            ],
            max_tokens=20,
            temperature=1.0  # High temperature = more random codes
        )

        code = response.choices[0].message.content.strip().upper()

        # Validate format — LMZT-XXXX
        if code.startswith("LMZT-") and len(code) == 9:
            print(f"✅ Groq ne code banaya: {code}")
            log_action("VideoHandler", f"Unique code generated: {code}", "Success")
            return code
        else:
            # Agar format galat aaya toh fallback
            print(f"⚠️ Groq ka format galat tha: '{code}' — fallback use kar raha hoon")
            return _fallback_code()

    except Exception as e:
        print(f"❌ Groq error: {e}")
        log_action("VideoHandler", f"Groq error, using fallback: {str(e)}", "Warning")
        return _fallback_code()


def _fallback_code() -> str:
    """
    Agar Groq fail ho toh Python se random code banao.
    """
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=4))
    code = f"LMZT-{suffix}"

    # Already exist karta hai? Dobara try karo
    attempts = 0
    while code in VALID_CODES and attempts < 10:
        suffix = ''.join(random.choices(chars, k=4))
        code = f"LMZT-{suffix}"
        attempts += 1

    print(f"🔄 Fallback code: {code}")
    return code


# ─────────────────────────────────────────
# STEP 2 — YT-DLP SE VIDEO DOWNLOAD KARO
# ─────────────────────────────────────────

def download_video(url: str) -> str | None:
    """
    yt-dlp se video download karo.
    Returns: downloaded file ka path (temp file)
    Returns: None if failed
    """
    try:
        # Temp folder mein save karo
        temp_dir = tempfile.mkdtemp(prefix="lazamat_")
        output_template = os.path.join(temp_dir, "video.%(ext)s")

        print(f"📥 Video download ho raha hai: {url}")
        log_action("VideoHandler", f"Downloading video: {url}", "Started")

        # yt-dlp command — Instagram ke liye best settings
        cmd = [
            "yt-dlp",
            "--format", "mp4/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--output", output_template,
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "--merge-output-format", "mp4",
            url
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode != 0:
            print(f"❌ yt-dlp error: {result.stderr}")
            log_action("VideoHandler", f"yt-dlp failed: {result.stderr[:100]}", "Error")
            return None

        # Downloaded file dhundo
        for fname in os.listdir(temp_dir):
            if fname.startswith("video") and fname.endswith(".mp4"):
                full_path = os.path.join(temp_dir, fname)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                print(f"✅ Video download ho gaya: {full_path} ({size_mb:.1f} MB)")
                log_action("VideoHandler", f"Video downloaded: {size_mb:.1f} MB", "Success")
                return full_path

        # .mp4 nahi mila, koi bhi video file dhundo
        for fname in os.listdir(temp_dir):
            full_path = os.path.join(temp_dir, fname)
            if os.path.isfile(full_path):
                print(f"✅ Video download ho gaya (non-mp4): {full_path}")
                return full_path

        print("❌ Download folder mein koi video nahi mili")
        log_action("VideoHandler", "Downloaded file not found", "Error")
        return None

    except subprocess.TimeoutExpired:
        print("❌ Download timeout (2 min)")
        log_action("VideoHandler", "Download timeout", "Error")
        return None
    except Exception as e:
        print(f"❌ Download error: {e}")
        log_action("VideoHandler", f"Download exception: {str(e)}", "Error")
        return None


# ─────────────────────────────────────────
# STEP 3 — CODE VALIDATE KARO
# ─────────────────────────────────────────

def is_valid_code(code: str) -> bool:
    """
    Check karo ki code valid hai ya nahi.
    Sirf VALID_CODES dict mein jo hain vohi valid hain.
    """
    return code.upper().strip() in VALID_CODES


def get_code_info(code: str) -> dict | None:
    """
    Code ki info return karo.
    """
    return VALID_CODES.get(code.upper().strip(), None)


def mark_code_used(code: str):
    """
    Code use ho gaya — mark karo taaki dubara post na ho.
    """
    code = code.upper().strip()
    if code in VALID_CODES:
        VALID_CODES[code]["used"] = True
        print(f"✅ Code {code} use hua — mark kar diya")


# ─────────────────────────────────────────
# MAIN FUNCTION — Test trigger hone par chalega
# ─────────────────────────────────────────

async def process_test_video(admin_bot, friend_bot) -> dict:
    """
    /test endpoint se call hoga.

    Kya karta hai:
    1. TEST_VIDEO_URL se video download karo (yt-dlp)
    2. Groq se unique code banao
    3. Admin bot par info bhejo
    4. Friend bot par video + code bhejo

    Future mein: yahan alag alag automation scenarios add kar sakte hain.
    """
    result = {"success": False, "code": None, "error": None}

    try:
        from config import ADMIN_CHAT_ID, FRIEND_CHAT_ID

        print("🚀 Test video processing shuru...")
        print(f"📎 URL: {TEST_VIDEO_URL}")

        # ── 1. Unique code banao ──
        code = generate_unique_code()
        result["code"] = code

        # ── 2. VALID_CODES mein save karo ──
        VALID_CODES[code] = {
            "url": TEST_VIDEO_URL,
            "used": False,
            "source": "test"
        }
        print(f"💾 Code save ho gaya: {code}")

        # ── 3. Video download karo ──
        video_path = download_video(TEST_VIDEO_URL)

        if not video_path:
            # Download fail — Admin ko batao
            await admin_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    "❌ *Test Video Download Failed!*\n\n"
                    f"URL: `{TEST_VIDEO_URL}`\n\n"
                    "yt-dlp se video nahi mili.\n"
                    "Reasons: Instagram login required / URL expired."
                ),
                parse_mode="Markdown"
            )
            result["error"] = "Video download failed"
            log_action("VideoHandler", "Test failed — download error", "Error")
            return result

        # ── 4. Admin Bot par info bhejo ──
        await admin_bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                "✅ *Test Trigger — Video Ready!*\n\n"
                f"🔗 URL: `{TEST_VIDEO_URL}`\n"
                f"🔑 Unique Code: `{code}`\n\n"
                "📤 Friend Bot par video + code bhej raha hoon...\n\n"
                "📌 *Dost ko yahi code dena hoga:*\n"
                f"`{code}`\n\n"
                "Jab dost MP4 + ye code bhejega tab automatically post hoga."
            ),
            parse_mode="Markdown"
        )
        print("✅ Admin ko info bhej di")

        # ── 5. Friend Bot par video bhejo ──
        with open(video_path, "rb") as video_file:
            await friend_bot.send_video(
                chat_id=FRIEND_CHAT_ID,
                video=video_file,
                caption=(
                    f"🎬 *Naya Video Aaya!*\n\n"
                    f"🔑 Unique Code: `{code}`\n\n"
                    "📌 *Ye code yaad rakhna!*\n"
                    "Jab edited MP4 bhejoge — saath mein sirf ye code likho:\n"
                    f"`{code}`\n\n"
                    "Code sahi hoga tabhi post schedule hoga. ✅\n"
                    "Code galat = post nahi hoga. ❌"
                ),
                parse_mode="Markdown"
            )
        print("✅ Friend Bot par video bhej di")

        # ── 6. Temp file clean karo ──
        try:
            import shutil
            temp_dir = os.path.dirname(video_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("🧹 Temp file clean ho gaya")
        except Exception:
            pass  # Cleanup fail ho toh bhi chalega

        result["success"] = True
        log_action("VideoHandler", f"Test complete — Code: {code}", "Success")
        print(f"🎉 Test complete! Code: {code}")
        return result

    except Exception as e:
        print(f"❌ process_test_video error: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
        log_action("VideoHandler", f"Test exception: {str(e)}", "Error")
        return result


# ─────────────────────────────────────────
# FUTURE — Yahan aur functions add karna:
#
# async def process_scheduled_video(...):
#     """Automated daily video processing"""
#     pass
#
# async def process_bulk_videos(...):
#     """Multiple URLs ek saath"""
#     pass
# ─────────────────────────────────────────
