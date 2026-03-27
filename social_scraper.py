"""
social_scraper.py — LAMAZAT CANVAS
────────────────────────────────────────────────
GitHub Actions pe chalega — Playwright se:
  1. TikTok   — hashtag creator/video count
  2. Instagram — hashtag posts count
  3. Google    — search result count (trends proxy)

Data → Google Sheet "Social Signals" tab mein save hoga
Automation 1 wahan se read karega (Signal 4)

Run: python social_scraper.py
"""

import os
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

GOOGLE_SHEET_ID   = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Min thresholds for signal = True
TIKTOK_MIN_VIDEOS    = 100_000   # 100K+ videos on hashtag
INSTAGRAM_MIN_POSTS  = 50_000    # 50K+ posts on hashtag
GOOGLE_MIN_RESULTS   = 1_000_000 # 1M+ search results

# ─────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
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

def save_signal(keyword, platform, creator_count, raw_text=""):
    """Social Signals tab mein save/update karo"""
    try:
        sheet = get_sheet()
        if not sheet:
            return False

        tab = sheet.worksheet("Social Signals")
        records = tab.get_all_records()

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        keyword_lower = keyword.lower()

        # Existing row update karo
        for i, row in enumerate(records, start=2):
            if (str(row.get("keyword", "")).lower() == keyword_lower and
                    str(row.get("platform", "")) == platform):
                tab.update_cell(i, 3, creator_count)
                tab.update_cell(i, 4, now)
                tab.update_cell(i, 5, raw_text[:100])
                print(f"[Sheet] Updated: {keyword} | {platform} | {creator_count}")
                return True

        # Naya row add karo
        tab.append_row([keyword, platform, creator_count, now, raw_text[:100]])
        print(f"[Sheet] Added: {keyword} | {platform} | {creator_count}")
        return True

    except Exception as e:
        print(f"[Sheet Save Error] {e}")
        return False

# ─────────────────────────────────────────
# KEYWORDS — Sheet ke Products se lo
# ─────────────────────────────────────────

def get_keywords_from_sheet():
    """
    Products tab se active products ke keywords lo.
    Agar products empty hain toh fallback list use karo.
    """
    try:
        sheet = get_sheet()
        if not sheet:
            return get_fallback_keywords()

        tab = sheet.worksheet("Products")
        records = tab.get_all_records()
        active = [r for r in records if r.get("status") == "Active"]

        keywords = []
        for p in active:
            name = str(p.get("name", ""))
            if name:
                # First 2-3 words as keyword
                words = name.split()[:3]
                kw = " ".join(words)
                if kw not in keywords:
                    keywords.append(kw)

        if keywords:
            print(f"[Keywords] {len(keywords)} from Products sheet")
            return keywords[:30]  # Max 30 per run (API limits)

    except Exception as e:
        print(f"[Keywords Error] {e}")

    return get_fallback_keywords()

def get_fallback_keywords():
    """Agar Sheet empty hai toh ye keywords test ke liye"""
    return [
        "led strip lights",
        "posture corrector",
        "car phone holder",
        "electric massage gun",
        "portable blender",
        "yoga mat",
        "resistance bands",
        "neck massager",
        "ring light",
        "smartwatch"
    ]

# ─────────────────────────────────────────
# HELPER — Number parse karo (1.2M, 500K, etc.)
# ─────────────────────────────────────────

def parse_count(text):
    """
    '1.2M videos' → 1200000
    '500K posts'  → 500000
    '12,345'      → 12345
    """
    try:
        text = str(text).strip().upper()
        text = text.replace(",", "").replace(" ", "")

        multiplier = 1
        if "B" in text:
            multiplier = 1_000_000_000
            text = text.replace("B", "")
        elif "M" in text:
            multiplier = 1_000_000
            text = text.replace("M", "")
        elif "K" in text:
            multiplier = 1_000
            text = text.replace("K", "")

        # Only digits + dot
        import re
        num_str = re.sub(r"[^\d.]", "", text)
        if num_str:
            return int(float(num_str) * multiplier)
    except Exception:
        pass
    return 0

# ─────────────────────────────────────────
# SCRAPER 1 — TIKTOK HASHTAG
# ─────────────────────────────────────────

