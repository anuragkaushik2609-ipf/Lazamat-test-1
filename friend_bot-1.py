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
from config import FRIEND_BOT_TOKEN, ADMIN_CHAT_ID
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
        "Yahan aaj ke products milenge.\n\n"
        "Video bhejne ka tarika:\n"
        "1. Video edit karo — MP4\n"
        "2. Is bot pe MP4 bhejo\n"
        "3. Video ke saath Product ID likho\n\n"
        "Example:\n"
        "`LAM-1234`\n\n"
        "Deadline — Sham 7 baje tak!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────
# VIDEO RECEIVE HANDLER
# ─────────────────────────────────────────

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Video check karo
    video = message.video or message.document
    if not video:
        await message.reply_text("❌ Sirf MP4 video bhejo.")
        return

    # Product ID check karo — caption mein hona chahiye
    caption = message.caption or ""
    caption = caption.strip()

    if not caption:
        await message.reply_text(
            "❌ *Product ID nahi mila!*\n\n"
            "Video ke saath Product ID likho.\n"
            "Example: `LAM-1234`",
            parse_mode="Markdown"
        )
        return

    # Sheet se product match karo
    product_id = caption.upper().strip()
    products = get_all_products()
    matched_product = None

    for p in products:
        if str(p.get("product_id", "")).upper() == product_id:
            matched_product = p
            break

    # Match nahi mila
    if not matched_product:
        active_ids = [str(p.get("product_id", "")) for p in products if p.get("status") == "Active"]

        # Admin ko alert bhejo
        app = context.application
        await send_wrong_product_alert(
            app.bot,
            caption,
            active_ids
        )

        await message.reply_text(
            f"❌ *Product ID '{product_id}' nahi mila!*\n\n"
            f"Admin ko alert bhej diya.\n"
            f"Sahi Product ID check karo aur dobara bhejo.",
            parse_mode="Markdown"
        )
        log_action("Friend Bot", f"Wrong product ID: {product_id}", "Error")
        return

    # Pehle se posted check karo
    already_posted = False
    for platform in POSTING_SCHEDULE.keys():
        if check_already_posted(product_id, platform):
            already_posted = True
            break

    if already_posted:
        await message.reply_text(
            f"⚠️ *Product {product_id} already scheduled hai!*\n\n"
            f"Ye product pehle se kisi platform pe post ho chuka hai ya schedule mein hai.",
            parse_mode="Markdown"
        )
        return

    # Telegram file_id save karo
    file_id = video.file_id
    product_name = matched_product.get("name", "Unknown")

    # Saare platforms ke liye schedule mein daalo
    scheduled_platforms = []
    for platform, time_str in POSTING_SCHEDULE.items():
        success = add_to_schedule(
            product_id=product_id,
            video_file_id=file_id,
            product_name=product_name,
            platform=platform,
            scheduled_time=time_str
        )
        if success:
            scheduled_platforms.append(f"{platform} — {time_str}")

    if scheduled_platforms:
        # Dost ko confirmation
        schedule_text = "\n".join([f"✅ {s}" for s in scheduled_platforms])
        await message.reply_text(
            f"🎉 *Video Schedule Ho Gayi!*\n\n"
            f"Product: {product_name}\n"
            f"ID: {product_id}\n\n"
            f"*Posting Schedule:*\n"
            f"{schedule_text}\n\n"
            f"Sab India time mein hai.",
            parse_mode="Markdown"
        )

        # Admin ko alert bhejo
        app = context.application
        await send_video_received_alert(
            app.bot,
            product_id,
            product_name,
            scheduled_platforms[0]
        )

        log_action("Friend Bot", f"Video received and scheduled: {product_id} — {product_name}", "Success")
    else:
        await message.reply_text(
            "❌ Schedule mein add nahi hua — Admin ko check karne kaho.",
        )
        log_action("Friend Bot", f"Schedule add failed: {product_id}", "Error")

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
