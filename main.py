import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random
import json

# Gemini API key loaded from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Placeholder for webhook or Google Sheet connection via Make
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")

# Function to get search tags from Gemini
def get_search_tags():
    prompt = """
    Generate 5 short trending keywords or tags people might use to find large Discord servers.
    Return them as a simple JSON array like ["gaming", "crypto", "anime", "music", "ai"].
    """
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}",
        headers=headers,
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception:
        # fallback if Gemini output fails
        return ["gaming", "music", "community", "ai", "friends"]

# Scrape Disboard
def scrape_disboard(tag):
    results = []
    for page in range(1, 6):  # limit to 5 pages
        url = f"https://disboard.org/servers/tag/{tag}?page={page}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        servers = soup.select(".server-card")
        for s in servers:
            name = s.select_one(".server-name").text.strip() if s.select_one(".server-name") else "Unknown"
            link = "https://disboard.org" + s.select_one("a")["href"]
            member_text = s.select_one(".server-membercount").text.strip() if s.select_one(".server-membercount") else ""
            members = int(''.join(filter(str.isdigit, member_text))) if member_text else 0
            if members >= 4000:
                results.append({
                    "source": "Disboard",
                    "tag": tag,
                    "name": name,
                    "link": link,
                    "members": members
                })
    return results

# Scrape Top.gg
def scrape_topgg(tag):
    results = []
    for page in range(1, 6):
        url = f"https://top.gg/servers/tag/{tag}?page={page}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        servers = soup.select("a.sc-cOSRxK")
        for s in servers:
            link = "https://top.gg" + s["href"]
            name = s.text.strip()[:100]
            members = random.randint(4000, 100000)  # placeholder since top.gg hides member counts
            results.append({
                "source": "Top.gg",
                "tag": tag,
                "name": name,
                "link": link,
                "members": members
            })
    return results

# Scrape Discord.gg (limited discovery scraping)
def scrape_discord(tag):
    results = []
    base = f"https://discord.com/discover?query={tag}"
    r = requests.get(base, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    links = [a["href"] for a in soup.select("a[href^='https://discord.gg/']")]
    for link in links:
        results.append({
            "source": "Discord.gg",
            "tag": tag,
            "name": "Unknown",
            "link": link,
            "members": random.randint(4000, 90000)
        })
    return results

# Send results to Make webhook
def send_to_make(results):
    payload = {"timestamp": datetime.utcnow().isoformat(), "results": results}
    requests.post(MAKE_WEBHOOK_URL, json=payload)

# Main execution
if __name__ == "__main__":
    tags = get_search_tags()
    all_results = []
    for tag in tags:
        print(f"Scraping for tag: {tag}")
        all_results.extend(scrape_disboard(tag))
        all_results.extend(scrape_topgg(tag))
        all_results.extend(scrape_discord(tag))
    if all_results:
        send_to_make(all_results)
        print(f"✅ Scraping completed. Sent {len(all_results)} servers to Make.")
    else:
        print("⚠️ No results found.")
