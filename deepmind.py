
from google import load_seen_jobs, save_seen_jobs, get_jobs_request, notify_job
from datetime import datetime
import re

SEEN_FILE = "seen_jobs_deepmind.txt"
locations = ["Zurich, Switzerland", "Mountain View, California, US", "New York City, New York, US"]

def main():
    seen_dm = load_seen_jobs(SEEN_FILE)
    updated_dm = fetch_deepmind_jobs(seen_dm)
    save_seen_jobs(SEEN_FILE, updated_dm)

def fetch_deepmind_jobs(seen_jobs):
    print("deepmind search started!")
    base_url = "https://boards-api.greenhouse.io/v1/boards/deepmind/jobs"
    jobs = get_jobs_request(base_url, page = None)
    if jobs is None:
        return seen_jobs

    new_jobs = []
    seen_set = set(seen_jobs)

    for job in jobs:
        title = job.get("title", "").strip()
        pattern = re.compile(r'\b(engineer|scientist)\b', re.IGNORECASE)
        if not pattern.search(title):
            continue

        location = job.get("location", {}).get("name", "")
        updated_raw = job.get("first_published", "")
        apply_url = job.get("absolute_url", "")

        if not title or not location or not updated_raw:
            continue

        if not any(loc in location for loc in locations):
            continue

        try:
            updated = datetime.fromisoformat(updated_raw).strftime("%Y-%m-%d %H:%M")
        except:
            updated = "Unknown"

        job_key = f"{title}::{updated}"

        if job_key in seen_set:
            continue

        # notify_job("DeepMind", title, location, updated, apply_url)
        new_jobs.append(job_key)
        seen_set.add(job_key)

    return seen_jobs + new_jobs

if __name__ == "__main__":
    import time
    INTERVAL = 20
    while True:
        print("\n🔍 Checking for jobs...")

        main()

        print(f"\n[⏳] Sleeping for {INTERVAL//60} minutes...\n")
        time.sleep(INTERVAL)