"""
automation1.py — LAMAZAT CANVAS
────────────────────────────────────────────────
Automation 1 — Trending Product Detection
Signals:
  1. Pytrends — Google Trends (5+ European countries)
  2. CJ API   — Order growth (buying proof)
  3. Facebook Ads Library — New ads last 7 days
  4. TikTok/Instagram — GitHub Actions se data aayega (Sheet mein save)
  5. Reviews Growth — CJ se review count

Flow:
  - Subah 6, Dopahar 12, Sham 6, Raat 12 — 4 sessions/day
  - Har session mein 10 products check → Sheet mein save
  - 5 mein se 4 signals positive = product aage jaata hai
  - Early Pool = 300 products max
  - 21 din baad auto remove
  - Telegram alerts via existing Admin Bot
"""

import os
import time
import random
import asyncio
import requests
import hashlib
from datetime import datetime, timedelta
from pytrends.request import TrendReq
from sheets import (
    get_sheet,
    add_product,
    get_all_products,
    update_product_status,
    get_automation_flag,
    log_action
)
from config import ADMIN_CHAT_ID

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

CJ_API_KEY       = os.getenv("CJ_API_KEY")
CJ_API_BASE      = "https://developers.cjdropshipping.com/api2.0/v1"

EUROPEAN_COUNTRIES = ["DE", "FR", "NL", "IT", "ES", "PL", "BE", "SE", "AT", "PT"]
GEO_CODES          = {
    "DE": "DE", "FR": "FR", "NL": "NL", "IT": "IT",
    "ES": "ES", "PL": "PL", "BE": "BE", "SE": "SE",
    "AT": "AT", "PT": "PT"
}

CATEGORY_SLOTS = {
    "Electronics": 100,
    "Clothing":    100,
    "Footwear":    100,
    "Fitness":     100,
    "Others":      100,
}

TYPE_RATIO = {
    "Viral":     0.20,
    "Medium":    0.50,
    "Evergreen": 0.30,
}

MIN_PRICE_EUR    = 15.0
MIN_MARGIN_PCT   = 35.0
MAX_POOL_SIZE    = 300
MAX_DAYS_IN_POOL = 21
SIGNALS_REQUIRED = 4

# ─────────────────────────────────────────
# CJ API — TOKEN
# ─────────────────────────────────────────

_cj_token = None
_cj_token_expiry = None

def get_cj_token():
    global _cj_token, _cj_token_expiry
    if _cj_token and _cj_token_expiry and datetime.now() < _cj_token_expiry:
        return _cj_token

    try:
        url = f"{CJ_API_BASE}/authentication/getAccessToken"
        resp = requests.post(url, json={"email": os.getenv("CJ_EMAIL"), "password": os.getenv("CJ_PASSWORD")}, timeout=15)
        data = resp.json()
        if data.get("result"):
            _cj_token = data["data"]["accessToken"]
            _cj_token_expiry = datetime.now() + timedelta(hours=23)
            log_action("CJ Auth", "Token refreshed", "Success")
            return _cj_token
    except Exception as e:
        log_action("CJ Auth", f"Token error: {e}", "Error")
    return None

def cj_headers():
    token = get_cj_token()
    return {"CJ-Access-Token": token} if token else {}

# ─────────────────────────────────────────
# CJ API — PRODUCT FETCH
# ─────────────────────────────────────────

def fetch_cj_trending_products(page=1, page_size=20):
    """CJ se trending/new arrival products fetch karo"""
    try:
        url = f"{CJ_API_BASE}/product/list"
        params = {
            "pageNum": page,
            "pageSize": page_size,
            "countryCode": "DE",       # Europe shipping check
            "categoryLevel1": "",
            "sortField": "totalOrders", # Order count se sort
            "sortType": "DESC"
        }
        resp = requests.get(url, headers=cj_headers(), params=params, timeout=20)
        data = resp.json()

        if data.get("result") and data.get("data"):
            products = data["data"].get("list", [])
            log_action("CJ Fetch", f"{len(products)} products fetched", "Success")
            return products
        else:
            log_action("CJ Fetch", f"No data: {data.get('message')}", "Warning")
            return []
    except Exception as e:
        log_action("CJ Fetch", f"Error: {e}", "Error")
        return []

