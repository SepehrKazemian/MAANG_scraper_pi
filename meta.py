import time
import os
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup
import pychrome
import telegram as tel
import functools

print = functools.partial(print, flush=True)
FILTERED_URL = "https://www.metacareers.com/jobs?roles[0]=Full%20time%20employment&sort_by_new=true&q=Machine%20learning&teams[0]=Software%20Engineering&teams[1]=Data%20%26%20Analytics"
SEEN_FILE = "seen_jobs_meta.txt"

# Load previously seen jobs
def load_seen_jobs():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        # Key format in file: url::title — location::date
        # Key format needed for check: url::title — location
        return set("::".join(line.strip().split("::")[:2]) for line in f if line.strip() and "::" in line)

# Save newly seen job
def save_seen_job(url, title, location, date):
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(f"{url}::{title} — {location}::{date}\n")

def run(port):
    print("Meta scraper using pychrome started.")
    first_run = not os.path.exists(SEEN_FILE) or os.stat(SEEN_FILE).st_size == 0
    seen_jobs = load_seen_jobs()

    try:
        browser = pychrome.Browser(url=f"http://127.0.0.1:{port}")
        tab = browser.new_tab()
        tab.start()
    except pychrome.exceptions.ConnectionError as e:
        print(f"❌ Error connecting to Chromium for Meta on port {port}: {e}", file=sys.stderr) # Added sys import needed
        return # Cannot proceed without browser connection

    page_num = 1
    new_jobs_found_overall = 0

    while True:
        paged_url = f"{FILTERED_URL}&page={page_num}"
        print(f"🔗 Loading Meta page {page_num}: {paged_url}")
        try:
            tab.call_method("Page.navigate", url=paged_url, _timeout=30) # Add timeout
            # Wait for page load event or a reasonable timeout
            tab.wait(15) # Increased wait time slightly

            # Get HTML after JavaScript execution
            html_result = tab.call_method("Runtime.evaluate", expression="document.documentElement.outerHTML", _timeout=20)
            if not html_result or 'result' not in html_result or 'value' not in html_result['result']:
                 print(f"❌ Failed to get HTML content from Meta page {page_num}.", file=sys.stderr)
                 break
            html = html_result['result']['value']
            soup = BeautifulSoup(html, "html.parser")

            # Selector based on previous version - might need updates if site changed
            job_links = soup.find_all("a", href=lambda x: x and x.startswith("/jobs/"))

            if not job_links:
                if page_num == 1:
                     print(f"⚠️ No job links found on the first page for Meta. Structure might have changed or no jobs available for query.")
                else:
                     print("✅ No more job listings found for Meta. Exiting pagination.")
                break

            print(f"Found {len(job_links)} potential job links on page {page_num}.")
            new_jobs_found_on_page = 0
            processed_hrefs_on_page = set() # Track hrefs processed on the current page

            for job_link_tag in job_links:
                href = job_link_tag.get("href")
                if not href or href in processed_hrefs_on_page:
                    continue
                processed_hrefs_on_page.add(href)
                full_url = f"https://www.metacareers.com{href}"

                title = "Unknown Title"
                location = "Unknown Location"
                try:
                    # Selectors based on previous version - might need updates
                    title_div = job_link_tag.find("div", class_="_6g3g") # Example old selector
                    title = title_div.get_text(strip=True) if title_div else "Unknown Title"

                    # Find location - might be sibling or child depending on structure
                    location_tag = job_link_tag.find("span") # Example old selector, adjust as needed
                    location = location_tag.get_text(strip=True) if location_tag else "Unknown Location"

                    # Fallback if specific selectors fail
                    if title == "Unknown Title" or location == "Unknown Location":
                        all_text = job_link_tag.get_text(" | ", strip=True)
                        parts = all_text.split("|", 1)
                        title = parts[0].strip() if parts else all_text
                        location = parts[1].strip() if len(parts) > 1 else "Unknown Location"

                except Exception as e:
                    print(f"Error parsing job details for {full_url}: {e}", file=sys.stderr)
                    tel.send_notification(f"Error parsing Meta job details: {full_url}") # Optional notification

                today = datetime.now().strftime("%Y-%m-%d")
                # Key format for checking: url::title — location
                job_key = f"{full_url}::{title} — {location}"

                if job_key not in seen_jobs:
                    new_jobs_found_on_page += 1
                    new_jobs_found_overall += 1
                    if not first_run:
                        print(f"✨ New Meta Job Found: {title} — {location}")
                        tel.send_notification(f"Meta: 🔹 {title} — {location} \n🔗 {full_url}")
                    else:
                        print(f"Found (first run): {title} — {location}")

                    save_seen_job(full_url, title, location, today)
                    seen_jobs.add(job_key) # Add to in-memory set

            if new_jobs_found_on_page == 0:
                print(f"No new jobs found on Meta page {page_num}.")

            page_num += 1
            time.sleep(3) # Be polite

        except (pychrome.exceptions.TimeoutException, pychrome.exceptions.CallMethodException) as e:
             print(f"❌ Error interacting with browser for Meta page {page_num}: {e}", file=sys.stderr)
             break # Stop pagination on browser error
        except Exception as e:
             print(f"❌ Unexpected error on Meta page {page_num}: {e}", file=sys.stderr)
             break # Stop on other errors too

    # Cleanup browser tab
    try:
        tab.stop()
        # Consider closing the browser if it's only used for this scraper run
        # browser.close_tab(tab)
    except Exception as e:
        print(f"Error stopping browser tab for Meta: {e}", file=sys.stderr)

    print(f"Meta scraper finished. Found {new_jobs_found_overall} new jobs overall.")


# Keep the main block for potential direct testing, but it needs the browser running
if __name__ == "__main__":
    import sys # Need sys for stderr printing
    print("Running Meta scraper standalone (requires Chromium running with remote debugging on port 9222)...")
    # Example: Start Chromium manually first if needed:
    # chromium-browser --headless --no-sandbox --remote-debugging-port=9222 --proxy-server=socks5://127.0.0.1:9050 --user-data-dir=/tmp/chrome-meta
    test_port = 9222
    interval = 600 # Example interval
    while True:
        run(test_port)
        print(f"\n[⏳] Sleeping for {interval//60} minutes...\n")
        time.sleep(interval)
