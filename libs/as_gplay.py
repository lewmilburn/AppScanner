"""
as_gplay.py — Download an APK from Google Play via gplaycli.

Authentication uses a gplaycli.conf file with your Google account credentials.
If no conf file exists, this script will prompt for your email and App Password
and generate one automatically.

WHY App Password?
  Google blocks standard passwords for automated tools.
  App Passwords bypass this — you generate one at:
  https://myaccount.google.com/apppasswords
  (requires 2-Step Verification to be enabled on your account)
"""

import os
import sys
import subprocess
import configparser
from pathlib import Path


GPLAYCLI_CONF = Path(__file__).parent / "gplaycli.conf"


# ---------------------------------------------------------------------------
# Credential persistence (via gplaycli.conf)
# ---------------------------------------------------------------------------

def load_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if GPLAYCLI_CONF.is_file():
        config.read(GPLAYCLI_CONF)
    return config


def save_config(email: str, password: str) -> None:
    config = configparser.ConfigParser()
    config["Credentials"] = {"gmail_address": email, "gmail_password": password, "token": "False"}
    try:
        with open(GPLAYCLI_CONF, "w") as f:
            config.write(f)
    except Exception as e:
        print(f"[WARN] Could not save config: {e}")


def clear_credentials() -> None:
    if GPLAYCLI_CONF.is_file():
        GPLAYCLI_CONF.unlink()
        print("[AUTH] Saved credentials removed.")
    else:
        print("[AUTH] No saved credentials found.")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_credentials() -> tuple[str, str]:
    config = load_config()
    if config.has_section("Credentials"):
        email = config.get("Credentials", "gmail_address", fallback=None)
        password = config.get("Credentials", "gmail_password", fallback=None)
        if email and password:
            print(f"[AUTH] Using saved credentials for {email}.")
            return email, password

    print()
    print("[AUTH] Google account credentials are required to download apps.")
    print("[AUTH] A standard password will NOT work — you need an App Password.")
    print("[AUTH] To create one:")
    print("       1. Enable 2-Step Verification: https://myaccount.google.com/security")
    print("       2. Generate an App Password:   https://myaccount.google.com/apppasswords")
    print("          (select 'Other' as the app name, e.g. 'gplaycli')")
    print()

    email = input("[AUTH] Google email address: ").strip()
    if not email or "@" not in email:
        print("[ERROR] Invalid email address.")
        sys.exit(1)

    password = input("[AUTH] App Password (16-char code, spaces optional): ").strip().replace(" ", "")
    if not password:
        print("[ERROR] App Password cannot be empty.")
        sys.exit(1)

    save_config(email, password)
    print("[AUTH] Credentials saved to gplaycli.conf — they will be used automatically next time.")
    print("[AUTH] To reset them, run: py AppScanner.py -c")

    return email, password


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download(app_id: str, dest_dir: Path = Path("..")) -> None:
    """Download app_id as <app_id>.apk into dest_dir."""
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

    get_credentials()  # ensures gplaycli.conf is populated before calling gplaycli

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    command = ["gplaycli", "-c", str(GPLAYCLI_CONF), "-d", app_id, "-f", str(dest_dir)]
    print(f"[INFO] Running: gplaycli -c gplaycli.conf -d {app_id} -f {dest_dir}")

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print("[ERROR] Download failed.")
        print(result.stderr)
        sys.exit(1)

    expected = dest_dir / f"{app_id}.apk"
    if not expected.is_file():
        apks = list(dest_dir.glob("*.apk"))
        if not apks:
            print("[ERROR] APK file not found after download.")
            sys.exit(1)

    print(f"[SUCCESS] APK downloaded to {dest_dir}/")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download an APK from Google Play")
    parser.add_argument("appID", help="Google Play App ID (e.g. com.example.app)")
    parser.add_argument("-o", "--output-dir", default="apps", help="Directory to save the APK (default: ./apps/)")
    args = parser.parse_args()
    download(args.appID, Path(args.output_dir))