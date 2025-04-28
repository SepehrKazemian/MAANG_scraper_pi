import time
import os
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup
import pychrome
import telegram as tel
import functools
import re
import sys # Added for error printing

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

# Ensure the seen jobs file exists
def ensure_seen_file():
    if not os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "w", encoding="utf-8") as f:
                pass # Just create the file
        except Exception as e:
             print(f"Error creating seen jobs file {SEEN_FILE}: {e}", file=sys.stderr)


# Load previously seen jobs
def load_seen_jobs():
    ensure_seen_file()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            # Key format in file: url::title — location::date
            # Key format needed for check: url::title — location
            seen = set()
            for line in f:
                if line.strip():
                    parts = line.strip().split("::", 2)
                    if len(parts) >= 2:
                        seen.add(f"{parts[0]}::{parts[1]}")
            return seen
    except Exception as e:
        print(f"Error loading seen jobs from {SEEN_FILE}: {e}", file=sys.stderr)
        return set()


# Save newly seen job
def save_seen_job(url, title, location, date):
     try:
        with open(SEEN_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url}::{title} — {location}::{date}\n")
     except Exception as e:
        print(f"Error saving seen job to {SEEN_FILE}: {e}", file=sys.stderr)


def run(port):
    print("Microsoft scraper using pychrome started.")
    ensure_seen_file() # Ensure file exists before checking size
    first_run = os.stat(SEEN_FILE).st_size == 0
    seen_jobs = load_seen_jobs()

    try:
        browser = pychrome.Browser(url=f"http://127.0.0.1:{port}")
        tab = browser.new_tab()
        tab.start()
    except pychrome.exceptions.ConnectionError as e:
        print(f"❌ Error connecting to Chromium for Microsoft on port {port}: {e}", file=sys.stderr)
        return # Cannot proceed

    page = 1
    new_jobs_found_overall = 0

    while True:
        url = BASE_URL.format(page=page)
        print(f"\n🔗 Loading Microsoft page {page}: {url}", flush=True)

        try:
            tab.call_method("Page.navigate", url=url, _timeout=30) # Add timeout
            tab.wait(15) # Increased wait

            html_result = tab.call_method("Runtime.evaluate", expression="document.documentElement.outerHTML", _timeout=20)
            if not html_result or 'result' not in html_result or 'value' not in html_result['result']:
                 print(f"❌ Failed to get HTML content from Microsoft page {page_num}.", file=sys.stderr)
                 break
            html = html_result['result']['value']
            soup = BeautifulSoup(html, "html.parser")

            # Selectors based on previous version - MIGHT NEED UPDATING
            job_cards = soup.find_all("div", class_="ms-DocumentCard")

            if not job_cards:
                if page == 1:
                    print("❌ Failed to find job listings on first page for Microsoft. Check layout or query.")
                else:
                    print("✅ No more job listings found for Microsoft. Stopping pagination.\n")
                break

            print(f"📄 Found {len(job_cards)} jobs on page {page}:\n")
            new_jobs_found_on_page = 0

            for card in job_cards:
                title = "Unknown Title"
                location_text = "Unknown Location"
                date_text = "Unknown Date"
                job_id = None
                job_url = None

                try:
                    # Selectors based on previous version - MIGHT NEED UPDATING
                    title_tag = card.find("h2")
                    title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

                    location_tag = card.find("i", {"data-icon-name": "POI"})
                    location_text = location_tag.find_next("span").get_text(strip=True) if location_tag and location_tag.find_next("span") else "Unknown Location"

                    date_tag = card.find("i", {"data-icon-name": "Clock"})
                    date_text = date_tag.find_next("span").get_text(strip=True) if date_tag and date_tag.find_next("span") else "Unknown Date"

                    # Job ID from outer parent div (aria-label="Job item 1814029") - MIGHT NEED UPDATING
                    parent_div = card.find_parent("div", attrs={"aria-label": re.compile(r"Job item \d+")})
                    if parent_div:
                        match = re.search(r"Job item (\d+)", parent_div.get("aria-label", ""))
                        if match:
                            job_id = match.group(1)

                    if not title or title == "Unknown Title" or not location_text or location_text == "Unknown Location" or not job_id:
                         # Try finding link directly if other methods fail
                         link_tag = card.find("a", href=re.compile(r"/global/en/job/\d+/"))
                         if link_tag:
                             job_url = f"https://jobs.careers.microsoft.com{link_tag['href']}"
                             if title == "Unknown Title":
                                 title = link_tag.get_text(strip=True) or "Unknown Title from Link"
                         else:
                             print(f"⚠️ Skipping card, couldn't extract essential info (Title: {title}, Loc: {location_text}, ID: {job_id})", file=sys.stderr)
                             print(f"   Card HTML snippet: {str(card)[:200]}...")
                             continue # Skip card

                    # Construct URL if not found via direct link
                    if not job_url:
                        slug = title.lower().replace(" ", "-").replace("–", "-").replace("&", "").replace(",", "").replace("’", "").replace(":", "")
                        slug = re.sub(r"[^a-z0-9\-]", "", slug)
                        slug = slug[:80] # Limit slug length
                        job_url = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}/{slug}"

                    # Key format: url::title — location
                    job_key = f"{job_url}::{title} — {location_text}"

                    if job_key not in seen_jobs:
                        new_jobs_found_on_page += 1
                        new_jobs_found_overall += 1
                        if not first_run:
                            print(f"✨ New Microsoft Job Found: {title} — {location_text}")
                            # tel.send_notification(f"Microsoft: 🔹 {title} — {location_text} \n🕒 {date_text} \n🔗 {job_url}")
                        else:
                            print(f"Found (first run): {title} — {location_text}")

                        save_seen_job(job_url, title, location_text, datetime.now().strftime("%Y-%m-%d"))
                        seen_jobs.add(job_key) # Add to in-memory set

                except Exception as e:
                    print(f"❌ Error processing Microsoft job card: {e}", file=sys.stderr)
                    print(f"   Card HTML snippet: {str(card)[:200]}...")
                    continue # Skip to next card

            if new_jobs_found_on_page == 0:
                print(f"No new jobs found on Microsoft page {page}.")

            page += 1
            time.sleep(3) # Be polite

        except (pychrome.exceptions.TimeoutException, pychrome.exceptions.CallMethodException) as e:
             print(f"❌ Error interacting with browser for Microsoft page {page}: {e}", file=sys.stderr)
             break # Stop pagination on browser error
        except Exception as e:
             print(f"❌ Unexpected error on Microsoft page {page}: {e}", file=sys.stderr)
             break # Stop on other errors too

    # Cleanup browser tab
    try:
        tab.stop()
    except Exception as e:
        print(f"Error stopping browser tab for Microsoft: {e}", file=sys.stderr)

    print(f"Microsoft scraper finished. Found {new_jobs_found_overall} new jobs overall.")


# Keep main block for testing
if __name__ == "__main__":
    print("Running Microsoft scraper standalone (requires Chromium running with remote debugging on port 9223)...")
    # Example: Start Chromium manually first if needed:
    # chromium-browser --headless --no-sandbox --remote-debugging-port=9223 --user-data-dir=/tmp/chrome-microsoft
    test_port = 9223
    interval = 600
    while True:
        run(test_port)
        print(f"\n[⏳] Sleeping for {interval//60} minutes...\n")
        time.sleep(interval)
