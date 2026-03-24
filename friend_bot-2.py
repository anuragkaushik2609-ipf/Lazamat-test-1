import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from config import FRIEND_BOT_TOKEN, ADMIN_CHAT_ID, FRIEND_CHAT_ID
from sheets import (
    get_all_products,
    add_to_schedule,
    check_already_posted,
    log_action
)
from admin_bot import (
    send_video_received_alert,
    send_wrong_product_alert
)

# ─────────────────────────────────────────
# POSTING SCHEDULE — India Time
# ─────────────────────────────────────────

POSTING_SCHEDULE = {
    "Instagram": "21:30",
    "TikTok": "22:30",
    "Facebook": "23:30",
    "YouTube": "00:30",
    "Pinterest": "01:30"
}

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *LAMAZAT CANVAS — Friend Bot*\n\n"
        "Yahan videos aayenge posting ke liye.\n\n"
        "📌 *Video bhejne ka tarika:*\n"
        "1. Bot par jo video aaye usse edit karo\n"
        "2. Edited MP4 is bot par bhejo\n"
        "3. Video ke caption mein unique code likho\n\n"
        "✅ *Example caption:*\n"
        "`LMZT-A3K9`\n\n"
        "⚠️ Code sahi hoga tabhi post schedule hoga.\n"
        "Code galat = post nahi hoga!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────
# VIDEO RECEIVE HANDLER — WITH UNIQUE CODE VALIDATION
# ─────────────────────────────────────────

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # ── Video check ──
    video = message.video or message.document
    if not video:
        await message.reply_text("❌ Sirf MP4 video bhejo.")
        return

    # ── Caption check ──
    caption = (message.caption or "").strip()

    if not caption:
        await message.reply_text(
            "❌ *Code nahi mila!*\n\n"
            "Video ke saath unique code likhna zaroori hai.\n"
            "Example: `LMZT-A3K9`\n\n"
            "Code tumhe bot par pehle se bheja gaya hoga. 🔍",
            parse_mode="Markdown"
        )
        return

    # ── Caption parse karo — code dhundo ──
    # Caption mein sirf code hoga ya code + kuch aur
    # LMZT-XXXX format match karo
    import re
    code_match = re.search(r'LMZT-[A-Z0-9]{4}', caption.upper())

    if not code_match:
        await message.reply_text(
            "❌ *Valid code nahi mila!*\n\n"
            "Code format: `LMZT-XXXX`\n"
            "Example: `LMZT-A3K9`\n\n"
            "Sahi code likho aur dobara bhejo.",
            parse_mode="Markdown"
        )
        log_action("Friend Bot", f"Invalid code format in caption: {caption}", "Error")
        return

    submitted_code = code_match.group(0)

    # ── Unique Code Validate karo ──
    from video_handler import is_valid_code, get_code_info, mark_code_used

    if not is_valid_code(submitted_code):
        await message.reply_text(
            f"❌ *Code `{submitted_code}` valid nahi hai!*\n\n"
            "Ye code ya toh:\n"
            "• Galat hai\n"
            "• Expire ho gaya\n"
            "• Pehle use ho chuka hai\n\n"
            "Sahi code check karo — tumhe bot par message aaya hoga.",
            parse_mode="Markdown"
        )
        log_action("Friend Bot", f"Invalid/expired code: {submitted_code}", "Error")
        return

    # ── Check karo already used toh nahi ──
    code_info = get_code_info(submitted_code)
    if code_info and code_info.get("used"):
        await message.reply_text(
            f"⚠️ *Code `{submitted_code}` pehle use ho chuka hai!*\n\n"
            "Ek code sirf ek baar kaam karta hai.\n"
            "Nayi video ke liye naya code lena hoga.",
            parse_mode="Markdown"
        )
        log_action("Friend Bot", f"Code already used: {submitted_code}", "Error")
        return

    # ── Code valid hai — Schedule mein daalo ──
    file_id = video.file_id
    product_name = f"Video-{submitted_code}"  # Test mein product name nahi hoga

    # Code use mark karo
    mark_code_used(submitted_code)

    # Saare platforms ke liye schedule
    scheduled_platforms = []
    for platform, time_str in POSTING_SCHEDULE.items():
        success = add_to_schedule(
            product_id=submitted_code,
            video_file_id=file_id,
            product_name=product_name,
            platform=platform,
            scheduled_time=time_str
        )
        if success:
            scheduled_platforms.append(f"{platform} — {time_str}")

    if scheduled_platforms:
        schedule_text = "\n".join([f"✅ {s}" for s in scheduled_platforms])
        await message.reply_text(
            f"🎉 *Video Schedule Ho Gayi!*\n\n"
            f"Code: `{submitted_code}`\n\n"
            f"*Posting Schedule:*\n"
            f"{schedule_text}\n\n"
            f"Sab India time mein hai. 🇮🇳",
            parse_mode="Markdown"
        )

        # Admin ko alert
        app = context.application
        await send_video_received_alert(
            app.bot,
            submitted_code,
            product_name,
            scheduled_platforms[0]
        )

        log_action("Friend Bot", f"Video scheduled with code: {submitted_code}", "Success")

    else:
        await message.reply_text(
            "❌ Schedule mein add nahi hua — Admin ko batao.",
        )
        log_action("Friend Bot", f"Schedule add failed for code: {submitted_code}", "Error")

# ─────────────────────────────────────────
# PRODUCT SEND — Automation se call hoga
# ─────────────────────────────────────────

async def send_product_to_friend(bot, products):
    text = (
        "🎯 *Aaj Ke Top 4 Products*\n\n"
        "In 4 products ki video edit karni hai.\n"
        "Deadline — Sham 7 baje\n\n"
    )

    for i, p in enumerate(products[:4], 1):
        text += (
            f"{i}. *{p.get('name', 'N/A')}*\n"
            f"   ID: `{p.get('product_id', 'N/A')}`\n"
            f"   Price: EUR {p.get('price_eur', 'N/A')}\n"
            f"   CJ Video: {p.get('cj_video_url', 'N/A')}\n\n"
        )

    text += (
        "📌 *Video bhejne ka tarika:*\n"
        "MP4 bhejo + caption mein Product ID likho\n"
        "Example caption: `LAM-1234`"
    )

    # Friend bot ka chat ID — yahan Admin Chat ID use karenge
    # Future mein alag friend chat ID add kar sakte hain
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=text,
        parse_mode="Markdown"
    )

    log_action("Friend Bot", f"Top 4 products sent to friend", "Success")

# ─────────────────────────────────────────
# MAIN — BOT START
# ─────────────────────────────────────────

def create_friend_app():
    """Application object banao — main.py use karega asyncio mein"""
    app = Application.builder().token(FRIEND_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.MimeType("video/mp4"), handle_video))

    log_action("Friend Bot", "Bot initialized", "Success")
    return app

def main():
    """Standalone chalane ke liye"""
    app = create_friend_app()
    print("✅ Friend Bot chal raha hai...")
    app.run_polling()

if __name__ == "__main__":
    main()
