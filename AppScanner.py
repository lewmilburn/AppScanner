"""
AppScanner.py

For help and usage, see README.md
"""

import sys
import argparse
import urllib.request
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "libs"))

from libs import as_scan as scanner, as_apkpure
from libs import as_install

APPS_DIR = Path(__file__).parent / "apps"
VERSION = "0.2.1"
GITHUB_API = "https://api.github.com/repos/lewmilburn/AppScanner/releases/latest"

def check_for_updates():
    try:
        req = urllib.request.Request(GITHUB_API, headers={"User-Agent": "AppScanner"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            latest = data.get("tag_name", "").lstrip("v")
            current = VERSION.lstrip("v")
            if latest and latest != current:
                url = data.get("html_url", "https://github.com/lewmilburn/AppScanner/releases")
                print(f"[UPDATE] A new version is available: v{latest} (you have v{current})")
                print(f"[UPDATE] Download it at: {url}\n")
    except Exception: pass

def main():
    print(f"[INFO] AppScanner is in BETA, expect bugs and issues.")
    print(f"[INFO] Please report any problems to github.com/lewmilburn/AppScanner")
    check_for_updates()
    print(f"[INFO] ")

    installed_flag = Path(__file__).parent / "libs" / "installed.conf"
    if not installed_flag.exists():
        as_install.install_trufflehog()

    parser = argparse.ArgumentParser(
        description="AppScanner: download, decompile, and scan apps"
    )
    parser.add_argument(
        "--app", "-a",
        type=str,
        default=None,
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
        "--search", "-q",
        type=str,
        default=None,
        help="Search APKPure for apps to download and scan"
    )
    parser.add_argument(
        "--categorySearch", "-cs",
        type=str,
        default=None,
        help="Search APKPure for apps in a specific category"
    )
    parser.add_argument(
        "--categoryList", "-cl",
        action="store_true",
        help="Gets a list of all available APK categories"
    )
    parser.add_argument(
        "--save-list", "-v",
        type=Path,
        default=None,
        help="Save search selection to a list file"
    )
    parser.add_argument(
        "--keep", "-k",
        action="store_true",
        help="Move successfully scanned APKs to ./apps/scanned/ instead of deleting them"
    )
    args = parser.parse_args()

    if args.skip_dl and (args.list or args.search or args.categorySearch or args.categoryList):
        parser.error("--skip-dl cannot be combined with --list or --search")

    if not args.skip_dl and not args.app and not args.list and not args.search and not args.categorySearch and not args.categoryList:
        parser.error("--app, --list, --search, or --categorySearch is required unless using --skip-dl")

    if not args.skip_dl:
        app_ids = []

        # Determine search source
        if args.search:
            app_ids = as_apkpure.search_and_select(args.search, searchtype=0, list_output=args.save_list)
        elif args.categorySearch:
            app_ids = as_apkpure.search_and_select(args.categorySearch, searchtype=1, list_output=args.save_list)
        elif args.categoryList:
            categories = as_apkpure.category_list()
            if not categories:
                print("[INFO] No categories found.")
                sys.exit(0)

            print("\n=== Categories ===")
            for i, cat in enumerate(categories, 1):
                print(f"{i:2}. {cat}")

            choice = input("\nSelect a category number to search apps (or press Enter to cancel): ").strip()
            if not choice:
                sys.exit(0)

            if not choice.isdigit() or not (1 <= int(choice) <= len(categories)):
                print("[ERROR] Invalid selection.")
                sys.exit(1)

            selected_category = categories[int(choice) - 1].lower().replace(" ", "-")
            print(f"[INFO] Selected category: {selected_category}")

            app_ids = as_apkpure.search_and_select(selected_category, searchtype=1, list_output=args.save_list)
        elif args.list:
            if not args.list.is_file():
                print(f"[ERROR] File not found: {args.list}")
                sys.exit(1)
            app_ids = [line.strip() for line in args.list.read_text().splitlines() if line.strip()]
            print(f"[INFO] Loaded {len(app_ids)} App ID(s) from {args.list}")
        elif args.app:
            app_ids = [args.app]

        if not app_ids:
            print("[INFO] No apps selected.")
            sys.exit(0)

        # --- NEW: If --save-list is provided, just save & exit ---
        if args.save_list:
            print(f"[INFO] App IDs saved to {args.save_list}, exiting without downloading.")
            sys.exit(0)

        # --- Normal download & scan ---
        APPS_DIR.mkdir(exist_ok=True)
        print(f"\n=== AppScanner: downloading {len(app_ids)} app(s) ===\n")

        for i, app_id in enumerate(app_ids, 1):
            print(f"--- Download [{i}/{len(app_ids)}]: {app_id} ---")
            as_apkpure.download(app_id, dest_dir=APPS_DIR)
            print()

    else: print("\n=== AppScanner: scan only (skip download) mode ===\n")

    print("--- Decompile & Scan ---\n")
    scanner.scan_all(keep=args.keep, version=VERSION)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
