import asyncio
import os
import re
import functools
import sys
from datetime import datetime
from bs4 import BeautifulSoup
from pyppeteer import launch
import telegram as tel

print = functools.partial(print, flush=True)

BASE_URL = (
    "https://jobs.careers.microsoft.com/global/en/search?"
    "q=ai&lc=Canada&lc=United%20States"
    "&p=Research%2C%20Applied%2C%20%26%20Data%20Sciences"
    "&p=Software%20Engineering"
    "&d=Data%20Science&d=Software%20Engineering"
    "&exp=Experienced%20professionals"
    "&et=Full-Time&l=en_us"
    "&pg={page}&pgSz=20&o=Recent"
)
SEEN_FILE = "seen_jobs_microsoft.txt"

# --- Seen Jobs Utilities ---
def ensure_seen_file():
    if not os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "w", encoding="utf-8"):
            pass

def load_seen_jobs():
    ensure_seen_file()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set("::".join(line.strip().split("::")[:2]) for line in f if line.strip() and "::" in line)
    except Exception as e:
        print(f"❌ Error loading seen jobs: {e}", file=sys.stderr)
        return set()

def save_seen_job(url, title, location, date):
    try:
        with open(SEEN_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url}::{title} — {location}::{date}\n")
    except Exception as e:
        print(f"❌ Error saving seen job: {e}", file=sys.stderr)

# --- Main Scraper ---
async def main():
    print("Microsoft scraper (pyppeteer version) started.")

    seen_jobs = load_seen_jobs()
    first_run = len(seen_jobs) == 0
    new_jobs_found_overall = 0

    browser = await launch({
        'headless': True,
        'executablePath': '/usr/bin/chromium-browser',
        'args': ['--no-sandbox', '--disable-gpu']
    })

    page = await browser.newPage()
    page_num = 1

    try:
        while True:
            url = BASE_URL.format(page=page_num)
            print(f"🔗 Loading Microsoft page {page_num}: {url}")

            try:
                await page.goto(url, timeout=30000)
                await page.waitForSelector('div.ms-DocumentCard', timeout=15000)  # ✅ Wait properly for job cards

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                job_cards = soup.find_all("div", class_="ms-DocumentCard")

                if not job_cards:
                    if page_num == 1:
                        print("❌ Failed to find job listings on first page. Check layout or query.")
                    else:
                        print("✅ No more job listings found. Stopping pagination.\n")
                    break  # ✅ No jobs → Stop pagination

                print(f"📄 Found {len(job_cards)} jobs on page {page_num}.")

                new_jobs_found_page = 0

                for card in job_cards:
                    try:
                        title_tag = card.find("h2")
                        title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

                        location_tag = card.find("i", {"data-icon-name": "POI"})
                        location_text = location_tag.find_next("span").get_text(strip=True) if location_tag else "Unknown Location"

                        date_tag = card.find("i", {"data-icon-name": "Clock"})
                        date_text = date_tag.find_next("span").get_text(strip=True) if date_tag else "Unknown Date"

                        parent_div = card.find_parent("div", attrs={"aria-label": re.compile(r"Job item \d+")})
                        job_id = None
                        if parent_div:
                            match = re.search(r"Job item (\d+)", parent_div.get("aria-label", ""))
                            if match:
                                job_id = match.group(1)

                        link_tag = card.find("a", href=re.compile(r"/global/en/job/\d+/"))
                        job_url = None
                        if link_tag:
                            job_url = f"https://jobs.careers.microsoft.com{link_tag['href']}"
                            if title == "Unknown Title":
                                title = link_tag.get_text(strip=True) or "Unknown Title"

                        if not job_url and job_id:
                            slug = title.lower().replace(" ", "-").replace("–", "-").replace("&", "").replace(",", "").replace("’", "").replace(":", "")
                            slug = re.sub(r"[^a-z0-9\-]", "", slug)
                            slug = slug[:80]
                            job_url = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}/{slug}"

                        if not job_url:
                            print(f"⚠️ Skipping card (no URL): {title} — {location_text}")
                            continue

                        job_key = f"{job_url}::{title} — {location_text}"

                        if job_key not in seen_jobs:
                            new_jobs_found_page += 1
                            new_jobs_found_overall += 1
                            seen_jobs.add(job_key)
                            save_seen_job(job_url, title, location_text, datetime.now().strftime("%Y-%m-%d"))

                            if not first_run:
                                print(f"✨ New Job Found: {title} — {location_text}")
                                tel.send_notification(f"Microsoft: 🔹 {title} — {location_text} \n🕒 {date_text} \n🔗 {job_url}")
                            else:
                                print(f"Found (first run): {title} — {location_text}")

                    except Exception as e:
                        print(f"❌ Error processing job card: {e}", file=sys.stderr)
                        continue

                if new_jobs_found_page == 0:
                    print(f"No new jobs found on Microsoft page {page_num}.")

                page_num += 1
                await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ Error on Microsoft page {page_num}: {e}", file=sys.stderr)
                break  # ✅ Break loop if page fails badly

    finally:
        await browser.close()
        print(f"Microsoft scraper finished. Found {new_jobs_found_overall} new jobs overall.")

# --- Standalone run ---
if __name__ == "__main__":
    print("Running Microsoft scraper standalone...")
    asyncio.run(main())
