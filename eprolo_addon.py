"""
eprolo_addon.py — LAMAZAT CANVAS
────────────────────────────────────────────────
Eprolo Products Sheet se data lo aur automation1 ke
run_session() ke baad Early Pool mein add karo.

Eprolo = main source — Sheet se scrape kiya hua data
"""

import os
import re
import time
import hashlib
import asyncio
import requests
from datetime import datetime
from sheets import get_sheet, add_product, get_all_products, log_action
from automation1 import (
    check_pytrends_signal, check_order_growth_signal,
    check_facebook_ads_signal, check_social_signal_from_sheet,
    calculate_score, detect_category, detect_type,
    is_duplicate, MIN_PRICE_EUR, MIN_MARGIN_PCT
)
from config import ADMIN_CHAT_ID

# ─────────────────────────────────────────
# EPROLO PRODUCTS SHEET SE LO
# ─────────────────────────────────────────

def get_eprolo_products(min_signal="Medium"):
    """Eprolo Products tab se Strong/Medium products lo"""
    try:
        sheet = get_sheet()
        if not sheet:
            return []
        try:
            tab = sheet.worksheet("Eprolo Products")
        except Exception:
            log_action("Eprolo Addon", "Eprolo Products tab nahi mili", "Warning")
            return []

        records = tab.get_all_records()
        strong_levels = ["Strong"] if min_signal == "Strong" else ["Strong", "Medium"]
        result = [r for r in records if r.get("signal_strength") in strong_levels
                  and r.get("status") == "Active"]

        log_action("Eprolo Addon", f"{len(result)} Eprolo products found", "Info")
        return result

    except Exception as e:
        log_action("Eprolo Addon", f"Error: {e}", "Error")
        return []

# ─────────────────────────────────────────
# EPROLO → POOL MEIN ADD
# ─────────────────────────────────────────

async def process_eprolo_products(admin_bot_token):
    """
    Eprolo products ko signals check karke Early Pool mein add karo.
    run_session() ke baad call hoga.
    """
    log_action("Eprolo Addon", "Processing started", "Info")

    eprolo_products = get_eprolo_products()
    if not eprolo_products:
        log_action("Eprolo Addon", "No Eprolo products to process", "Info")
        return 0

    existing = get_all_products()
    added = 0

    for ep in eprolo_products[:8]:  # Max 8 per run
        try:
            name      = str(ep.get("name", ""))
            price_usd = float(ep.get("price_usd", 0) or 0)
            price_eur = float(ep.get("price_eur", price_usd * 0.92) or price_usd * 0.92)
            orders    = int(ep.get("orders", 0) or 0)
            image_url = str(ep.get("image_url", ""))
            video_url = str(ep.get("video_url", ""))
            ep_id     = str(ep.get("product_id", ""))

            if not name or price_eur < MIN_PRICE_EUR:
                continue

            # Margin estimate (Eprolo ka cost ~50% of sell price)
            cost_est   = price_eur * 0.50
            shipping   = 3.5
            gross      = price_eur - cost_est - shipping
            margin_pct = (gross / price_eur * 100) if price_eur > 0 else 0

            if margin_pct < 25:  # Eprolo ke liye thoda lenient
                log_action("Eprolo Addon", f"Low margin {margin_pct:.1f}%: {name[:30]}", "Skip")
                continue

            # Duplicate check
            img_hash = hashlib.md5(image_url.encode()).hexdigest()[:12] if image_url else ""
            if is_duplicate({"name": name, "price_eur": price_eur, "image_hash": img_hash}, existing):
                log_action("Eprolo Addon", f"Duplicate: {name[:30]}", "Skip")
                continue

            category = detect_category(name)
            keyword  = " ".join(name.split()[:3])

            # Signals check
            trend_ok, countries = check_pytrends_signal(keyword)
            time.sleep(1)
            order_ok   = orders >= 200  # Eprolo pe 200+ = good
            fb_ok, ad_count = check_facebook_ads_signal(keyword)
            social_ok, creators = check_social_signal_from_sheet(keyword)

            signals_data = {
                "countries_trending": countries,
                "orders": orders,
                "ad_count": ad_count,
                "creator_count": creators,
            }
            score = calculate_score(signals_data, {"price_eur": price_eur, "margin_pct": margin_pct})
            passed = sum([trend_ok, order_ok, fb_ok, social_ok])
            product_type = detect_type(orders, countries)

            if passed < 2:  # Eprolo ke liye 2+ signals kafi hai
                log_action("Eprolo Addon", f"Too few signals ({passed}/4): {name[:30]}", "Skip")
                continue

            product_id = f"EP-{ep_id}" if not ep_id.startswith("EP-") else ep_id

            new_product = {
                "product_id":   product_id,
                "name":         name,
                "category":     category,
                "type":         product_type,
                "score":        score,
                "video_url":    video_url,
                "price_eur":    round(price_eur, 2),
                "supplier":     "Eprolo",
                "signal_1":     "Yes" if trend_ok  else "No",
                "signal_2":     "Yes" if order_ok  else "No",
                "signal_3":     "Yes" if fb_ok     else "No",
                "signal_4":     "Yes" if social_ok else "No",
                "signal_5":     "No",
                "days_in_pool": 0,
                "status":       "Active",
                "source":       f"Eprolo (Orders:{orders})",
                "image_hash":   img_hash,
            }

            success = add_product(new_product)
            if success:
                added += 1
                existing.append(new_product)
                log_action("Eprolo Addon", f"Added: {name[:40]} Score:{score}", "Success")

                # Telegram alert
                await _send_alert(admin_bot_token, new_product, orders, passed, score, image_url)

            time.sleep(1)

        except Exception as e:
            log_action("Eprolo Addon", f"Error: {e}", "Error")
            continue

    log_action("Eprolo Addon", f"Done — {added} products added", "Success")
    return added

async def _send_alert(admin_bot_token, product, orders, passed, score, image_url):
    try:
        msg = (
            f"🛍️ *Eprolo Product Added!*\n\n"
            f"*{product['name']}*\n"
            f"Source: Eprolo\n"
            f"Orders: {orders:,}\n"
            f"Score: `{score}/100`\n"
            f"Signals: `{passed}/4`\n"
            f"Price: EUR {product['price_eur']}\n"
            f"Type: {product['type']}"
        )
        url = f"https://api.telegram.org/bot{admin_bot_token}/sendMessage"
        requests.post(url, json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)

        if image_url:
            requests.post(
                f"https://api.telegram.org/bot{admin_bot_token}/sendPhoto",
                json={"chat_id": ADMIN_CHAT_ID, "photo": image_url,
                      "caption": f"📸 {product['name'][:60]}"},
                timeout=10
            )
    except Exception as e:
        log_action("Eprolo Alert", f"Error: {e}", "Error")
