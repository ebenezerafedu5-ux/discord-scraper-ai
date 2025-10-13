import os
import traceback
from typing import List, Dict, Any
import asyncio
import httpx
from fastapi import FastAPI, BackgroundTasks

from playwright.async_api import async_playwright

app = FastAPI()

# ---------------------------
# Environment variables
# ---------------------------
def get_int_env(key: str, default: int) -> int:
    v = os.getenv(key)
    if not v:
        return default
    try:
        return int(v)
    except Exception:
        return default

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
MIN_MEMBERS = get_int_env("MIN_MEMBERS", 4000)
PAGE_LIMIT = get_int_env("PAGE_LIMIT", 5)
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

SITES = [
    "https://top.gg/servers",
    "https://disboard.org/servers",
    "https://discord.gg/invite"
]

# ---------------------------
# Startup event
# ---------------------------
@app.on_event("startup")
async def startup_event():
    print("Startup: Discord scraper app loaded.")
    print(f"MIN_MEMBERS={MIN_MEMBERS}, PAGE_LIMIT={PAGE_LIMIT}, MAKE_WEBHOOK_SET={bool(MAKE_WEBHOOK_URL)}")

# ---------------------------
# Health check
# ---------------------------
@app.get("/health")
async def health():
    return {"ok": True, "ready": True}

# ---------------------------
# Scraper logic
# ---------------------------
async def run_scraper_task():
    results: List[Dict[str, Any]] = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()

            for site in SITES:
                for page_num in range(1, PAGE_LIMIT + 1):
                    url = f"{site}?page={page_num}"
                    try:
                        await page.goto(url, timeout=30000)
                        await page.wait_for_timeout(2000)
                    except Exception as e:
                        print(f"[WARN] Failed to load {url}: {e}")
                        continue

                    server_cards = await page.query_selector_all(".server-card")
                    if not server_cards:
                        server_cards = await page.query_selector_all(".card, .listing, .server")

                    for card in server_cards:
                        try:
                            name = None
                            if await card.query_selector(".server-name"):
                                name = await card.query_selector_eval(".server-name", "el => el.textContent")
                            elif await card.query_selector(".name"):
                                name = await card.query_selector_eval(".name", "el => el.textContent")

                            tag = None
                            if await card.query_selector(".server-tag"):
                                tag = await card.query_selector_eval(".server-tag", "el => el.textContent")

                            invite = None
                            if await card.query_selector("a.invite-link"):
                                invite = await card.query_selector_eval("a.invite-link", "el => el.href")
                            elif await card.query_selector("a[href*='discord.gg']"):
                                invite = await card.query_selector_eval("a[href*='discord.gg']", "el => el.href")

                            members = 0
                            if await card.query_selector(".member-count"):
                                members_text = await card.query_selector_eval(".member-count", "el => el.textContent")
                                members = int("".join(filter(str.isdigit, members_text))) if members_text else 0

                            if members >= MIN_MEMBERS:
                                results.append({
                                    "name": (name or "").strip(),
                                    "tag": (tag or "").strip(),
                                    "invite": invite or "",
                                    "members": members,
                                    "source_page": url
                                })
                        except Exception as e:
                            print(f"[DEBUG] card parse error on {url}: {e}")
                            continue

            await browser.close()

    except Exception as e:
        print("Error while running scraper:")
        traceback.print_exc()
        return

    if MAKE_WEBHOOK_URL and results:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(MAKE_WEBHOOK_URL, json={"results": results})
                print(f"[INFO] Posted to webhook: status={resp.status_code}")
        except Exception as e:
            print(f"[WARN] Failed to post webhook: {e}")

    print(f"✅ Scrape complete. {len(results)} results collected.")

# ---------------------------
# Non-blocking endpoint
# ---------------------------
@app.get("/run")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scraper_task)
    return {"status": "scraping started"}

# ---------------------------
# Root endpoint
# ---------------------------
@app.get("/")
async def root():
    return {"message": "Discord scraping bot is online."}
