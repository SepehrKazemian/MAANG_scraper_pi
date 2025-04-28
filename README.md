# Raspberry Pi Job Search Notifier

This project is a web scraper designed to run on a Raspberry Pi. It periodically checks job boards of specific companies (Meta, Microsoft, Google, DeepMind) for new postings matching certain criteria and sends notifications via Telegram.

## Features

*   Scrapes job listings from:
    *   Meta Careers
    *   Microsoft Careers
    *   Google Careers
    *   DeepMind Careers (via Greenhouse API)
*   Filters jobs based on keywords and locations (configurable within scripts).
*   Uses Tor and Chromium in headless mode for scraping Meta and Microsoft to handle potential IP blocks and JavaScript rendering.
*   Keeps track of seen jobs to avoid duplicate notifications.
*   Sends notifications for new jobs via Telegram.
*   Designed for continuous running (e.g., using `nohup`).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd JobSearchNotif
    ```

2.  **Install Dependencies:**
    *   **System Packages:** Ensure you have `chromium-browser` and `tor` installed on your Raspberry Pi.
        ```bash
        sudo apt update
        sudo apt install -y chromium-browser tor
        ```
    *   **Python Packages:** Install the required Python libraries. It's recommended to use a virtual environment.
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        ```

3.  **Configure Tor:**
    *   Enable the Tor Control Port by editing the Tor configuration file (`/etc/tor/torrc`):
        ```
        ControlPort 9051
        CookieAuthentication 1
        ```
    *   Add your user (e.g., `pi`) to the `debian-tor` group to allow access to the control port:
        ```bash
        sudo usermod -a -G debian-tor $(whoami)
        ```
    *   Restart the Tor service:
        ```bash
        sudo systemctl restart tor
        ```
    *   You might need to reboot or log out/in for the group changes to take effect.

4.  **Configure Credentials and Settings:**
    *   **Telegram Credentials (Environment Variables):**
        *   Create a Telegram bot using BotFather and get your `BOT_TOKEN`.
        *   Find your `CHAT_ID`. You can send a message to your bot and then visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` to find it.
        *   Set the following environment variables before running the script:
            *   `TELEGRAM_TOKEN`: Your Telegram Bot Token (Required).
            *   `TELEGRAM_CHAT_ID`: The chat ID where notifications should be sent (Required).
        *   Example:
            ```bash
            export TELEGRAM_TOKEN="YOUR_BOT_TOKEN"
            export TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
            ```
        *   The script will print a warning and fail to send notifications if these are not set.
    *   **Notification Setting (Config File):**
        *   A `config.ini` file is used to control whether notifications are sent.
        *   Edit `JobSearchNotif/config.ini`:
            ```ini
            [settings]
            # Set to false or 0 to disable Telegram notifications
            notifications_enabled = true
            ```
        *   Set `notifications_enabled` to `false` (or `0`, `no`, `off`) to disable notifications. Any other value (or if the file/setting is missing) enables notifications.

5.  **Run the Scraper:**
    *   You can run the main script directly:
        ```bash
        python job_search_main.py
        ```
    *   For continuous background operation, use `nohup`:
        ```bash
        nohup python job_search_main.py > job_search_main.log 2>&1 &
        ```

## Dependencies

*   Python 3.x
*   `chromium-browser`
*   `tor`
*   Python libraries: See `requirements.txt`
    *   `requests`
    *   `stem`
    *   `beautifulsoup4`
    *   `pychrome`

## Notes

*   The scraper relies on the specific HTML structure and API endpoints of the target websites. Changes to these sites may break the scraper.
*   Scraping frequency is set within the scripts (e.g., `job_search_main.py`, `google.py`). Adjust `time.sleep()` values as needed, but be respectful of the target websites' resources.
*   Error handling in the main loop (`job_search_main.py`) has been improved: an error in one scraper (e.g., Meta) should no longer stop the others (e.g., Google, Microsoft, DeepMind) from running in the same cycle. Errors during browser restarts are also caught individually.
*   The `api_call.py` file is currently empty.
*   The `test.py` file provides a basic test for the DeepMind API endpoint.
