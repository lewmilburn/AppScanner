"""
as_apkpure.py — Search and download APKs from APKPure.
"""

import sys
import subprocess
import tempfile
from pathlib import Path
from time import sleep

from bs4 import BeautifulSoup

USER_AGENT = "AppScanner github.com/lewmilburn/AppScanner"

def _fetch(url: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f: tmp = f.name
    result = subprocess.run(
        ["curl", "-s", "-L", "-A", USER_AGENT, url, "-o", tmp],
        capture_output=True
    )
    if result.returncode != 0:
        print(f"[ERROR] Failed to fetch {url}")
        sys.exit(1)
    with open(tmp, "r", encoding="utf-8", errors="ignore") as f: return f.read()


def search(query: str) -> list[dict]:
    print(f"[INFO] Searching APKPure for '{query}'...")
    html = _fetch(f"https://apkpure.com/search?q={query.replace(' ', '+')}")
    soup = BeautifulSoup(html, "html.parser")

    results = []
    for anchor in soup.select("ul#search-res li a.dd"):
        href = anchor.get("href", "")
        pkg = href.rstrip("/").rsplit("/", 1)[-1] if href else ""

        name_el = anchor.select_one("p.p1")
        dev_el = anchor.select_one("p.p2")

        if not name_el or not pkg: continue

        name = name_el.get_text(strip=True)
        dev = dev_el.get_text(strip=True) if dev_el else ""

        results.append({"name": name, "package": pkg, "developer": dev})

    return results


def interactive_select(results: list[dict]) -> list[str]:
    if not results:
        print("[INFO] No results found.")
        return []

    print("\n[SEARCH] Results:")
    for i, app in enumerate(results, 1):
        dev_str = f" — {app['developer']}" if app.get("developer") else ""
        print(f"  {i:2}. {app['name']} ({app['package']}){dev_str}")

    print("\nEnter numbers to download (e.g. 1,3,5 or 1-5 or 'all'), or press Enter to cancel:")
    selection = input("> ").strip().lower()

    if not selection: return []

    indices = set()
    if selection == "all": indices = set(range(len(results)))
    else:
        for part in selection.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                indices.update(range(int(start) - 1, int(end)))
            elif part.isdigit(): indices.add(int(part) - 1)

    return [results[i]["package"] for i in sorted(indices) if 0 <= i < len(results)]

def save_list(packages: list[str], path: Path) -> None:
    path.write_text("\n".join(packages))
    print(f"[INFO] Saved {len(packages)} package ID(s) to {path}")

def search_and_select(query: str, list_output: Path = None) -> list[str]:
    results = search(query)
    packages = interactive_select(results)

    if not packages:
        print("[INFO] No packages selected.")
        return []

    if list_output: save_list(packages, list_output)

    return packages

def download(app_id: str, dest_dir: Path = Path("..")) -> None:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / f"{app_id}.apk"
    url = f"https://d.apkpure.com/b/APK/{app_id}?version=latest"

    print(f"[INFO] Downloading {app_id} from APKPure...")
    result = subprocess.run([
        "curl", "-L",
        "-A", USER_AGENT,
        url, "-o", str(dest)
    ])

    if result.returncode != 0:
        print(f"[ERROR] Download failed for {app_id}.")
        sys.exit(1)

    print(f"[INFO] APK downloaded to {dest}")

    sleep(2)
