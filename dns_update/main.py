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

url = f"https://api.iranserver.com/domain/{domain}/dns"
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


def update_dns_record(ns_name, ip):
    """
    Updates a DNS nameserver record.
    Returns True if the request succeeded with a 2xx status.
    Returns False otherwise.
    """

    data = {
        "ns": ns_name,
        "ip": ip,
    }

    try:
        response = requests.put(
            url=url,
            headers=headers,
            json=data,
            timeout=10,
        )

        logging.info(
            "DNS update request for %s returned status %s",
            ns_name,
            response.status_code,
        )

        if 200 <= response.status_code < 300:
            logging.info("Successfully updated %s to IP %s", ns_name, ip)
            return True

        logging.error(
            "Failed to update %s. Status: %s | Body: %s",
            ns_name,
            response.status_code,
            response.text,
        )
        return False

    except requests.exceptions.RequestException as e:
        logging.error("Network error while updating %s: %s", ns_name, e)
        return False

    except Exception as e:
        logging.exception("Unexpected error while updating %s: %s", ns_name, e)
        return False


def update_bind_zone(ip):
    """
    Updates the A records in the bind zone file with the new public IP
    and increments the SOA serial.
    """

    try:
        path = Path(BIND_ZONE_FILE)

        if not path.exists():
            logging.error("Bind zone file not found: %s", BIND_ZONE_FILE)
            return False

        content = path.read_text()

        # replace A records
        content = re.sub(r"(ns1\s+IN\s+A\s+)(\S+)", r"\g<1>" + ip, content)

        content = re.sub(r"(@\s+IN\s+A\s+)(\S+)", r"\g<1>" + ip, content)

        content = re.sub(r"(www\s+IN\s+A\s+)(\S+)", r"\g<1>" + ip, content)

        # increment serial
        serial_match = re.search(r"(\d+)\s*;\s*Serial", content)
        if serial_match:
            old_serial = serial_match.group(1)
            new_serial = str(int(old_serial) + 1)
            content = content.replace(old_serial, new_serial, 1)
            logging.info("SOA serial updated: %s -> %s", old_serial, new_serial)
        else:
            logging.warning("Could not find SOA serial to increment")

        path.write_text(content)

        logging.info("Bind zone file updated with new IP %s", ip)

        return True

    except Exception as e:
        logging.exception("Failed to update bind zone: %s", e)
        return False


def restart_bind():
    try:
        subprocess.run(["systemctl", "restart", "bind9"], check=True)
        logging.info("bind9 restarted successfully")
        return True

    except subprocess.CalledProcessError as e:
        logging.error("Failed to restart bind9: %s", e)
        return False


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

                update_dns_record("ns1.sepehrtech.org", current_pub_ip)
                update_dns_record("ns2.sepehrtech.org", current_pub_ip)

                if update_bind_zone(current_pub_ip):
                    restart_bind()

            else:
                logging.info("Public IP has not changed: %s", current_pub_ip)

        except Exception as e:
            logging.exception("Unexpected error in main loop: %s", e)

        time.sleep(sleep_seconds)
