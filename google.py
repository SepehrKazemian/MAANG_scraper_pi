import requests
import time
from datetime import datetime
import telegram as tel
import functools

print = functools.partial(print, flush=True)
SEARCH_TERM = "ai"
LOCATION = "Canada"
INTERVAL = 600  # in seconds (10 minutes)
SEEN_FILE = "seen_jobs_google.txt"

def get_jobs_request(url, page = None):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Error fetching{f' page {page}' if page is not None else ''}: {response.status_code}")
        return None

    data = response.json()
    jobs = data.get("jobs", [])

    if not jobs:
        print(f"[✓] No more jobs on page {f' page {page}' if page is not None else ''}. Stopping.")
        return None
    return jobs

def load_seen_jobs(SEEN_FILE):
    try:
        with open(SEEN_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def save_seen_jobs(SEEN_FILE, seen_jobs):
    # Sort by datetime extracted from job_key (title::timestamp)
    seen_jobs = sorted(seen_jobs, key=lambda x: x.split("::")[-1])
    with open(SEEN_FILE, "w") as f:
        for job in seen_jobs:
            f.write(job + "\n")

def notify_job(company, title, location, created_date, job_url):
    tel.send_notification(f"\n🔔 {company} Job: {title} [{location}] \n🕒 Oppened: {created_date}\n🔗 URL: {job_url}")

def main():
    seen_jobs = load_seen_jobs(SEEN_FILE)
    updated_jobs = fetch_all_jobs(seen_jobs)
    save_seen_jobs(SEEN_FILE, updated_jobs)

def fetch_all_jobs(seen_jobs):
    base_url = "https://careers.google.com/api/v3/search/"
    page = 1
    new_jobs = []

    seen_set = set(seen_jobs)

    while True:
        url = (
            f"{base_url}?q={SEARCH_TERM.replace(' ', '+')}"
            f"&location={LOCATION}&page={page}"
        )

        jobs = get_jobs_request(url, page = page)
        if jobs is None:
            break

        for job in jobs:
            title = job.get("title", "")
            apply_url = job.get("apply_url", "")
            location = job.get("locations", [{}])[0].get("display", "Unknown Location")

            created_raw = job.get("created", "")
            created = "Unknown"
            if created_raw:
                try:
                    created = datetime.fromisoformat(
                        created_raw.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    print(f"⚠️ Could not parse created date: {created_raw}")

            job_key = f"{title}::{created}"

            if job_key in seen_set:
                continue
            print(job_key)

            # notify_job("Google", title, location, created, apply_url)
            new_jobs.append(job_key)
            seen_set.add(job_key)

        page += 1

    return seen_jobs + new_jobs  # combine existing and new

if __name__ == "__main__":
    while True:
        print("\n🔍 Checking for jobs...")

        main()

        print(f"\n[⏳] Sleeping for {INTERVAL//60} minutes...\n")
        time.sleep(INTERVAL)
