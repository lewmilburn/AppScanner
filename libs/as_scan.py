"""
as_scan.py — Decompile and scan all apps in ./apps/

For each APK found in ./apps/:
  - Decompiles to ./apps/decompile_temp/<apk_stem>/
  - Scans with trufflehog v3
  - Saves report to ./apps/<apk_stem>_report.json

./apps/ itself is never deleted. Only ./apps/decompile_temp/ is cleaned up.
"""

import os
import sys
import json
import shutil
import stat
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from libs.as_report import generate_html


APPS_DIR       = Path(__file__).parent / "../apps"
DECOMPILE_DIR  = APPS_DIR / "decompile_temp"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_trufflehog() -> str:
    if sys.platform == "win32":
        binary = "trufflehog_windows.exe"
    elif sys.platform == "darwin":
        binary = "trufflehog_macos"
    else:
        binary = "trufflehog_linux"
    return str(Path(__file__).parent / binary)


def _get_apktool() -> str:
    return str(Path(__file__).parent / "apktool.jar")


def _on_rm_error(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def cleanup_decompile() -> None:
    """Remove ./apps/decompile_temp/ only — never touches ./apps/ itself."""
    time.sleep(1)
    if DECOMPILE_DIR.is_dir():
        for attempt in range(3):
            try:
                shutil.rmtree(DECOMPILE_DIR, onerror=_on_rm_error)
                print("[CLEANUP] Deleted apps/decompile_temp/")
                break
            except Exception as e:
                if attempt == 2:
                    print(f"[CLEANUP] Failed to delete apps/decompile_temp/: {e}")
                time.sleep(1)


# ---------------------------------------------------------------------------
# Core steps
# ---------------------------------------------------------------------------

def decompile(apk_path: Path) -> Path:
    """
    Decompile a single APK into ./apps/decompile_temp/<apk_stem>/.
    Returns the output directory path.
    """
    out_dir = DECOMPILE_DIR / apk_path.stem
    apktool = _get_apktool()
    command = ["java", "-jar", apktool, "d", str(apk_path), "-o", str(out_dir), "-f"]

    print(f"[INFO] Decompiling {apk_path.name} → apps/decompile_temp/{apk_path.stem}/")
    print(f"[INFO] Running: {' '.join(command)}")

    result = subprocess.run(command)

    if result.returncode != 0:
        print(f"[ERROR] Decompilation failed for {apk_path.name}.")
        return None

    if not out_dir.is_dir():
        print(f"[ERROR] Decompilation folder not created for {apk_path.name}.")
        return None

    print(f"[SUCCESS] Decompiled {apk_path.name}.")
    return out_dir


def scan(decompile_dir: Path, apk_stem: str) -> dict:
    """
    Scan a decompiled directory with trufflehog v3.
    Returns the report dict (combined report written by scan_all).
    """
    trufflehog  = _get_trufflehog()
    command     = [trufflehog, "filesystem", str(decompile_dir), "--json", "--no-update"]

    print(f"[INFO] Scanning {apk_stem} with TruffleHog...")
    print(f"[INFO] Running: {' '.join(command)}")

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode not in (0, 183):
        print(f"[ERROR] TruffleHog scan failed for {apk_stem}.")
        print(result.stderr)
        return None

    findings = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            findings.append({"raw": line})

    report = {
        "apk":            apk_stem,
        "scan_time":      datetime.now(timezone.utc).isoformat(),
        "total_findings": len(findings),
        "findings":       findings,
    }

    if findings:
        print(f"[WARNING] {len(findings)} potential secret(s) found in {apk_stem}.")
    else:
        print(f"[SUCCESS] No secrets found in {apk_stem}.")

    return report


def scan_all() -> None:
    """Decompile and scan every APK in ./apps/."""
    if not APPS_DIR.is_dir():
        print(f"[ERROR] apps directory not found: {APPS_DIR}")
        sys.exit(1)

    apks = sorted(f for ext in ("*.apk", "*.apkm", "*.xapk", "*.apks") for f in APPS_DIR.glob(ext))
    ios = sorted(f for ext in (".ipa", ".app") for f in APPS_DIR.glob(ext))

    if ios:
        print(f"[WARNING] iOS apps found in {APPS_DIR}")
        print(f"[WARNING] AppScanner does not yet support iOS apps.")

    if not apks:
        print(f"[ERROR] No APK files found in {APPS_DIR}")
        sys.exit(1)

    print(f"[INFO] Found {len(apks)} APK(s) to process.\n")
    DECOMPILE_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for i, apk_path in enumerate(apks, 1):
        print(f"--- [{i}/{len(apks)}] {apk_path.name} ---")

        out_dir = decompile(apk_path)
        if out_dir is None:
            print(f"[SKIP] Skipping scan for {apk_path.name} due to decompile failure.\n")
            results.append({"apk": apk_path.stem, "status": "decompile_failed"})
            continue

        report = scan(out_dir, apk_path.stem)
        if report is None:
            results.append({"apk": apk_path.stem, "status": "scan_failed"})
        else:
            results.append({"apk": apk_path.stem, "status": "ok", "total_findings": report["total_findings"], "report": report})

        print()

    # Write combined report
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    reports_dir = (APPS_DIR / "../reports").resolve()
    reports_dir.mkdir(exist_ok=True)
    all_reports = [r["report"] for r in results if "report" in r]
    combined_path = reports_dir / f"report_{timestamp}.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2)
    print(f"[REPORT] JSON report saved to: {combined_path}")

    # Write self-contained HTML report
    generate_html(all_reports, reports_dir / f"report_{timestamp}.html")

    # Summary
    print("\n=== Summary ===")
    for r in results:
        if r["status"] == "ok":
            print(f"  {r['apk']}: {r['total_findings']} finding(s)")
        else:
            print(f"  {r['apk']}: {r['status']}")

    cleanup_decompile()


if __name__ == "__main__":
    scan_all()