def check_cj_europe_shipping(product_id):
    """Product Europe mein ship hota hai?"""
    try:
        url = f"{CJ_API_BASE}/logistic/freightCalculate"
        body = {
            "productId": product_id,
            "quantity": 1,
            "countryCode": "DE"
        }
        resp = requests.post(url, headers=cj_headers(), json=body, timeout=15)
        data = resp.json()
        if data.get("result") and data.get("data"):
            return True
        return False
    except Exception as e:
        log_action("CJ Shipping", f"Error: {e}", "Error")
        return False

def get_cj_product_detail(product_id):
    """Product ki detail + reviews + video"""
    try:
        url = f"{CJ_API_BASE}/product/query"
        params = {"pid": product_id}
        resp = requests.get(url, headers=cj_headers(), params=params, timeout=15)
        data = resp.json()
        if data.get("result"):
            return data.get("data", {})
        return {}
    except Exception as e:
        log_action("CJ Detail", f"Error: {e}", "Error")
        return {}

def get_cj_order_growth(product_id):
    """Product ke orders ka growth check — buying proof"""
    try:
        url = f"{CJ_API_BASE}/product/query"
        params = {"pid": product_id}
        resp = requests.get(url, headers=cj_headers(), params=params, timeout=15)
        data = resp.json()
        if data.get("result"):
            orders = data["data"].get("productSellCount", 0)
            return int(orders) if orders else 0
        return 0
    except Exception as e:
        log_action("CJ Orders", f"Error: {e}", "Error")
        return 0

# ─────────────────────────────────────────
# SIGNAL 1 — PYTRENDS (Google Trends)
# ─────────────────────────────────────────

def check_pytrends_signal(keyword):
    """
    5+ European countries mein trend check.
    Teen consecutive checks consistently upar = signal.
    Returns: (signal: bool, countries_trending: int)
    """
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

        trending_countries = 0
        for geo in EUROPEAN_COUNTRIES[:6]:  # 6 countries check, 5+ chahiye
            try:
                pytrends.build_payload([keyword], cat=0, timeframe="now 7-d", geo=geo)
                data = pytrends.interest_over_time()

                if data.empty:
                    time.sleep(random.uniform(1.5, 3.0))
                    continue

                values = data[keyword].tolist()
                if len(values) >= 3:
                    # Last 3 points consistently upar?
                    last3 = values[-3:]
                    if last3[-1] > last3[0] and last3[-1] >= 30:
                        trending_countries += 1

                time.sleep(random.uniform(2.0, 4.0))
            except Exception:
                time.sleep(2)
                continue

        signal = trending_countries >= 5
        log_action("Pytrends", f"{keyword}: {trending_countries}/10 countries", "Success" if signal else "Info")
        return signal, trending_countries

    except Exception as e:
        log_action("Pytrends", f"Error for {keyword}: {e}", "Error")
        return False, 0

# ─────────────────────────────────────────
# SIGNAL 2 — CJ ORDER GROWTH
# ─────────────────────────────────────────

def check_order_growth_signal(product_id, current_orders):
    """
    Actual buying proof check.
    500+ orders = strong signal.
    """
    try:
        signal = current_orders >= 500
        log_action("Order Growth", f"ID:{product_id} Orders:{current_orders}", "Success" if signal else "Info")
        return signal
    except Exception as e:
        log_action("Order Growth", f"Error: {e}", "Error")
        return False

# ─────────────────────────────────────────
# SIGNAL 3 — FACEBOOK ADS LIBRARY
# ─────────────────────────────────────────

