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
import sys # Import sys for stderr printing

def rotate_tor_ip():
    with Controller.from_port(port=9051) as c:
        c.authenticate()
        c.signal(Signal.NEWNYM)

def launch_chromium_with_tor():
    subprocess.Popen([
        "chromium-browser",
        "--headless",  # optional, remove if you want UI
        "--no-sandbox",
        "--remote-debugging-port=9222",
        "--proxy-server=socks5://127.0.0.1:9050",
        "--user-data-dir=/tmp/chrome",
        "--log-level=3",
        "--disable-logging"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())

def restart_chromium(port, user_data_dir, tor=False):
    subprocess.run(["pkill", "-f", f"chromium-browser.*--remote-debugging-port={port}"])
    time.sleep(2)

    command = [
        "chromium-browser",
        "--headless",
        "--no-sandbox",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}"
    ]
    if tor:
        command.append("--proxy-server=socks5://127.0.0.1:9050")
        command.append("--log-level=3")
        command.append("--disable-logging")
        rotate_tor_ip()
        time.sleep(5)

    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())

restart_chromium(port=9222, user_data_dir="/tmp/chrome-meta", tor=True)  # Meta
restart_chromium(port=9223, user_data_dir="/tmp/chrome-microsoft", tor=False)  # Microsoft

proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050',
}

print("TOR IP:", requests.get("http://httpbin.org/ip", proxies=proxies).text)

print = functools.partial(print, flush=True)
print("starting process")
while True:
    print("\n--- Starting new job search cycle ---")

    # --- Meta ---
    try:
        print("Running Meta scraper...")
        meta.run(port=9222)
        print("Meta scraper finished.")
    except Exception as e:
        print(f"❌ Error running Meta scraper: {e}", file=sys.stderr)

    # --- Microsoft ---
    try:
        print("Running Microsoft scraper...")
        micr.run(port=9223)
        print("Microsoft scraper finished.")
    except Exception as e:
        print(f"❌ Error running Microsoft scraper: {e}", file=sys.stderr)

    # Add a small delay to allow pychrome background thread to potentially clean up
    time.sleep(2)

    # --- Google ---
    try:
        print("Running Google scraper...")
        ggl.main()
        print("Google scraper finished.")
    except Exception as e:
        print(f"❌ Error running Google scraper: {e}", file=sys.stderr)

    # --- DeepMind ---
    try:
        print("Running DeepMind scraper...")
        dm.main()
        print("DeepMind scraper finished.")
    except Exception as e:
        print(f"❌ Error running DeepMind scraper: {e}", file=sys.stderr)

    # --- Restart Browsers ---
    print("Restarting Chromium instances...")
    try:
        restart_chromium(port=9222, user_data_dir="/tmp/chrome-meta", tor=True)  # Meta
    except Exception as e:
        print(f"❌ Error restarting Meta Chromium: {e}", file=sys.stderr)

    try:
        restart_chromium(port=9223, user_data_dir="/tmp/chrome-microsoft", tor=False)  # Microsoft
    except Exception as e:
        print(f"❌ Error restarting Microsoft Chromium: {e}", file=sys.stderr)

    print(f"--- Cycle finished. Waiting for 600 seconds (10 minutes)... ---")
    time.sleep(600)


# nohup python3 job_search_main.py > job_search_main.log 2>&1 &
