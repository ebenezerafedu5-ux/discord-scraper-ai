import traceback

try:
    # everything in your current main.py goes here
    # for example, your code that runs the bot
except Exception as e:
    print("Application crashed with error:")
    traceback.print_exc()
    raise e

import os
import asyncio
from fastapi import FastAPI
from playwright.async_api import async_playwright
import httpx

app = FastAPI()

# Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
MIN_MEMBERS = int(os.getenv("MIN_MEMBERS", 4000))
PAGE_LIMIT = int(os.getenv("PAGE_LIMIT", 5))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

# Sites to scrape
SITES = [
    "https://top.gg/servers",
    "https://disboard.org/servers",
    "https://discord.gg/invite"  # placeholder
]

@app.get("/health")
async def health():
    return {"ok": True, "ready": True}

@app.post("/run")
async def run_scraper():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        for site in SITES:
            for page_num in range(1, PAGE_LIMIT + 1):
                url = f"{site}?page={page_num}"
                await page.goto(url)
                await page.wait_for_timeout(2000)  # wait for content to load

                # Example scraping logic (adjust per site)
                server_cards = await page.query_selector_all(".server-card")  # adjust selector
                for card in server_cards:
                    try:
                        name = await card.query_selector_eval(".server-name", "el => el.textContent")
                        tag = await card.query_selector_eval(".server-tag", "el => el.textContent")
                        invite = await card.query_selector_eval("a.invite-link", "el => el.href")
                        members_text = await card.query_selector_eval(".member-count", "el => el.textContent")
                        members = int("".join(filter(str.isdigit, members_text)))
                        if members >= MIN_MEMBERS:
                            results.append({
                                "name": name,
                                "tag": tag,
                                "invite": invite,
                                "members": members
                            })
                    except Exception:
                        continue

        await browser.close()

    # Send to Make.com if webhook exists
    if MAKE_WEBHOOK_URL:
        async with httpx.AsyncClient() as client:
            await client.post(MAKE_WEBHOOK_URL, json=results)

    return {"scraped": len(results)}