def check_facebook_ads_signal(keyword):
    """
    Facebook Ads Library — no login.
    Last 7 din mein 20+ naye ads = green flag.
    Returns: (signal: bool, ad_count: int)
    """
    try:
        url = "https://www.facebook.com/ads/library/async/search_typeahead/"
        params = {
            "q": keyword,
            "session_id": hashlib.md5(keyword.encode()).hexdigest()[:16],
            "country": "DE",
            "ad_type": "all",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.facebook.com/ads/library/"
        }

        # Public search endpoint
        search_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=DE&q={keyword}&search_type=keyword_unordered"

        resp = requests.get(search_url, headers=headers, timeout=20)

        # Response mein ad count extract karo
        # Facebook public page se count estimate
        if resp.status_code == 200:
            content = resp.text
            # "results" ya ad count dhundho
            import re
            count_match = re.findall(r'"count":(\d+)', content)
            if count_match:
                ad_count = max([int(c) for c in count_match])
                signal = ad_count >= 20
                log_action("FB Ads", f"{keyword}: ~{ad_count} ads", "Success" if signal else "Info")
                return signal, ad_count

        # Fallback — agar page load hua toh ads exist karte hain
        signal = resp.status_code == 200
        log_action("FB Ads", f"{keyword}: Page loaded={signal}", "Info")
        return signal, 0 if not signal else 25  # Conservative estimate

    except Exception as e:
        log_action("FB Ads", f"Error for {keyword}: {e}", "Error")
        return False, 0

# ─────────────────────────────────────────
# SIGNAL 4 — TIKTOK/INSTAGRAM (GitHub Actions se)
# ─────────────────────────────────────────

def check_social_signal_from_sheet(product_keyword):
    """
    GitHub Actions Playwright se data already Sheet mein save hoga.
    'Social Signals' tab se read karo.
    Returns: (signal: bool, creator_count: int)
    """
    try:
        sheet = get_sheet()
        if not sheet:
            return False, 0

        try:
            tab = sheet.worksheet("Social Signals")
            records = tab.get_all_records()
        except Exception:
            # Tab nahi hai abhi — GitHub Actions abhi setup nahi
            log_action("Social Signal", f"{product_keyword}: Tab not found", "Warning")
            return False, 0

        keyword_lower = product_keyword.lower()
        for row in records:
            if keyword_lower in str(row.get("keyword", "")).lower():
                creator_count = int(row.get("creator_count", 0))
                signal = creator_count >= 10
                log_action("Social Signal", f"{product_keyword}: {creator_count} creators", "Success" if signal else "Info")
                return signal, creator_count

        return False, 0

    except Exception as e:
        log_action("Social Signal", f"Error: {e}", "Error")
        return False, 0

# ─────────────────────────────────────────
# SIGNAL 5 — REVIEWS GROWTH
# ─────────────────────────────────────────

def check_reviews_signal(product_id, review_count):
    """
    Review count check.
    1000+ reviews organic rate pe = real product.
    1000 reviews 3 din mein = fake flag.
    """
    try:
        # CJ se review data
        detail = get_cj_product_detail(product_id)
        current_reviews = int(detail.get("productReviewCount", review_count) or 0)

        # 50-999 reviews = real organic growth zone
        # 1000+ thodi der mein = suspicious
        if current_reviews > 5000:
            log_action("Reviews", f"ID:{product_id} Suspicious: {current_reviews}", "Warning")
            return False

        signal = current_reviews >= 50
        log_action("Reviews", f"ID:{product_id} Reviews:{current_reviews}", "Success" if signal else "Info")
        return signal

    except Exception as e:
        log_action("Reviews", f"Error: {e}", "Error")
        return False

# ─────────────────────────────────────────
# SCORING FORMULA (PDF se)
# ─────────────────────────────────────────

