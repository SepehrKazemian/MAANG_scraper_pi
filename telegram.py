import requests
import os
import sys # Import sys for error handling
import configparser # Import configparser

# --- Configuration Reading ---
CONFIG_FILE = 'config.ini'
config = configparser.ConfigParser()
notifications_enabled_from_config = True # Default to enabled

try:
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        # Use getboolean for robust true/false parsing (handles 1/0, yes/no, true/false, on/off)
        notifications_enabled_from_config = config.getboolean('settings', 'notifications_enabled', fallback=True)
    else:
        print(f"Warning: Config file '{CONFIG_FILE}' not found. Using default settings (notifications enabled).", file=sys.stderr)
except (configparser.Error, ValueError) as e:
    print(f"Warning: Error reading '{CONFIG_FILE}'. Using default settings (notifications enabled). Error: {e}", file=sys.stderr)

NOTIFICATIONS_ENABLED = notifications_enabled_from_config

# --- Credentials (still from environment variables) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Optional: Check if essential credentials are set at module load time
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("Warning: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables not set. Notifications will fail if enabled.", file=sys.stderr)

def send_notification(message):
    if not NOTIFICATIONS_ENABLED:
        # Optional: print a message indicating notifications are off
        # print("Info: Notifications are disabled via config file.", file=sys.stderr)
        return # Skip sending if disabled

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Cannot send Telegram notification due to missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.", file=sys.stderr)
        return # Don't attempt to send if credentials are missing

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"📢 {message}",
        "disable_notification": False # Keep notifications enabled by default on Telegram's side
    }
    try:
        response = requests.post(url, data=payload, timeout=10) # Add timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram notification: {e}", file=sys.stderr)
