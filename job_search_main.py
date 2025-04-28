import asyncio
import meta as meta
import google as ggl
import microsoft as micr
import deepmind as dm
import time
import functools
import requests
import subprocess
from stem import Signal
from stem.control import Controller
import os
import sys

# Auto-flush print
print = functools.partial(print, flush=True)

# --- TOR Proxy Config ---
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050',
}

def rotate_tor_ip():
    with Controller.from_port(port=9051) as c:
        c.authenticate()
        c.signal(Signal.NEWNYM)

# --- TOR IP Test ---
try:
    print("Testing TOR connection...")
    tor_ip = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10).text
    print("TOR IP:", tor_ip)
except Exception as e:
    print(f"❌ Error testing TOR connection: {e}", file=sys.stderr)

# --- Scraping Loop ---
async def job_search_cycle():
    while True:
        print("\n--- Starting new job search cycle ---")

        # --- Meta ---
        try:
            print("Running Meta scraper...")
            await meta.main()  # async
            print("Meta scraper finished.")
        except Exception as e:
            print(f"❌ Error running Meta scraper: {e}", file=sys.stderr)

        # Rotate TOR IP after Meta
        try:
            print("Rotating TOR IP...")
            rotate_tor_ip()
            await asyncio.sleep(5)  # fixed: must be await not time.sleep
        except Exception as e:
            print(f"❌ Error rotating TOR IP: {e}", file=sys.stderr)

        # --- Microsoft ---
        try:
            print("Running Microsoft scraper...")
            await micr.main()  # async
            print("Microsoft scraper finished.")
        except Exception as e:
            print(f"❌ Error running Microsoft scraper: {e}", file=sys.stderr)

        # --- Google ---
        try:
            print("Running Google scraper...")
            ggl.main()  # normal function, no await
            print("Google scraper finished.")
        except Exception as e:
            print(f"❌ Error running Google scraper: {e}", file=sys.stderr)

        # --- DeepMind ---
        try:
            print("Running DeepMind scraper...")
            dm.main()  # normal function, no await
            print("DeepMind scraper finished.")
        except Exception as e:
            print(f"❌ Error running DeepMind scraper: {e}", file=sys.stderr)

        print(f"--- Cycle finished. Waiting for 600 seconds (10 minutes)... ---")
        await asyncio.sleep(600)

# --- Run everything ---
if __name__ == "__main__":
    print("Starting async job search system...")
    asyncio.run(job_search_cycle())