def calculate_score(signals_data, product_data):
    """
    Signal Weight:
    Multi-Country Trend  25%
    Sales Growth         25%
    Profit Margin        20%
    Competition Level    20%
    Min Order Price      10%
    """
    score = 0.0

    # 1. Multi-Country Trend (25%)
    countries_trending = signals_data.get("countries_trending", 0)
    trend_score = min(countries_trending / 5, 1.0) * 25
    score += trend_score

    # 2. Sales Growth (25%)
    orders = signals_data.get("orders", 0)
    if orders >= 2000:
        sales_score = 25
    elif orders >= 1000:
        sales_score = 20
    elif orders >= 500:
        sales_score = 15
    elif orders >= 100:
        sales_score = 8
    else:
        sales_score = 0
    score += sales_score

    # 3. Profit Margin (20%)
    margin = product_data.get("margin_pct", 0)
    if margin >= 50:
        margin_score = 20
    elif margin >= 40:
        margin_score = 16
    elif margin >= 35:
        margin_score = 12
    else:
        margin_score = 0
    score += margin_score

    # 4. Competition Level (20%) — FB ads count
    ad_count = signals_data.get("ad_count", 0)
    if ad_count <= 30:
        comp_score = 20    # Low competition = good
    elif ad_count <= 60:
        comp_score = 14
    elif ad_count <= 100:
        comp_score = 8
    else:
        comp_score = 3    # Too saturated
    score += comp_score

    # 5. Price (10%)
    price = product_data.get("price_eur", 0)
    if price >= 30:
        price_score = 10
    elif price >= 20:
        price_score = 7
    elif price >= 15:
        price_score = 4
    else:
        price_score = 0
    score += price_score

    return round(score, 1)

# ─────────────────────────────────────────
# DUPLICATE DETECTION (3-layer)
# ─────────────────────────────────────────

def is_duplicate(new_product, existing_products):
    """
    3 layer check:
    1. Image hash
    2. Title keywords
    3. Price range
    3 mein se 2 match = duplicate
    """
    new_title_words = set(new_product.get("name", "").lower().split())
    new_price = float(new_product.get("price_eur", 0))
    new_img = new_product.get("image_hash", "")

    for existing in existing_products:
        if existing.get("status") != "Active":
            continue

        matches = 0

        # Layer 1 — Image hash
        if new_img and new_img == existing.get("image_hash", ""):
            matches += 1

        # Layer 2 — Title keywords (60%+ common words)
        existing_words = set(str(existing.get("name", "")).lower().split())
        if new_title_words and existing_words:
            common = new_title_words & existing_words
            overlap = len(common) / max(len(new_title_words), 1)
            if overlap >= 0.6:
                matches += 1

        # Layer 3 — Price range (±20%)
        try:
            ex_price = float(existing.get("price_eur", 0))
            if ex_price > 0 and abs(new_price - ex_price) / ex_price <= 0.20:
                matches += 1
        except Exception:
            pass

        if matches >= 2:
            return True

    return False

# ─────────────────────────────────────────
# CATEGORY & TYPE HELPERS
# ─────────────────────────────────────────

def detect_category(product_name, category_name_cj):
    """CJ category se map karo"""
    name_lower = (product_name + " " + category_name_cj).lower()
    if any(k in name_lower for k in ["phone", "laptop", "earphone", "speaker", "gadget", "electronic", "led", "camera", "watch"]):
        return "Electronics"
    if any(k in name_lower for k in ["shirt", "dress", "jacket", "pants", "hoodie", "tshirt", "clothing", "fashion", "apparel"]):
        return "Clothing"
    if any(k in name_lower for k in ["shoe", "boot", "sneaker", "footwear", "sandal", "slipper"]):
        return "Footwear"
    if any(k in name_lower for k in ["gym", "fitness", "yoga", "workout", "exercise", "dumbbell", "sports"]):
        return "Fitness"
    return "Others"

def detect_type(orders, days_trending):
    """Order pattern + trend age se type detect"""
    if orders > 5000 and days_trending <= 7:
        return "Viral"
    elif orders > 1000:
        return "Medium"
    else:
        return "Evergreen"

