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

        # Login ke baad URL change hone ka wait karo (max 15 sec)
        try:
            await page.wait_for_function(
                "() => !window.location.hash.includes('/login')",
                timeout=15000
            )
            print("[Login] URL changed away from login page ✅")
        except Exception:
            pass

        await asyncio.sleep(random.uniform(2, 3))

        # Login success check — hash mein #/login nahi hona chahiye
        current_url = page.url
        print(f"[Login] Current URL: {current_url[:80]}")

        if "#/login" not in current_url.lower():
            print(f"[Login] Success! Logged in ✅")
            return True
        else:
            # Page content check as fallback
            content = await page.content()
            if "logout" in content.lower() or "my account" in content.lower():
                print("[Login] Actually logged in (found logout in content)")
                return True
            print(f"[Login] Failed — still on login page ❌")
            # Screenshot debug info
            title = await page.title()
            print(f"[Login] Page title: {title}")
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

    await asyncio.sleep(random.uniform(3, 5))

    # Scroll karke lazy-load products trigger karo
    for _ in range(5):
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        await asyncio.sleep(random.uniform(1.5, 2.5))

    # Pehle debug — kya kya classes hain page par
    all_classes = await page.evaluate("""
        () => {
            const els = document.querySelectorAll('[class]');
            const classes = new Set();
            els.forEach(el => el.className.toString().split(' ').forEach(c => { if(c) classes.add(c); }));
            return [...classes].slice(0, 80).join(', ');
        }
    """)
    print(f"[Debug] Page classes: {all_classes[:300]}")

    # Product card selectors — broad se narrow
    card_selectors = [
        ".product-item",
        ".goods-item",
        "[class*='product-card']",
        "[class*='goods-card']",
        "[class*='item-card']",
        ".catalog-item",
        "[class*='catalog'] .item",
        "li[class*='product']",
        "div[class*='product'][class*='list'] > div",
        "[class*='product-list'] > div",
        "[class*='goodsItem']",
        "[class*='productItem']",
        ".el-col",  # Element UI grid
        "[class*='goods-list'] > div",
    ]

    cards = []
    used_sel = ""
    for sel in card_selectors:
        cards = await page.query_selector_all(sel)
        if len(cards) >= 3:
            print(f"[Scraper] Found {len(cards)} cards — selector: {sel}")
            used_sel = sel
            break

    if not cards:
        print("[Scraper] No product cards found — trying JS extraction")
        # JavaScript se directly data nikaalo
        js_products = await page.evaluate("""
            () => {
                const results = [];
                // Sab links dhundo jo product URL jaisi lagein
                const links = document.querySelectorAll('a[href*="product"], a[href*="goods"], a[href*="item"]');
                links.forEach((link, i) => {
                    if (i >= 20) return;
                    const card = link.closest('li, div.item, div[class*="card"], div[class*="product"]') || link.parentElement;
                    if (!card) return;
                    const text = card.innerText || '';
                    const img = card.querySelector('img');
                    const priceMatch = text.match(/\\$?([\\d.]+)/);
                    const nameEl = card.querySelector('h1,h2,h3,h4,p,span[class*="name"],span[class*="title"],.name,.title');
                    results.push({
                        name: nameEl ? nameEl.innerText.trim() : text.split('\\n')[0].trim(),
                        href: link.href,
                        price_text: priceMatch ? priceMatch[1] : '',
                        img_src: img ? (img.src || img.dataset.src || '') : '',
                        card_text: text.slice(0, 200)
                    });
                });
                return results;
            }
        """)
        print(f"[Scraper] JS found {len(js_products)} potential products")
        for i, item in enumerate(js_products[:5]):
            print(f"  [{i+1}] name={item.get('name','')[:50]} | price={item.get('price_text')} | href={item.get('href','')[:60]}")

        # JS results se product banao
        for item in js_products[:20]:
            try:
                name = item.get("name", "").strip()
                if not name or len(name) < 4:
                    name = item.get("card_text", "").split("\n")[0].strip()
                if not name or len(name) < 4:
                    continue
                price_str = item.get("price_text", "")
                price = float(price_str) if price_str else 0.0
                if price < MIN_PRICE or price > MAX_PRICE:
                    continue
                href = item.get("href", "")
                id_match = re.search(r'[?&]id=(\d+)|/(\d{6,})', href)
                pid = (id_match.group(1) or id_match.group(2)) if id_match else f"EP{abs(hash(name))%100000:05d}"
                products.append({
                    "name": name[:150],
                    "product_id": pid,
                    "product_url": href,
                    "price_usd": price,
                    "price_eur": usd_to_eur(price),
                    "image_url": item.get("img_src", ""),
                    "orders": 0, "reviews": 0, "rating": 0,
                    "category": "", "video_url": "",
                    "signal_strength": signal_strength(0, 0, 0)
                })
            except Exception:
                continue

        # Agar JS bhi fail toh page source se JSON try karo
        if not products:
            print("[Scraper] Trying JSON from page source...")
            content = await page.content()
            print(f"[Debug] Page content length: {len(content)} chars")
            # First 500 chars of body text
            body_text = await page.evaluate("() => document.body ? document.body.innerText.slice(0, 500) : 'NO BODY'")
            print(f"[Debug] Body text preview: {body_text[:300]}")
            json_products = extract_from_json(content)
            products.extend(json_products)

        print(f"[Scraper] Extracted {len(products)} products (JS mode)")
        return products

    # Card-based extraction — JS evaluate for speed + accuracy
    js_data = await page.evaluate(f"""
        () => {{
            const results = [];
            const cards = document.querySelectorAll('{used_sel}');
            cards.forEach((card, i) => {{
                if (i >= 20) return;
                const data = {{}};

                // Name — sab text elements try karo
                const nameEl = card.querySelector('h1,h2,h3,h4,[class*="title"],[class*="name"],[class*="Title"],[class*="Name"],p.name,span.name');
                data.name = nameEl ? nameEl.innerText.trim() : '';
                if (!data.name) {{
                    // First meaningful text node
                    const allText = card.querySelectorAll('p,span,div');
                    for (let el of allText) {{
                        const t = el.innerText.trim();
                        if (t.length > 8 && t.length < 200 && !t.match(/^\\$|^\\d/)) {{
                            data.name = t;
                            break;
                        }}
                    }}
                }}

                // Price
                const priceEl = card.querySelector('[class*="price"],[class*="Price"],[class*="cost"],span.amount,.amount');
                const priceText = priceEl ? priceEl.innerText : card.innerText;
                const priceMatch = priceText.match(/\\$?([\\d]+\\.?[\\d]{{0,2}})/);
                data.price_text = priceMatch ? priceMatch[1] : '';

                // Link
                const link = card.querySelector('a[href]');
                data.href = link ? link.href : '';

                // Image
                const img = card.querySelector('img');
                data.img = img ? (img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy') || '') : '';

                // Sold/Orders
                const soldEl = card.querySelector('[class*="sold"],[class*="order"],[class*="sale"],[class*="Sold"]');
                data.sold_text = soldEl ? soldEl.innerText : '';

                // Full card text for debug
                data.card_text = card.innerText.slice(0, 150);

                results.push(data);
            }});
            return results;
        }}
    """)

    print(f"[Scraper] JS extracted raw data for {len(js_data)} cards")
    # Debug first 3 cards
    for i, item in enumerate(js_data[:3]):
        print(f"  Card[{i+1}]: name='{item.get('name','')[:40]}' price='{item.get('price_text')}' text='{item.get('card_text','')[:80]}'")

    for item in js_data:
        try:
            name = item.get("name", "").strip()
            if not name or len(name) < 4:
                continue

            price_str = item.get("price_text", "")
            price = float(price_str) if price_str else 0.0
            if price == 0:
                # card_text se price try karo
                m = re.search(r'\$?([\d]+\.?[\d]{0,2})', item.get("card_text", ""))
                if m:
                    price = float(m.group(1))

            if price < MIN_PRICE or price > MAX_PRICE:
                continue

            href = item.get("href", "")
            id_match = re.search(r'[?&]id=(\d+)|/(\d{6,})', href)
            pid = (id_match.group(1) or id_match.group(2)) if id_match else f"EP{abs(hash(name))%100000:05d}"

            sold_text = item.get("sold_text", "")
            orders = parse_number(sold_text) if sold_text else 0

            products.append({
                "name": name[:150],
                "product_id": pid,
                "product_url": href if href.startswith("http") else f"https://eprolo.com{href}",
                "price_usd": price,
                "price_eur": usd_to_eur(price),
                "image_url": item.get("img", ""),
                "orders": orders,
                "reviews": 0,
                "rating": 0,
                "category": "",
                "video_url": "",
                "signal_strength": signal_strength(orders, 0, 0)
            })
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
