"""
AppScanner.py

For help and usage, see README.md
"""

import sys
import argparse
from pathlib import Path

from libs.as_gplay import clear_credentials
from libs import as_scan as scanner, as_gplay

APPS_DIR = Path(__file__).parent / "apps"


def main():
    parser = argparse.ArgumentParser(
        description="AppScanner: download, decompile, and scan apps"
    )
    parser.add_argument(
        "appID",
        nargs="?",
        help="Google Play App ID (e.g. com.example.app)"
    )
    parser.add_argument(
        "--skip-dl", "-s",
        action="store_true",
        help="Skip download and scan all apps already in ./apps/"
    )
    parser.add_argument(
        "--list", "-l",
        type=Path,
        default=None,
        help="Path to a file containing one App ID per line to download and scan"
    )
    parser.add_argument(
        "--clear-credentials", "-c",
        action="store_true",
        help="Remove saved Google credentials and exit"
    )
    args = parser.parse_args()

    if args.clear_credentials:
        clear_credentials()
        sys.exit(0)

    if args.skip_dl and args.list:
        parser.error("--list and --skip-dl are mutually exclusive")

    if not args.skip_dl and not args.appID and not args.list:
        parser.error("appID or --list is required unless using --skip-dl or --clear-credentials")

    if not args.skip_dl:
        # Collect app IDs to download
        app_ids = []

        if args.list:
            if not args.list.is_file():
                print(f"[ERROR] File not found: {args.list}")
                sys.exit(1)
            app_ids = [line.strip() for line in args.list.read_text().splitlines() if line.strip()]
            print(f"[INFO] Loaded {len(app_ids)} App ID(s) from {args.list}")
        elif args.appID:
            app_ids = [args.appID]

        APPS_DIR.mkdir(exist_ok=True)
        print(f"\n=== AppScanner: downloading {len(app_ids)} app(s) ===\n")

        for i, app_id in enumerate(app_ids, 1):
            print(f"--- Download [{i}/{len(app_ids)}]: {app_id} ---")
            as_gplay.download(app_id, dest_dir=APPS_DIR)
            print()
    else:
        print("\n=== AppScanner: scan only (skip download) mode ===\n")

    print("--- Decompile & Scan ---\n")
    scanner.scan_all()

    print("\n=== Done ===")


if __name__ == "__main__":
    main()