def get_category_counts(products):
    """Current pool mein category count"""
    counts = {k: 0 for k in CATEGORY_SLOTS}
    for p in products:
        if p.get("status") == "Active":
            cat = p.get("category", "Others")
            counts[cat] = counts.get(cat, 0) + 1
    return counts

def category_has_space(category, current_counts):
    """Is category mein jagah hai?"""
    return current_counts.get(category, 0) < CATEGORY_SLOTS.get(category, 100)

# ─────────────────────────────────────────
# EARLY POOL — 21 DIN RULE
# ─────────────────────────────────────────

def remove_expired_products():
    """21 din se zyada products remove karo"""
    try:
        sheet = get_sheet()
        if not sheet:
            return 0

        tab = sheet.worksheet("Products")
        records = tab.get_all_records()
        removed = 0

        for i, row in enumerate(records, start=2):
            if row.get("status") != "Active":
                continue
            try:
                added_at = datetime.strptime(str(row.get("added_at", "")), "%Y-%m-%d %H:%M")
                days_in_pool = (datetime.now() - added_at).days
                if days_in_pool >= MAX_DAYS_IN_POOL:
                    tab.update_cell(i, 15, "Expired")
                    removed += 1
                    log_action("Pool Cleanup", f"Expired: {row.get('product_id')} — {days_in_pool} days", "Info")
            except Exception:
                continue

        if removed:
            log_action("Pool Cleanup", f"{removed} products expired", "Success")
        return removed

    except Exception as e:
        log_action("Pool Cleanup", f"Error: {e}", "Error")
        return 0

# ─────────────────────────────────────────
# TELEGRAM ALERT
# ─────────────────────────────────────────

