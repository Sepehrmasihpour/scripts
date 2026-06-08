#!/home/sepehr/scripts/venv/bin/python

import time
import logging
from pathlib import Path
import subprocess
import re

import requests

# =========================
# Configuration
# =========================

BIND_ZONE_FILE = "/etc/bind/db.sepehrtech.org"

access_token = ""
public_ip = None

domain = "sepehrtech.org"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
}

url = " https://api.cloudflare.com/client/v4"
what_is_my_ip_url = "https://ifconfig.ir/"


sleep_seconds = 120


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
    """
    Gets current public IP from the IP service.
    Returns the IP string if successful.
    Returns None if anything goes wrong.
    """

    try:
        response = requests.get(what_is_my_ip_url, timeout=5)

        logging.info("IP check response status: %s", response.status_code)

        if response.status_code != 200:
            logging.error(
                "Failed to get public IP. Status: %s | Body: %s",
                response.status_code,
                response.text,
            )
            return None

        try:
            data = response.json()
        except ValueError:
            logging.error(
                "IP service did not return valid JSON. Body: %s", response.text
            )
            return None

        current_ip = data.get("ip")

        if not current_ip:
            logging.error(
                "JSON response does not contain 'ip'. Response JSON: %s", data
            )
            return None

        return current_ip

    except requests.exceptions.RequestException as e:
        logging.error("Network error while getting public IP: %s", e)
        return None

    except Exception as e:
        logging.exception("Unexpected error while getting public IP: %s", e)
        return None


def get_cloudflare_zone_id(name):
    try:
        endpoint = f"{url}/zones"

        logging.info("Requesting Cloudflare zones")

        response = requests.get(endpoint, headers=headers, timeout=10)

        if response.status_code != 200:
            logging.error(
                "Cloudflare API returned non-200 status: %s | body=%s",
                response.status_code,
                response.text,
            )
            print("Cloudflare request failed:", response.status_code)
            return False

        try:
            data = response.json()
        except ValueError:
            logging.error(
                "Failed to decode JSON from Cloudflare response: %s", response.text
            )
            print("Invalid JSON response from Cloudflare")
            return False

        if not data.get("success"):
            logging.error(
                "Cloudflare API reported failure. errors=%s messages=%s",
                data.get("errors"),
                data.get("messages"),
            )
            print("Cloudflare API returned failure:", data.get("errors"))
            return False

        zones = data.get("result", [])
        target_zone = next((item for item in data if item["name"] == name), None)
        print(target_zone)
        zone_id = target_zone["id"]
        print(zone_id)

        logging.info("Successfully fetched %s zones", len(zones))

        return zones

    except requests.exceptions.RequestException as e:
        logging.exception("Network error while contacting Cloudflare API: %s", e)
        return False

    except Exception as e:
        logging.exception(
            "Unexpected error while getting Cloudflare zones details: %s", e
        )
        return False


def update_dns_record(ip):
    """
    Updates a DNS nameserver record.
    Returns True if the request succeeded with a 2xx status.
    Returns False otherwise.
    """

    data = {
        "type": "A",
        "name": "sepehrtech.org",
        "content": ip,
        "ttl": 1,
        "proxied": False,
    }

    try:
        response = requests.put(
            url=url,
            headers=headers,
            data=data,
            timeout=10,
        )

        logging.info(
            "DNS update request for %s returned status %s",
            response.status_code,
        )

        if 200 <= response.status_code < 300:
            logging.info("Successfully updated %s to IP %s", ip)
            print("URL:", url)
            print("Method: PUT")
            print("Payload:", data)
            print("Status:", response.status_code)
            print("Headers:", response.headers)
            print("Body:", response.text)
            return True
        logging.error(
            "Failed to update %s. Status: %s | Body: %s",
            response.status_code,
            response.text,
        )
        return False

    except requests.exceptions.RequestException as e:
        logging.error("Network error while updating %s: %s", e)
        return False

    except Exception as e:
        logging.exception("Unexpected error while updating %s: %s", e)
        return False


def get_domains():
    response = requests.post("https://api.iranserver.com/domains", headers=headers)
    print(response.text)


# =========================
# Main loop
# =========================
if __name__ == "__main__":
    while True:
        try:
            current_pub_ip = get_current_public_ip()

            if public_ip is None or current_pub_ip != public_ip:
                logging.info(
                    "Public IP changed. Old IP: %s | New IP: %s",
                    public_ip,
                    current_pub_ip,
                )

                public_ip = current_pub_ip
                get_cloudflare_zone_id("sepehrtech.org")

                # update_dns_record("ns1.sepehrtech.org", current_pub_ip)
                # update_dns_record("ns2.sepehrtech.org", current_pub_ip)

            else:
                logging.info("Public IP has not changed: %s", current_pub_ip)

        except Exception as e:
            logging.exception("Unexpected error in main loop: %s", e)

        time.sleep(sleep_seconds)


# dfghjnm,
