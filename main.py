# main.py
import os
import traceback
from typing import List, Dict, Any

from fastapi import FastAPI
from playwright.async_api import async_playwright
import httpx

app = FastAPI()

# ---------------------------
# Safe env parsing helpers
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

# Default target sites (you can edit)
SITES = [
    "https://top.gg/servers",
    "https://disboard.org/servers",
    "https://discord.gg/invite"
]

# ---------------------------
# Startup logging (non-blocking)
# ---------------------------
@app.on_event("startup")
async def startup_event():
    # Minimal info so logs show relevant config without leaking secrets
    print("Startup: Discord scraper app loaded.")
    print(f"MIN_MEMBERS={MIN_MEMBERS}, PAGE_LIMIT={PAGE_LIMIT}, MAKE_WEBHOOK_SET={bool(MAKE_WEBHOOK_URL)}")

# ---------------------------
# Health endpoint
# ---------------------------
@app.get("/health")
async def health():
    return {"ok": True, "ready": True}

# ---------------------------
# Run scraper endpoint
# ---------------------------
@app.post("/run")
async def run_scraper() -> Dict[str, Any]:
    """
    POST /run  -> launches Playwright, scrapes configured SITES up to PAGE_LIMIT,
    returns a summary and a small sample of results. If MAKE_WEBHOOK_URL is set,
    tries to POST results to that webhook (non-fatal on failure).
    """
    results: List[Dict[str, Any]] = []

    try:
        async with async_playwright() as p:
            # Launch with common flags used in containers
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
                        await page.goto(url, timeout=30000)  # 30s per page
                        await page.wait_for_timeout(2000)     # small wait for JS
                    except Exception as e:
                        print(f"[WARN] Failed to load {url}: {e}")
                        continue

                    # Primary selector (may need adjustment per site)
                    server_cards = await page.query_selector_all(".server-card")
                    if not server_cards:
                        # fallback attempt: try some generic selectors
                        server_cards = await page.query_selector_all(".card, .listing, .server")

                    for card in server_cards:
                        try:
                            # defensive selector extraction: check existence before eval
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

                            # only capture if meets threshold
                            if members >= MIN_MEMBERS:
                                results.append({
                                    "name": (name or "").strip(),
                                    "tag": (tag or "").strip(),
                                    "invite": invite or "",
                                    "members": members,
                                    "source_page": url
                                })
                        except Exception as e:
                            # single-card parse error should not stop the whole run
                            print(f"[DEBUG] card parse error on {url}: {e}")
                            continue

            await browser.close()

    except Exception as e:
        print("Error while running scraper:")
        traceback.print_exc()
        return {"error": str(e)}

    # If webhook is set, try to post results (failure here shouldn't be fatal)
    if MAKE_WEBHOOK_URL and results:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(MAKE_WEBHOOK_URL, json={"results": results})
                print(f"[INFO] Posted to webhook: status={resp.status_code}")
        except Exception as e:
            print(f"[WARN] Failed to post webhook: {e}")

    # Limit return size so logs/responses don't explode
    return {"scraped": len(results), "sample": results[:20]}