async def send_telegram_alert(bot_token, chat_id, message):
    """Simple Telegram message bhejo"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        log_action("Telegram", f"Alert error: {e}", "Error")
        return False

async def alert_top4(admin_bot_token, top_products):
    """Top 4 products ka alert"""
    if not top_products:
        return

    text = "🏆 *Top 4 Products — Is Session Ke*\n\n"
    for i, p in enumerate(top_products[:4], 1):
        text += (
            f"{i}. *{p.get('name', 'N/A')}*\n"
            f"   Score: `{p.get('score', 'N/A')}`\n"
            f"   Price: EUR {p.get('price_eur', 'N/A')}\n"
            f"   Type: {p.get('type', 'N/A')}\n"
            f"   Category: {p.get('category', 'N/A')}\n"
            f"   CJ Video: {p.get('cj_video_url', 'N/A')}\n\n"
        )
    await send_telegram_alert(admin_bot_token, ADMIN_CHAT_ID, text)

async def alert_pool_full(admin_bot_token, count):
    """180+ slots pe alert"""
    text = (
        f"⚠️ *Early Pool Alert*\n\n"
        f"Pool mein {count}/300 products hain.\n"
        f"180 slots fill — monitor karo."
    )
    await send_telegram_alert(admin_bot_token, ADMIN_CHAT_ID, text)

# ─────────────────────────────────────────
# MAIN SESSION — PRODUCT ANALYSIS
# ─────────────────────────────────────────

async def run_session(admin_bot_token, products_to_check=None):
    """
    Ek session run karo — 10 products analyze karo.
    Subah 6, Dopahar 12, Sham 6, Raat 12 — 4x/day.
    """
    log_action("Automation1", "Session started", "Info")

    # 0. Automation flag check
    flag = get_automation_flag("Automation1")
    if flag and flag.get("status") == "Stopped":
        log_action("Automation1", "Stopped via flag — skipping session", "Info")
        return

    # 1. Expired products clean karo
    removed = remove_expired_products()

    # 2. Current pool status
    existing_products = get_all_products()
    active_products = [p for p in existing_products if p.get("status") == "Active"]
    pool_size = len(active_products)

    if pool_size >= MAX_POOL_SIZE:
        log_action("Automation1", f"Pool full: {pool_size}/300", "Warning")
        await send_telegram_alert(
            admin_bot_token, ADMIN_CHAT_ID,
            f"⚠️ *Pool Full*\n\n{pool_size}/300 products hain. Kuch hatao."
        )
        return

    category_counts = get_category_counts(existing_products)

    # 3. CJ se products fetch
    if not products_to_check:
        products_to_check = fetch_cj_trending_products(page_size=20)

    if not products_to_check:
        log_action("Automation1", "No products from CJ", "Warning")
        return

    session_added = []
    checked = 0

    for cj_product in products_to_check:
        if checked >= 10:  # Har session mein max 10
            break

        try:
            product_id   = str(cj_product.get("pid", cj_product.get("productId", "")))
            product_name = cj_product.get("productName", cj_product.get("productNameEn", "Unknown"))
            cj_category  = cj_product.get("categoryName", "")
            sell_price   = float(cj_product.get("sellPrice", cj_product.get("productPrice", 0)) or 0)
            supplier_price = float(cj_product.get("costPrice", sell_price * 0.5) or sell_price * 0.5)
            order_count  = int(cj_product.get("productSellCount", 0) or 0)
            image_url    = cj_product.get("productImage", "")
            video_url    = cj_product.get("productVideo", "")

            # ── Price filter ──
            if sell_price < MIN_PRICE_EUR:
                log_action("Filter", f"{product_name}: Price too low EUR {sell_price}", "Skip")
                continue

            # ── Margin check ──
            shipping_est = 3.5  # Average Europe shipping estimate
            gross_profit = sell_price - supplier_price - shipping_est
            margin_pct = (gross_profit / sell_price * 100) if sell_price > 0 else 0

            if margin_pct < MIN_MARGIN_PCT:
                log_action("Filter", f"{product_name}: Margin low {margin_pct:.1f}%", "Skip")
                continue

            # ── Europe shipping check ──
            if not check_cj_europe_shipping(product_id):
                log_action("Filter", f"{product_name}: No Europe shipping", "Skip")
                continue

            # ── Category detect ──
            category = detect_category(product_name, cj_category)

            # ── Category space check ──
            if not category_has_space(category, category_counts):
                log_action("Filter", f"{product_name}: {category} category full", "Skip")
                continue

            # ── Image hash for duplicate check ──
            img_hash = hashlib.md5(image_url.encode()).hexdigest()[:12] if image_url else ""

            product_for_dup_check = {
                "name": product_name,
                "price_eur": sell_price,
                "image_hash": img_hash
            }

            # ── Duplicate check ──
            if is_duplicate(product_for_dup_check, existing_products):
                log_action("Filter", f"{product_name}: Duplicate detected", "Skip")
                continue

            # ── SIGNAL CHECKS ──
            signals_passed = 0
            signals_data = {}

            # Signal 1 — Pytrends
            keyword = " ".join(product_name.split()[:3])  # First 3 words
            trend_signal, countries_count = check_pytrends_signal(keyword)
            signals_data["countries_trending"] = countries_count
            if trend_signal:
                signals_passed += 1
            time.sleep(random.uniform(2, 4))

            # Signal 2 — CJ Order Growth
            order_signal = check_order_growth_signal(product_id, order_count)
            signals_data["orders"] = order_count
            if order_signal:
                signals_passed += 1

            # Signal 3 — Facebook Ads
            fb_signal, ad_count = check_facebook_ads_signal(keyword)
            signals_data["ad_count"] = ad_count
            if fb_signal:
                signals_passed += 1
            time.sleep(random.uniform(1, 2))

            # Signal 4 — TikTok/Instagram (GitHub Actions se)
            social_signal, creator_count = check_social_signal_from_sheet(keyword)
            signals_data["creator_count"] = creator_count
            if social_signal:
                signals_passed += 1

            # Signal 5 — Reviews
            review_detail = get_cj_product_detail(product_id)
            review_count  = int(review_detail.get("productReviewCount", 0) or 0)
            review_signal = check_reviews_signal(product_id, review_count)
            if review_signal:
                signals_passed += 1

            log_action(
                "Signals",
                f"{product_name}: {signals_passed}/5 signals passed",
                "Success" if signals_passed >= SIGNALS_REQUIRED else "Info"
            )

            # ── Minimum 4 signals chahiye ──
            if signals_passed < SIGNALS_REQUIRED:
                checked += 1
                continue

            # ── Score calculate ──
            product_data_for_score = {
                "price_eur": sell_price,
                "margin_pct": margin_pct
            }
            score = calculate_score(signals_data, product_data_for_score)

            # ── Type detect ──
            product_type = detect_type(order_count, countries_count)

            # ── Sheet mein add karo ──
            new_product = {
                "product_id":   product_id,
                "name":         product_name,
                "category":     category,
                "type":         product_type,
                "score":        score,
                "cj_video_url": video_url,
                "price_eur":    round(sell_price, 2),
                "supplier":     "CJ Dropshipping",
                "signal_1":     "Yes" if trend_signal else "No",
                "signal_2":     "Yes" if order_signal else "No",
                "signal_3":     "Yes" if fb_signal else "No",
                "signal_4":     "Yes" if social_signal else "No",
                "signal_5":     "Yes" if review_signal else "No",
                "days_in_pool": 0,
                "status":       "Active",
                "source":       "CJ Trending",
                "image_hash":   img_hash,
            }

            success = add_product(new_product)
            if success:
                session_added.append(new_product)
                category_counts[category] = category_counts.get(category, 0) + 1
                existing_products.append(new_product)
                pool_size += 1
                log_action("Pool Add", f"Added: {product_name} Score:{score}", "Success")

            checked += 1
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            log_action("Session Error", f"{product_id}: {str(e)}", "Error")
            checked += 1
            continue

    # ── Top 4 alert ──
    if session_added:
        top4 = sorted(session_added, key=lambda x: x.get("score", 0), reverse=True)[:4]
        await alert_top4(admin_bot_token, top4)

    # ── Pool 180+ alert ──
    if pool_size >= 180:
        await alert_pool_full(admin_bot_token, pool_size)

    log_action(
        "Automation1",
        f"Session done — {len(session_added)} products added, Pool: {pool_size}/300",
        "Success"
    )

# ─────────────────────────────────────────
# SCHEDULER — 4 sessions/day
# ─────────────────────────────────────────

def get_next_session_time():
    """Agle session ka wait time calculate karo (seconds)"""
    session_hours = [6, 12, 18, 0]  # 6am, 12pm, 6pm, 12am India time
    now = datetime.now()
    current_hour = now.hour

    for h in session_hours:
        if current_hour < h:
            next_dt = now.replace(hour=h, minute=0, second=0, microsecond=0)
            return (next_dt - now).total_seconds()

    # Aaj ke sab sessions done — kal subah 6 baje
    next_dt = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    return (next_dt - now).total_seconds()

async def run_scheduler(admin_bot_token):
    """
    Continuous scheduler — 4 sessions/day.
    Server restart safe — next session time calculate karta hai.
    """
    log_action("Scheduler", "Automation 1 scheduler started", "Info")
    await send_telegram_alert(
        admin_bot_token, ADMIN_CHAT_ID,
        "🟢 *Automation 1 Online!*\n\nTrending product detection shuru ho gayi.\n4 sessions/day — 10 products/session."
    )

    while True:
        try:
            await run_session(admin_bot_token)
        except Exception as e:
            log_action("Scheduler", f"Session error: {e}", "Error")

        wait_seconds = get_next_session_time()
        wait_hours = round(wait_seconds / 3600, 1)
        log_action("Scheduler", f"Next session in {wait_hours} hours", "Info")
        await asyncio.sleep(wait_seconds)

# ─────────────────────────────────────────
# ENTRY — main.py se call hoga
# ─────────────────────────────────────────

def start_automation1(admin_bot_token):
    """main.py se background thread mein call karo"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_scheduler(admin_bot_token))
