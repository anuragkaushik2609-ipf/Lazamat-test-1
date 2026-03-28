"""
eprolo_scraper.py — LAMAZAT CANVAS
────────────────────────────────────────────────
Eprolo se Playwright ke zariye trending products fetch:
  1. Login karo (email + password)
  2. Catalog/trending products scrape karo
  3. Price, image, video, orders, reviews lo
  4. Google Sheet "Eprolo Products" tab mein save karo
  5. automation1.py wahan se read karega (CJ ke bajaye ya saath mein)

GitHub Actions pe chalega — har 6 ghante.
"""

import os
import re
import json
import time
import random
import asyncio
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

EPROLO_EMAIL    = os.getenv("EPROLO_EMAIL")
EPROLO_PASSWORD = os.getenv("EPROLO_PASSWORD")
GOOGLE_SHEET_ID    = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Eprolo URLs
LOGIN_URL   = "https://eprolo.com/app/#/login"
CATALOG_URL = "https://eprolo.com/app/newProductsCatalog.html"
HOT_SELLING = "https://eprolo.com/app/newProductsCatalog.html?categoryId=&sortType=hot"

MIN_PRICE = 8.0   # USD
MAX_PRICE = 80.0  # USD

# ─────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────

def get_sheet():
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        return client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        print(f"[Sheet Error] {e}")
        return None

def ensure_tab(sheet):
    """Eprolo Products tab banao agar nahi hai"""
    try:
        return sheet.worksheet("Eprolo Products")
    except Exception:
        ws = sheet.add_worksheet(title="Eprolo Products", rows=1000, cols=15)
        ws.append_row([
            "product_id", "name", "category", "price_usd", "price_eur",
            "image_url", "video_url", "orders", "reviews", "rating",
            "shipping_days", "signal_strength", "product_url",
            "scraped_at", "status"
        ])
        return ws

def save_product(product):
    """Sheet mein save karo"""
    try:
        sheet = get_sheet()
        if not sheet:
            return False
        tab = ensure_tab(sheet)
        records = tab.get_all_records()

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Already exists? Update karo
        for i, row in enumerate(records, start=2):
            if str(row.get("product_id", "")) == str(product.get("product_id", "")):
                tab.update_cell(i, 8,  product.get("orders", 0))
                tab.update_cell(i, 14, now)
                print(f"[Sheet] Updated: {product['name'][:40]}")
                return True

        # Naya row
        tab.append_row([
            product.get("product_id", ""),
            product.get("name", "")[:100],
            product.get("category", ""),
            product.get("price_usd", 0),
            product.get("price_eur", 0),
            product.get("image_url", ""),
            product.get("video_url", ""),
            product.get("orders", 0),
            product.get("reviews", 0),
            product.get("rating", 0),
            product.get("shipping_days", ""),
            product.get("signal_strength", "Weak"),
            product.get("product_url", ""),
            now,
            "Active"
        ])
        print(f"[Sheet] Saved: {product['name'][:40]}")
        return True
    except Exception as e:
        print(f"[Sheet Save Error] {e}")
        return False

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def parse_number(text):
    if not text:
        return 0
    try:
        text = str(text).strip().upper().replace(",", "")
        multiplier = 1
        if "M" in text:
            multiplier = 1_000_000
            text = text.replace("M+", "").replace("M", "")
        elif "K" in text:
            multiplier = 1_000
            text = text.replace("K+", "").replace("K", "")
        num = re.sub(r"[^\d.]", "", text)
        return int(float(num) * multiplier) if num else 0
    except Exception:
        return 0

def usd_to_eur(usd):
    return round(float(usd) * 0.92, 2)

def signal_strength(orders, reviews, rating):
    score = 0
    if orders >= 1000: score += 3
    elif orders >= 500: score += 2
    elif orders >= 100: score += 1
    if reviews >= 200: score += 2
    elif reviews >= 50: score += 1
    if rating >= 4.5: score += 2
    elif rating >= 4.0: score += 1
    if score >= 6: return "Strong"
    elif score >= 4: return "Medium"
    elif score >= 2: return "Weak"
    return "Very Weak"

