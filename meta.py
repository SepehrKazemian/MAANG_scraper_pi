import asyncio
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from pyppeteer import launch
import telegram as tel
import sys
import functools

print = functools.partial(print, flush=True)

FILTERED_URL = (
    "https://www.metacareers.com/jobs?"
    "roles[0]=Full%20time%20employment&sort_by_new=true&q=Machine%20learning"
    "&teams[0]=Software%20Engineering&teams[1]=Data%20%26%20Analytics"
)
SEEN_FILE = "seen_jobs_meta.txt"

# --- Load/Save Seen Jobs ---
def load_seen_jobs():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set("::".join(line.strip().split("::")[:2]) for line in f if line.strip() and "::" in line)

def save_seen_job(url, title, location, date):
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(f"{url}::{title} — {location}::{date}\n")

# --- Main Scraper ---
async def main():
    print("Meta scraper (pyppeteer version) started.")
    first_run = not os.path.exists(SEEN_FILE) or os.stat(SEEN_FILE).st_size == 0
    seen_jobs = load_seen_jobs()
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
            paged_url = f"{FILTERED_URL}&page={page_num}"
            print(f"🔗 Loading Meta page {page_num}: {paged_url}")

            new_jobs_found_page = 0

            try:
                await page.goto(paged_url, timeout=30000)
                await asyncio.sleep(3)  # You asked to keep logic same for now
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                job_links = soup.find_all("a", href=lambda x: x and x.startswith("/jobs/"))

                if not job_links:
                    if page_num == 1:
                        print(f"⚠️ No job links found on first page. Structure might have changed.")
                    else:
                        print(f"✅ No more job listings found. Exiting pagination.")
                    break  # ✅ Stop if no job links found

                print(f"Found {len(job_links)} potential job links on page {page_num}.")

                processed_hrefs_on_page = set()

                for job_link_tag in job_links:
                    href = job_link_tag.get("href")
                    if not href or href in processed_hrefs_on_page:
                        continue
                    processed_hrefs_on_page.add(href)
                    full_url = f"https://www.metacareers.com{href}"

                    title = "Unknown Title"
                    location = "Unknown Location"
                    try:
                        title_div = job_link_tag.find("div", class_="_6g3g")
                        title = title_div.get_text(strip=True) if title_div else "Unknown Title"

                        location_tag = job_link_tag.find("span")
                        location = location_tag.get_text(strip=True) if location_tag else "Unknown Location"

                        if title == "Unknown Title" or location == "Unknown Location":
                            all_text = job_link_tag.get_text(" | ", strip=True)
                            parts = all_text.split("|", 1)
                            title = parts[0].strip() if parts else all_text
                            location = parts[1].strip() if len(parts) > 1 else "Unknown Location"

                    except Exception as e:
                        print(f"Error parsing job details for {full_url}: {e}", file=sys.stderr)
                        tel.send_notification(f"Error parsing Meta job details: {full_url}")

                    today = datetime.now().strftime("%Y-%m-%d")
                    job_key = f"{full_url}::{title} — {location}"

                    if job_key not in seen_jobs:
                        new_jobs_found_page += 1
                        seen_jobs.add(job_key)
                        save_seen_job(full_url, title, location, today)

                        if not first_run:
                            print(f"✨ New Meta Job Found: {title} — {location}")
                            tel.send_notification(f"Meta: 🔹 {title} — {location} \n🔗 {full_url}")
                        else:
                            print(f"Found (first run): {title} — {location}")

                if new_jobs_found_page == 0:
                    print(f"No new jobs found on Meta page {page_num}.")

            except Exception as e:
                print(f"❌ Error scraping Meta page {page_num}: {e}", file=sys.stderr)
                # ✅ Even if error happens, go to next page

            page_num += 1
            await asyncio.sleep(3)

    finally:
        await browser.close()
        print(f"Meta scraper finished. Found {new_jobs_found_overall} new jobs overall.")

# --- Run if standalone ---
if __name__ == "__main__":
    asyncio.run(main())
