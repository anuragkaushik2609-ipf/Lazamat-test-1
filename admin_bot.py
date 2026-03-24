import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from config import ADMIN_BOT_TOKEN, ADMIN_CHAT_ID
from sheets import (
    get_early_pool_count,
    get_all_products,
    delete_product,
    get_api_usage,
    get_automation_flag,
    set_automation_flag,
    log_action
)

# ─────────────────────────────────────────
# SECURITY CHECK — sirf admin use kar sake
# ─────────────────────────────────────────

def is_admin(update: Update) -> bool:
    return str(update.effective_chat.id) == str(ADMIN_CHAT_ID)

# ─────────────────────────────────────────
# START — MAIN MENU
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("Access denied.")
        return

    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("🛒 Early Pool", callback_data="early_pool")],
        [InlineKeyboardButton("⏹ Stop Button", callback_data="stop_menu"),
         InlineKeyboardButton("🗑 Delete Product", callback_data="delete_menu")],
        [InlineKeyboardButton("📈 API Limits", callback_data="api_limits")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "👋 *LAMAZAT CANVAS — Admin Bot*\n\nKya karna hai?"

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ─────────────────────────────────────────
# STATUS
# ─────────────────────────────────────────

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    auto1 = get_automation_flag("Automation1")
    auto2 = get_automation_flag("Automation2")
    filter_bot = get_automation_flag("FilterBot")

    def flag_emoji(flag):
        if flag is None:
            return "⚪ Unknown"
        if flag["status"] == "Running":
            return "🟢 Running"
        elif flag["status"] == "Stopped":
            stop_until = flag.get("stop_until", "")
            return f"🔴 Stopped until {stop_until}"
        return "⚪ Unknown"

    text = (
        "📊 *Automation Status*\n\n"
        f"Automation 1: {flag_emoji(auto1)}\n"
        f"Automation 2: {flag_emoji(auto2)}\n"
        f"Filter Bot: {flag_emoji(filter_bot)}\n"
    )

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ─────────────────────────────────────────
# EARLY POOL COUNT
# ─────────────────────────────────────────

async def show_early_pool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    count = get_early_pool_count()

    text = (
        "🛒 *Early Pool Count*\n\n"
        f"Total: {count['total']} / 300\n\n"
        f"Viral (20%): {count['viral']}\n"
        f"Medium (50%): {count['medium']}\n"
        f"Evergreen (30%): {count['evergreen']}\n"
    )

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ─────────────────────────────────────────
# API LIMITS
# ─────────────────────────────────────────

async def show_api_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    apis = [
        ("CJ Dropshipping", 1000),
        ("YouTube Data API", 10000),
        ("Groq API", 14400),
        ("Google Sheets API", 500),
        ("Instagram Playwright", 1000),
        ("TikTok Playwright", 2000),
        ("Brevo Email", 300),
    ]

    text = "📈 *API Limits Today*\n\n"

    for api_name, daily_limit in apis:
        usage = get_api_usage(api_name)
        if usage:
            used = usage.get("used_today", 0)
            percent = int((int(used) / daily_limit) * 100)
            if percent >= 80:
                emoji = "🔴"
            elif percent >= 50:
                emoji = "🟡"
            else:
                emoji = "🟢"
            text += f"{emoji} {api_name}: {used}/{daily_limit} ({percent}%)\n"
        else:
            text += f"⚪ {api_name}: No data\n"

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ─────────────────────────────────────────
# STOP BUTTON — STEP 1 — Kaunsa automation?
# ─────────────────────────────────────────

async def show_stop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Automation 1", callback_data="stop_select_Automation1")],
        [InlineKeyboardButton("Automation 2", callback_data="stop_select_Automation2")],
        [InlineKeyboardButton("Filter Bot", callback_data="stop_select_FilterBot")],
        [InlineKeyboardButton("Dono (1 + 2)", callback_data="stop_select_Both")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        "⏹ *Stop Button*\n\nKaunsa automation band karna hai?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────
# STOP BUTTON — STEP 2 — Kitni der?
# ─────────────────────────────────────────

async def show_stop_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # automation name save karo context mein
    automation = query.data.replace("stop_select_", "")
    context.user_data["stop_automation"] = automation

    keyboard = [
        [InlineKeyboardButton("1 Ghanta", callback_data="stop_dur_1"),
         InlineKeyboardButton("2 Ghante", callback_data="stop_dur_2")],
        [InlineKeyboardButton("6 Ghante", callback_data="stop_dur_6"),
         InlineKeyboardButton("12 Ghante", callback_data="stop_dur_12")],
        [InlineKeyboardButton("Custom Time", callback_data="stop_dur_custom")],
        [InlineKeyboardButton("🔙 Back", callback_data="stop_menu")]
    ]

    await query.edit_message_text(
        f"⏱ *{automation} — Kitni der band karna hai?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────
# STOP BUTTON — STEP 3 — Execute stop
# ─────────────────────────────────────────

async def execute_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    duration_str = query.data.replace("stop_dur_", "")

    if duration_str == "custom":
        context.user_data["waiting_custom_time"] = True
        await query.edit_message_text(
            "⏱ *Custom time likho — ghanton mein*\n\nExample: 3 (3 ghante ke liye)",
            parse_mode="Markdown"
        )
        return

    duration = int(duration_str)
    automation = context.user_data.get("stop_automation", "")

    await process_stop(query, context, automation, duration)

async def process_stop(query_or_message, context, automation, duration):
    stop_until = datetime.now() + timedelta(hours=duration)
    stop_until_str = stop_until.strftime("%Y-%m-%d %H:%M")

    if automation == "Both":
        set_automation_flag("Automation1", "Stopped", stop_until_str)
        set_automation_flag("Automation2", "Stopped", stop_until_str)
        names = "Automation 1 + Automation 2"
    else:
        set_automation_flag(automation, "Stopped", stop_until_str)
        names = automation

    log_action("Stop Button", f"{names} stopped for {duration} hours", "Success")

    text = (
        f"🔴 *{names} band kar diya!*\n\n"
        f"Duration: {duration} ghante\n"
        f"Resume hoga: {stop_until_str}\n\n"
        f"1 ghante pehle reminder milega."
    )

    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]

    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await query_or_message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # Resume reminder schedule karo
    context.application.job_queue.run_once(
        resume_reminder,
        when=timedelta(hours=duration - 1),
        data={"automation": automation, "names": names, "stop_until": stop_until_str}
    )

    # Auto resume schedule karo
    context.application.job_queue.run_once(
        auto_resume,
        when=timedelta(hours=duration),
        data={"automation": automation, "names": names}
    )

# ─────────────────────────────────────────
# RESUME REMINDER (1 ghante pehle)
# ─────────────────────────────────────────

async def resume_reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"⏰ *Reminder — 1 ghanta bacha!*\n\n"
            f"{data['names']} 1 ghante mein resume hoga.\n"
            f"Resume time: {data['stop_until']}"
        ),
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────
# AUTO RESUME
# ─────────────────────────────────────────

async def auto_resume(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    automation = data["automation"]
    names = data["names"]

    if automation == "Both":
        set_automation_flag("Automation1", "Running")
        set_automation_flag("Automation2", "Running")
    else:
        set_automation_flag(automation, "Running")

    log_action("Auto Resume", f"{names} resumed", "Success")

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🟢 *{names} resume ho gaya!*",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────
# CUSTOM TIME HANDLER
# ─────────────────────────────────────────

async def handle_custom_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    if context.user_data.get("waiting_custom_time"):
        try:
            duration = int(update.message.text.strip())
            automation = context.user_data.get("stop_automation", "")
            context.user_data["waiting_custom_time"] = False
            await process_stop(update.message, context, automation, duration)
        except ValueError:
            await update.message.reply_text("❌ Sirf number likho — jaise: 3")

# ─────────────────────────────────────────
# DELETE PRODUCT
# ─────────────────────────────────────────

async def show_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    products = get_all_products()
    active_products = [p for p in products if p.get("status") == "Active"][:10]

    if not active_products:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ Koi active product nahi hai.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = []
    for p in active_products:
        keyboard.append([InlineKeyboardButton(
            f"{p['product_id']} — {p['name'][:20]}",
            callback_data=f"delete_confirm_{p['product_id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

    await query.edit_message_text(
        "🗑 *Product Delete Karo*\n\nKaunsa product delete karna hai?\n(Top 10 active products dikh rahe hain)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.replace("delete_confirm_", "")

    keyboard = [
        [InlineKeyboardButton("✅ Haan, Delete Karo", callback_data=f"delete_yes_{product_id}"),
         InlineKeyboardButton("❌ Nahi", callback_data="delete_menu")]
    ]

    await query.edit_message_text(
        f"⚠️ *Product ID: {product_id}*\n\nPakka delete karna hai?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.replace("delete_yes_", "")
    success = delete_product(product_id)

    if success:
        text = f"✅ Product {product_id} delete ho gaya!"
    else:
        text = f"❌ Delete nahi hua — Product {product_id} nahi mila."

    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ─────────────────────────────────────────
# CALLBACK ROUTER — sab buttons yahan se route honge
# ─────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    query = update.callback_query
    data = query.data

    if data == "main_menu":
        await show_main_menu(update, context)
    elif data == "status":
        await show_status(update, context)
    elif data == "early_pool":
        await show_early_pool(update, context)
    elif data == "api_limits":
        await show_api_limits(update, context)
    elif data == "stop_menu":
        await show_stop_menu(update, context)
    elif data.startswith("stop_select_"):
        await show_stop_duration(update, context)
    elif data.startswith("stop_dur_"):
        await execute_stop(update, context)
    elif data == "delete_menu":
        await show_delete_menu(update, context)
    elif data.startswith("delete_confirm_"):
        await confirm_delete(update, context)
    elif data.startswith("delete_yes_"):
        await execute_delete(update, context)

# ─────────────────────────────────────────
# ALERT FUNCTIONS — Automation se call honge
# ─────────────────────────────────────────

async def send_alert(bot, message):
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=message,
        parse_mode="Markdown"
    )

async def send_top4_alert(bot, products):
    text = "🏆 *Top 4 Products — Is Session Ke*\n\n"
    for i, p in enumerate(products[:4], 1):
        text += (
            f"{i}. *{p.get('name', 'N/A')}*\n"
            f"   ID: {p.get('product_id', 'N/A')}\n"
            f"   Score: {p.get('score', 'N/A')}\n"
            f"   Price: EUR {p.get('price_eur', 'N/A')}\n"
            f"   Type: {p.get('type', 'N/A')}\n\n"
        )
    await send_alert(bot, text)

async def send_price_change_alert(bot, product_id, product_name, old_price, new_price, change_percent):
    if change_percent >= 30:
        emoji = "🔴 URGENT"
        action = "Auto hide kar diya — 3 din mein decision lo"
    elif change_percent >= 15:
        emoji = "🟡 WARNING"
        action = "Check karo — decision lo"
    else:
        emoji = "🟢 INFO"
        action = "Auto update ho gaya"

    text = (
        f"{emoji} *Price Change Alert*\n\n"
        f"Product: {product_name}\n"
        f"ID: {product_id}\n"
        f"Old Price: EUR {old_price}\n"
        f"New Price: EUR {new_price}\n"
        f"Change: {change_percent}%\n"
        f"Action: {action}"
    )
    await send_alert(bot, text)

async def send_stock_alert(bot, product_id, product_name, stock_level):
    text = (
        f"📦 *Low Stock Alert*\n\n"
        f"Product: {product_name}\n"
        f"ID: {product_id}\n"
        f"Stock: {stock_level} units bache hain\n"
        f"Action: Auto hide kar diya"
    )
    await send_alert(bot, text)

async def send_api_limit_alert(bot, api_name, used, total):
    percent = int((used / total) * 100)
    text = (
        f"⚠️ *API Limit Alert — {api_name}*\n\n"
        f"Used: {used}/{total} ({percent}%)\n"
        f"Low priority checks band kar diye"
    )
    await send_alert(bot, text)

async def send_ban_alert(bot, platform, account):
    text = (
        f"🚫 *Account Ban Alert*\n\n"
        f"Platform: {platform}\n"
        f"Account: {account}\n"
        f"Action: Naya account banao — process document mein hai"
    )
    await send_alert(bot, text)

async def send_video_missing_alert(bot):
    text = (
        "⏰ *Video Alert — Raat 8 Baje*\n\n"
        "Dost ne abhi tak video nahi bheji!\n\n"
        "Options:\n"
        "1. Dost ko remind karo\n"
        "2. Stop click karo — aaj ki posting skip\n\n"
        "Raat 9 baje tak video nahi aayi toh auto skip ho jaayega."
    )
    await send_alert(bot, text)

async def send_video_received_alert(bot, product_id, product_name, scheduled_time):
    text = (
        f"✅ *Video Receive Ho Gayi!*\n\n"
        f"Product: {product_name}\n"
        f"ID: {product_id}\n"
        f"Schedule: {scheduled_time}\n"
        f"Status: Post ke liye ready!"
    )
    await send_alert(bot, text)

async def send_wrong_product_alert(bot, received_name, expected_ids):
    text = (
        f"❌ *Wrong Product Name Alert*\n\n"
        f"Dost ne bheja: '{received_name}'\n"
        f"Sheet mein match nahi mila!\n\n"
        f"Available Product IDs:\n"
        f"{chr(10).join(expected_ids[:5])}\n\n"
        f"Dost ko sahi Product ID bhejne kaho."
    )
    await send_alert(bot, text)

# ─────────────────────────────────────────
# MAIN — BOT START
# ─────────────────────────────────────────

def main():
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))

    # Button handlers
    app.add_handler(CallbackQueryHandler(button_handler))

    # Custom time text input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_time))

    print("✅ Admin Bot chal raha hai...")
    log_action("Admin Bot", "Bot started", "Success")

    app.run_polling()

if __name__ == "__main__":
    main()
