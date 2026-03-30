"""
as_apkpure.py — Search and download APKs from APKPure.
"""

import sys
import subprocess
import tempfile
from pathlib import Path
from time import sleep

from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"

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

def category_list() -> list[str]:
    print("[INFO] Fetching all APKPure categories...")
    categories = set()

    for url in ["https://apkpure.com/app", "https://apkpure.com/game"]:
        html = _fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.select("a[href^='/'][data-dt-cate]"):
            href = a.get("href", "").strip()
            span = a.select_one("span")
            if span and href and "/topic/" not in href:
                slug = href.lstrip("/")
                categories.add(slug)

    categories = sorted(categories)
    print(f"[INFO] Found {len(categories)} unique categories.")
    return categories

def category_search(query: str) -> list[dict]:
    print(f"[INFO] Fetching category '{query}'...")

    results = []
    page = 1

    while True:
        html = _fetch(f"https://apkpure.com/{query}?page={page}&sort=new&ajax=1")
        soup = BeautifulSoup(html, "html.parser")

        items = soup.select("div.grid-row")
        if not items:
            print("[INFO] No more results.")
            break

        print(f"\n[INFO] Page {page}: {len(items)} apps")

        for item in items:
            pkg = item.get("data-dt-pkg", "").strip()
            if not pkg:
                continue

            title_el = item.select_one("a.grid-item-title")
            dev_el = item.select_one("p.grid-item-developer")

            name = title_el.get_text(strip=True) if title_el else ""
            dev = dev_el.get_text(strip=True) if dev_el else ""

            results.append({
                "name": name,
                "package": pkg,
                "developer": dev
            })

        # Ask how many more pages
        choice = input("How many more pages? (Enter = stop): ").strip()

        if not choice:
            break

        if not choice.isdigit():
            print("[INFO] Invalid input, stopping.")
            break

        remaining = int(choice)

        for _ in range(remaining):
            page += 1
            sleep(3)

            html = _fetch(f"https://apkpure.com/{query}?page={page}&sort=new&ajax=1")
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select("div.grid-row")
            if not items:
                print("[INFO] No more results.")
                return results

            print(f"[INFO] Page {page}: {len(items)} apps")

            for item in items:
                pkg = item.get("data-dt-pkg", "").strip()
                if not pkg:
                    continue

                title_el = item.select_one("a.grid-item-title")
                dev_el = item.select_one("p.grid-item-developer")

                name = title_el.get_text(strip=True) if title_el else ""
                dev = dev_el.get_text(strip=True) if dev_el else ""

                results.append({
                    "name": name,
                    "package": pkg,
                    "developer": dev
                })

    return results


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

    print("\nWarning: Downloading a large number of apps at once may result in you being blocked despite AppScanner's delays.")
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
    if path.exists():
        while True:
            choice = input(f"[INFO] File {path} already exists. Overwrite (o) or Append (a)? [o/a]: ").strip().lower()
            if choice in {"o", "a"}:
                break
            print("[INFO] Invalid input. Enter 'o' to overwrite or 'a' to append.")

        if choice == "a":
            existing = path.read_text().splitlines()
            packages = existing + packages

    path.write_text("\n".join(packages))
    print(f"[INFO] Saved {len(packages)} package ID(s) to {path}")

def search_and_select(query: str, searchtype: int = 0, list_output: Path = None) -> list[str]:
    if searchtype == 0: results = search(query)
    else: results = category_search(query)

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