# ─────────────────────────────────────────
# STEP 1 — LOGIN
# ─────────────────────────────────────────

async def login_eprolo(page):
    """Eprolo mein login karo"""
    print("[Login] Opening Eprolo login page...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(random.uniform(2, 3))

    try:
        # Email field
        email_selectors = [
            "input[type='email']",
            "input[placeholder*='email' i]",
            "input[name='email']",
            "#email"
        ]
        for sel in email_selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el:
                    await el.fill(EPROLO_EMAIL)
                    break
            except PlaywrightTimeout:
                continue

        await asyncio.sleep(0.5)

        # Password field
        pwd_selectors = [
            "input[type='password']",
            "input[placeholder*='password' i]",
            "input[name='password']",
            "#password"
        ]
        for sel in pwd_selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el:
                    await el.fill(EPROLO_PASSWORD)
                    break
            except PlaywrightTimeout:
                continue

        await asyncio.sleep(0.5)

        # Login button
        btn_selectors = [
            "button[type='submit']",
            "button:has-text('Login')",
            "button:has-text('Sign In')",
            "button:has-text('Log in')",
            ".login-btn",
            "#login-btn"
        ]
        for sel in btn_selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=3000)
                if el:
                    await el.click()
                    break
            except PlaywrightTimeout:
                continue

        await asyncio.sleep(random.uniform(3, 5))

        # Login success check
        current_url = page.url
        if "login" not in current_url.lower() or "dashboard" in current_url.lower() or "app" in current_url.lower():
            print(f"[Login] Success! URL: {current_url[:60]}")
            return True
        else:
            print(f"[Login] May have failed. URL: {current_url[:60]}")
            # Page content check
            content = await page.content()
            if "logout" in content.lower() or "dashboard" in content.lower():
                print("[Login] Actually logged in (found logout/dashboard in content)")
                return True
            return False

    except Exception as e:
        print(f"[Login Error] {e}")
        return False

# ─────────────────────────────────────────
# STEP 2 — PRODUCT CARDS EXTRACT
# ─────────────────────────────────────────

