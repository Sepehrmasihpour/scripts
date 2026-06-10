#!/home/sepehr/scripts/venv/bin/python

import time
import logging
from pathlib import Path
import requests

# =========================
# Configuration
# =========================
ACCESS_TOKEN = ""  # Add your token here
DOMAIN = "sepehrtech.org"

# Ensure the URL has no leading spaces!
API_BASE_URL = "https://api.cloudflare.com/client/v4"
IP_SERVICE_URL = "https://ifconfig.ir/"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

SLEEP_SECONDS = 120

# =========================
# Logging setup
# =========================
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "dns_update.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logging.info("Script started.")

# =========================
# Helper functions
# =========================


def get_current_public_ip():
    try:
        response = requests.get(IP_SERVICE_URL, timeout=5)
        if response.status_code != 200:
            logging.error("Failed to get public IP. Status: %s", response.status_code)
            return None
        data = response.json()
        return data.get("ip")
    except Exception as e:
        logging.exception("Error while getting public IP: %s", e)
        return None


def get_cloudflare_zone_id(domain_name):
    try:
        endpoint = f"{API_BASE_URL}/zones"
        response = requests.get(endpoint, headers=HEADERS, timeout=10)
        data = response.json()

        if response.status_code != 200:
            logging.error(
                "Failed to get DNS zones. Status: %s | Response: %s",
                response.status_code,
                response.text,
            )
            return False

        if not data.get("success"):
            logging.error("Cloudflare API error: %s", data.get("errors"))
            return None

        zones = data.get("result", [])
        target_zone = next((z for z in zones if z["name"] == domain_name), None)

        if not target_zone:
            logging.error("Zone %s not found in Cloudflare account.", domain_name)
            return None

        logging.info("Found Zone ID for %s: %s", domain_name, target_zone["id"])
        return target_zone["id"]

    except Exception as e:
        logging.exception("Error getting zone ID: %s", e)
        return None


def get_cloudflare_record_id(zone_id, record_name):
    try:
        endpoint = f"{API_BASE_URL}/zones/{zone_id}/dns_records"
        response = requests.get(endpoint, headers=HEADERS, timeout=10)
        data = response.json()

        if response.status_code != 200:
            logging.error(
                "Failed to update get DNS record ID. Status: %s | Response: %s",
                response.status_code,
                response.text,
            )
            return False

        if not data.get("success"):
            logging.error(
                "Cloudflare API error getting records: %s", data.get("errors")
            )
            return None

        records = data.get("result", [])
        # Find the A record matching our domain
        target_record = next(
            (r for r in records if r["name"] == record_name and r["type"] == "A"), None
        )

        if not target_record:
            logging.error("DNS record %s not found.", record_name)
            return None

        logging.info("Found Record ID for %s: %s", record_name, target_record["id"])
        return target_record["id"]

    except Exception as e:
        logging.exception("Error getting record ID: %s", e)
        return None


def update_dns_record(zone_id, record_id, ip):
    endpoint = f"{API_BASE_URL}/zones/{zone_id}/dns_records/{record_id}"
    data = {
        "type": "A",
        "name": "ssh",
        "content": ip,
        "ttl": 1,
        "proxied": False,
    }

    try:
        # Note: Use 'json=' instead of 'data=' to send JSON format
        response = requests.patch(endpoint, headers=HEADERS, json=data, timeout=10)
        data = response.json()

        if response.status_code != 200:
            logging.error(
                "Failed to update DNS. Status: %s | Response: %s",
                response.status_code,
                response.text,
            )
            return False

        if not data.get("success"):
            logging.error(
                "Cloudflare API error getting records: %s", data.get("errors")
            )
            return False

        resutl = data.get("result")
        logging.info("Successfully updated %s to IP %s. result:%s", DOMAIN, ip, resutl)
        return True

    except Exception as e:
        logging.exception("Error while updating DNS: %s", e)
        return False


# =========================
# Main loop
# =========================
if __name__ == "__main__":
    # Initialize globals
    cached_ip = None
    zone_id = None
    record_id = None

    while True:
        try:
            current_pub_ip = get_current_public_ip()

            if current_pub_ip and current_pub_ip != cached_ip:
                logging.info(
                    "IP change detected. Old: %s | New: %s", cached_ip, current_pub_ip
                )

                # Fetch IDs if not already known
                if not zone_id:
                    zone_id = get_cloudflare_zone_id(DOMAIN)

                if zone_id and not record_id:
                    record_id = get_cloudflare_record_id(zone_id, DOMAIN)

                if zone_id and record_id:
                    if update_dns_record(zone_id, record_id, current_pub_ip):
                        cached_ip = current_pub_ip
                else:
                    logging.error(
                        "Could not obtain Zone/Record IDs. Retrying in next loop."
                    )

            elif current_pub_ip:
                logging.info("IP unchanged (%s).", current_pub_ip)

        except Exception as e:
            logging.exception("Unexpected error in main loop: %s", e)

        time.sleep(SLEEP_SECONDS)