async def scrape_tiktok(page, keyword):
    """
    TikTok hashtag page se video count lo.
    URL: tiktok.com/tag/{keyword}
    """
    hashtag = keyword.replace(" ", "")
    url = f"https://www.tiktok.com/tag/{hashtag}"

    try:
        print(f"[TikTok] Checking: #{hashtag}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(3, 5))

        # Multiple selectors try karo — TikTok UI change hoti hai
        count_text = ""
        selectors = [
            "[data-e2e='challenge-vvcount']",
            "strong[data-e2e='challenge-vvcount']",
            "h2[data-e2e='challenge-vvcount']",
            ".tiktok-1n2ykfh",
            "[class*='VideoCount']",
            "[class*='videoCount']",
        ]

        for selector in selectors:
            try:
                el = await page.wait_for_selector(selector, timeout=5000)
                if el:
                    count_text = await el.inner_text()
                    if count_text:
                        break
            except PlaywrightTimeout:
                continue

        # Fallback — page content mein dhundo
        if not count_text:
            content = await page.content()
            import re
            # "videos" ke paas number dhundo
            matches = re.findall(r'([\d.]+[KMB]?)\s*(?:videos|Views|views)', content)
            if matches:
                count_text = matches[0]

        count = parse_count(count_text)
        signal = count >= TIKTOK_MIN_VIDEOS

        print(f"[TikTok] #{hashtag}: {count_text} ({count}) — Signal: {signal}")
        save_signal(keyword, "TikTok", count, count_text)
        return count, signal

    except Exception as e:
        print(f"[TikTok Error] {keyword}: {e}")
        save_signal(keyword, "TikTok", 0, "Error")
        return 0, False

# ─────────────────────────────────────────
# SCRAPER 2 — INSTAGRAM HASHTAG
# ─────────────────────────────────────────

async def scrape_instagram(page, keyword):
    """
    Instagram hashtag explore page se post count lo.
    Login nahi chahiye — public hashtag pages accessible hain.
    URL: instagram.com/explore/tags/{hashtag}/
    """
    hashtag = keyword.replace(" ", "")
    url = f"https://www.instagram.com/explore/tags/{hashtag}/"

    try:
        print(f"[Instagram] Checking: #{hashtag}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(4, 7))

        count_text = ""

        # Instagram ke selectors
        selectors = [
            "span.g47SY",
            "span[class*='count']",
            "header span span",
            "span[title]",
        ]

        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    if any(c in text.upper() for c in ["K", "M", "B"]) or text.replace(",", "").isdigit():
                        count_text = text
                        break
                if count_text:
                    break
            except Exception:
                continue

        # Fallback — meta tag se
        if not count_text:
            try:
                meta = await page.query_selector("meta[name='description']")
                if meta:
                    desc = await meta.get_attribute("content")
                    import re
                    matches = re.findall(r'([\d,]+(?:\.\d+)?[KMB]?)\s*(?:posts|Posts)', str(desc))
                    if matches:
                        count_text = matches[0]
            except Exception:
                pass

        # Page content fallback
        if not count_text:
            content = await page.content()
            import re
            matches = re.findall(r'"edge_hashtag_to_media":\{"count":(\d+)', content)
            if matches:
                count_text = matches[0]

        count = parse_count(count_text)
        signal = count >= INSTAGRAM_MIN_POSTS

        print(f"[Instagram] #{hashtag}: {count_text} ({count}) — Signal: {signal}")
        save_signal(keyword, "Instagram", count, count_text)
        return count, signal

    except Exception as e:
        print(f"[Instagram Error] {keyword}: {e}")
        save_signal(keyword, "Instagram", 0, "Error")
        return 0, False

# ─────────────────────────────────────────
# SCRAPER 3 — GOOGLE SEARCH COUNT
# ─────────────────────────────────────────

async def scrape_google(page, keyword):
    """
    Google search result count — trend proxy.
    "About X results" → parse karo.
    """
    query = keyword.replace(" ", "+")
    url = f"https://www.google.com/search?q={query}&gl=de&hl=en"

    try:
        print(f"[Google] Checking: {keyword}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(2, 4))

        count_text = ""
        count = 0

        # Google result stats
        selectors = [
            "#result-stats",
            "div#resultStats",
            "[id='result-stats']"
        ]

        for selector in selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    count_text = await el.inner_text()
                    break
            except Exception:
                continue

        # Parse "About 1,23,00,000 results"
        if count_text:
            import re
            numbers = re.findall(r'[\d,]+', count_text)
            if numbers:
                biggest = max(numbers, key=lambda x: len(x.replace(",", "")))
                count = int(biggest.replace(",", ""))

        signal = count >= GOOGLE_MIN_RESULTS

        print(f"[Google] {keyword}: {count_text[:50]} ({count}) — Signal: {signal}")
        save_signal(keyword, "Google", count, count_text[:100])
        return count, signal

    except Exception as e:
        print(f"[Google Error] {keyword}: {e}")
        save_signal(keyword, "Google", 0, "Error")
        return 0, False

# ─────────────────────────────────────────
# COMBINED SIGNAL — Sheet mein update
# ─────────────────────────────────────────

def update_combined_signal(keyword, tiktok_count, ig_count, google_count):
    """
    3 sources mein se 2+ positive = combined signal True.
    Automation 1 isko read karega.
    """
    try:
        tiktok_ok  = tiktok_count  >= TIKTOK_MIN_VIDEOS
        ig_ok      = ig_count      >= INSTAGRAM_MIN_POSTS
        google_ok  = google_count  >= GOOGLE_MIN_RESULTS

        positives = sum([tiktok_ok, ig_ok, google_ok])
        combined  = positives >= 2  # 3 mein se 2+ = signal True

        # creator_count = combined score (max of 3)
        combined_count = max(tiktok_count // 1000, ig_count // 100, google_count // 100000)

        save_signal(keyword, "Combined", combined_count,
                    f"TT:{tiktok_ok} IG:{ig_ok} G:{google_ok} Score:{positives}/3")

        print(f"[Combined] {keyword}: {positives}/3 → Signal={combined}")
        return combined

    except Exception as e:
        print(f"[Combined Error] {e}")
        return False

# ─────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────

async def run_scraper():
    keywords = get_keywords_from_sheet()
    print(f"\n🚀 Social Scraper Starting — {len(keywords)} keywords\n{'─'*50}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-extensions",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Europe/Berlin",
        )

        # Anti-bot — webdriver hide karo
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """)

        page = await context.new_page()

        results_summary = []

        for i, keyword in enumerate(keywords):
            print(f"\n[{i+1}/{len(keywords)}] Keyword: '{keyword}'")

            tiktok_count = ig_count = google_count = 0

            # TikTok
            try:
                tiktok_count, _ = await scrape_tiktok(page, keyword)
                await asyncio.sleep(random.uniform(3, 6))
            except Exception as e:
                print(f"[TikTok Skip] {e}")

            # Instagram
            try:
                ig_count, _ = await scrape_instagram(page, keyword)
                await asyncio.sleep(random.uniform(3, 6))
            except Exception as e:
                print(f"[Instagram Skip] {e}")

            # Google
            try:
                google_count, _ = await scrape_google(page, keyword)
                await asyncio.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"[Google Skip] {e}")

            # Combined signal
            combined = update_combined_signal(keyword, tiktok_count, ig_count, google_count)
            results_summary.append({
                "keyword": keyword,
                "tiktok": tiktok_count,
                "instagram": ig_count,
                "google": google_count,
                "signal": combined
            })

            # Keywords ke beech delay — bot detection avoid karo
            if i < len(keywords) - 1:
                wait = random.uniform(5, 12)
                print(f"[Wait] {wait:.1f}s before next keyword...")
                await asyncio.sleep(wait)

        await browser.close()

    # Summary print
    print(f"\n{'─'*50}")
    print(f"✅ Scraping Done — {len(results_summary)} keywords processed")
    positive = [r for r in results_summary if r["signal"]]
    print(f"📈 Positive signals: {len(positive)}/{len(results_summary)}")
    for r in positive:
        print(f"   ✓ {r['keyword']} — TT:{r['tiktok']:,} IG:{r['instagram']:,} G:{r['google']:,}")

if __name__ == "__main__":
    asyncio.run(run_scraper())
