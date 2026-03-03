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
VERSION = "1.0.0"
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
    check_for_updates()

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
        "--save-list",
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

    if args.skip_dl and (args.list or args.search):
        parser.error("--skip-dl cannot be combined with --list or --search")

    if not args.skip_dl and not args.app and not args.list and not args.search:
        parser.error("--app, --list, or --search is required unless using --skip-dl")

    if not args.skip_dl:
        app_ids = []

        if args.search:
            app_ids = as_apkpure.search_and_select(args.search, list_output=args.save_list)
            if not app_ids: sys.exit(0)
        elif args.list:
            if not args.list.is_file():
                print(f"[ERROR] File not found: {args.list}")
                sys.exit(1)
            app_ids = [line.strip() for line in args.list.read_text().splitlines() if line.strip()]
            print(f"[INFO] Loaded {len(app_ids)} App ID(s) from {args.list}")
        elif args.app:
            app_ids = [args.app]

        APPS_DIR.mkdir(exist_ok=True)
        print(f"\n=== AppScanner: downloading {len(app_ids)} app(s) ===\n")

        for i, app_id in enumerate(app_ids, 1):
            print(f"--- Download [{i}/{len(app_ids)}]: {app_id} ---")
            as_apkpure.download(app_id, dest_dir=APPS_DIR)
            print()
    else: print("\n=== AppScanner: scan only (skip download) mode ===\n")

    print("--- Decompile & Scan ---\n")
    scanner.scan_all(keep=args.keep)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