async def extract_products_from_page(page):
    """Current page se product cards extract karo"""
    products = []

    await asyncio.sleep(random.uniform(2, 4))

    # Scroll karke products load karo
    for _ in range(4):
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        await asyncio.sleep(random.uniform(1, 2))

    # Product card selectors — Eprolo ke liye
    card_selectors = [
        ".product-item",
        ".goods-item",
        "[class*='product-card']",
        "[class*='goods-card']",
        "[class*='item-card']",
        ".catalog-item",
        "[class*='catalog']  .item",
        "li[class*='product']",
        "div[class*='product'][class*='list'] > div",
    ]

    cards = []
    for sel in card_selectors:
        cards = await page.query_selector_all(sel)
        if len(cards) >= 3:
            print(f"[Scraper] Found {len(cards)} cards — selector: {sel}")
            break

    if not cards:
        print("[Scraper] No product cards found — trying JSON from page source")
        # Page source se JSON data try karo
        content = await page.content()
        json_products = extract_from_json(content)
        return json_products

    for card in cards[:20]:
        try:
            product = {}

            # Name
            name_sels = ["h3", "h4", ".title", ".name", "[class*='title']", "[class*='name']", "a"]
            for s in name_sels:
                el = await card.query_selector(s)
                if el:
                    text = await el.inner_text()
                    if text and len(text) > 5:
                        product["name"] = text.strip()[:150]
                        break

            if not product.get("name"):
                continue

            # Product URL + ID
            link = await card.query_selector("a[href]")
            if link:
                href = await link.get_attribute("href")
                if href:
                    product["product_url"] = href if href.startswith("http") else f"https://eprolo.com{href}"
                    id_match = re.search(r'[?&]id=(\d+)|/(\d{6,})', href)
                    if id_match:
                        product["product_id"] = id_match.group(1) or id_match.group(2)

            if not product.get("product_id"):
                product["product_id"] = f"EP{hash(product.get('name',''))%100000:05d}"

            # Price
            price_sels = [".price", "[class*='price']", "span[class*='cost']", ".amount"]
            for s in price_sels:
                el = await card.query_selector(s)
                if el:
                    text = await el.inner_text()
                    num = re.sub(r"[^\d.]", "", text.replace(",", "."))
                    if num:
                        product["price_usd"] = float(num)
                        product["price_eur"] = usd_to_eur(float(num))
                        break

            if not product.get("price_usd"):
                continue

            price = product["price_usd"]
            if price < MIN_PRICE or price > MAX_PRICE:
                continue

            # Image
            img = await card.query_selector("img")
            if img:
                src = await img.get_attribute("src") or await img.get_attribute("data-src") or ""
                if src:
                    product["image_url"] = src if src.startswith("http") else f"https:{src}"

            # Orders / Sold count
            sold_sels = ["[class*='sold']", "[class*='order']", "[class*='sale']"]
            for s in sold_sels:
                el = await card.query_selector(s)
                if el:
                    text = await el.inner_text()
                    count = parse_number(text)
                    if count > 0:
                        product["orders"] = count
                        break
            if "orders" not in product:
                product["orders"] = 0

            # Rating
            rating_sels = ["[class*='rating']", "[class*='star']", ".score"]
            for s in rating_sels:
                el = await card.query_selector(s)
                if el:
                    text = await el.inner_text()
                    num = re.sub(r"[^\d.]", "", text)
                    if num:
                        val = float(num)
                        if 1 <= val <= 5:
                            product["rating"] = val
                            break
            if "rating" not in product:
                product["rating"] = 0

            product["reviews"]  = 0
            product["category"] = ""
            product["video_url"] = ""
            product["signal_strength"] = signal_strength(
                product.get("orders", 0), product.get("reviews", 0), product.get("rating", 0)
            )

            products.append(product)

        except Exception:
            continue

    print(f"[Scraper] Extracted {len(products)} products from page")
    return products


def extract_from_json(content):
    """Page source se embedded JSON data extract karo"""
    products = []
    try:
        # Common JSON patterns
        patterns = [
            r'"productName"\s*:\s*"([^"]+)"[^}]*"salePrice"\s*:\s*"?([\d.]+)',
            r'"name"\s*:\s*"([^"]+)"[^}]*"price"\s*:\s*"?([\d.]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for i, (name, price) in enumerate(matches[:20]):
                if float(price) >= MIN_PRICE:
                    products.append({
                        "product_id": f"EPJ{i:04d}",
                        "name": name[:100],
                        "price_usd": float(price),
                        "price_eur": usd_to_eur(float(price)),
                        "orders": 0, "reviews": 0, "rating": 0,
                        "image_url": "", "video_url": "", "category": "",
                        "signal_strength": "Weak"
                    })
            if products:
                break
    except Exception as e:
        print(f"[JSON Extract] {e}")
    return products

# ─────────────────────────────────────────
# STEP 3 — DETAIL PAGE (top products)
# ─────────────────────────────────────────

async def get_product_detail(page, product):
    """Product detail page se video URL + better data"""
    url = product.get("product_url", "")
    if not url:
        return product

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(random.uniform(2, 3))

        # Video URL
        video_sels = ["video source", "video[src]", "[class*='video'] source", "source[type='video/mp4']"]
        for s in video_sels:
            el = await page.query_selector(s)
            if el:
                src = await el.get_attribute("src") or ""
                if src:
                    product["video_url"] = src if src.startswith("http") else f"https:{src}"
                    break

        # Better orders count
        sold_sels = ["[class*='sold']", "[class*='order-count']", "[class*='sales']"]
        for s in sold_sels:
            el = await page.query_selector(s)
            if el:
                text = await el.inner_text()
                count = parse_number(text)
                if count > product.get("orders", 0):
                    product["orders"] = count
                    break

        # Reviews
        review_sels = ["[class*='review-count']", "[class*='reviews']", "span[class*='eval']"]
        for s in review_sels:
            el = await page.query_selector(s)
            if el:
                text = await el.inner_text()
                count = parse_number(text)
                if count > 0:
                    product["reviews"] = count
                    break

        # Shipping info
        ship_sels = ["[class*='shipping']", "[class*='delivery']", "[class*='ship-day']"]
        for s in ship_sels:
            el = await page.query_selector(s)
            if el:
                text = (await el.inner_text())[:60]
                if text:
                    product["shipping_days"] = text
                    break

        # Recalculate signal
        product["signal_strength"] = signal_strength(
            product.get("orders", 0), product.get("reviews", 0), product.get("rating", 0)
        )

    except Exception as e:
        print(f"[Detail Error] {product.get('name','')[:30]}: {e}")

    return product

# ─────────────────────────────────────────
# MAIN SCRAPER
# ─────────────────────────────────────────

async def run_eprolo_scraper():
    print(f"\n🛍️ Eprolo Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("─" * 50)

    if not EPROLO_EMAIL or not EPROLO_PASSWORD:
        print("❌ EPROLO_EMAIL ya EPROLO_PASSWORD missing!")
        return

    all_products = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-dev-shm-usage", "--disable-gpu",
                "--no-first-run", "--single-process",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Europe/Berlin",
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        # Login
        logged_in = await login_eprolo(page)
        if not logged_in:
            print("❌ Login failed! Email/password check karo.")
            await browser.close()
            return

        await asyncio.sleep(2)

        # Catalog pages scrape karo
        pages_to_scrape = [
            HOT_SELLING,
            f"{CATALOG_URL}?sortType=hot",
            f"{CATALOG_URL}?sortType=new",
        ]

        for url in pages_to_scrape:
            print(f"\n[Scrape] Loading: {url[:70]}...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                products = await extract_products_from_page(page)
                all_products.extend(products)
                print(f"[Scrape] Got {len(products)} products")
                await asyncio.sleep(random.uniform(3, 6))
            except Exception as e:
                print(f"[Scrape Error] {e}")

            if len(all_products) >= 40:
                break

        # Duplicate remove
        seen = set()
        unique = []
        for p in all_products:
            pid = p.get("product_id", "")
            if pid and pid not in seen:
                seen.add(pid)
                unique.append(p)

        print(f"\n[Total] {len(unique)} unique products")

        # Top products ka detail page visit karo
        strong = [p for p in unique if p.get("orders", 0) >= 100 or p.get("price_usd", 0) >= 15][:10]
        print(f"[Detail] Visiting {len(strong)} product detail pages...")

        for i, product in enumerate(strong):
            if product.get("product_url"):
                print(f"[Detail {i+1}/{len(strong)}] {product['name'][:40]}")
                product = await get_product_detail(page, product)
                strong[i] = product
                await asyncio.sleep(random.uniform(2, 4))

        await browser.close()

    # Sheet mein save
    print(f"\n[Save] Saving {len(unique)} products to Sheet...")
    saved = 0
    for p in unique:
        if save_product(p):
            saved += 1

    # Summary
    strong_count = len([p for p in unique if p.get("signal_strength") == "Strong"])
    medium_count = len([p for p in unique if p.get("signal_strength") == "Medium"])

    print(f"\n{'─'*50}")
    print(f"✅ Eprolo Scraper Done!")
    print(f"   Total: {len(unique)} products")
    print(f"   Strong: {strong_count}")
    print(f"   Medium: {medium_count}")
    print(f"   Saved:  {saved}")

if __name__ == "__main__":
    asyncio.run(run_eprolo_scraper())
