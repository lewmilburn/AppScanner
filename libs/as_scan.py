"""
as_scan.py — Decompile and scan all apps in ./apps/
"""

import os
import platform
import sys
import json
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from libs.as_report import generate_html


APPS_DIR       = Path(__file__).parent / "../apps"
DECOMPILE_DIR  = APPS_DIR / "decompile_temp"

def _get_trufflehog() -> str:
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    arch = arch_map.get(platform.machine().lower())
    if not arch: raise RuntimeError(f"Unsupported architecture: {platform.machine().lower()}")

    ext_map = {"windows": ".exe"}
    if platform.system().lower() not in ("windows", "darwin", "linux"): raise RuntimeError(f"Unsupported OS: {platform.system().lower()}")

    ext = ext_map.get(platform.system().lower(), "")
    return str(Path(__file__).parent / f"trufflehog_{platform.system().lower()}_{arch}{ext}")

def _get_apktool() -> str: return str(Path(__file__).parent / "apktool.jar")

def _on_rm_error(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def cleanup_decompile() -> None:
    if DECOMPILE_DIR.is_dir():
        for attempt in range(3):
            try:
                shutil.rmtree(DECOMPILE_DIR, onerror=_on_rm_error)
                print("[INFO] Deleted apps/decompile_temp/")
                break
            except Exception as e:
                if attempt == 2:
                    print(f"[INFO] Failed to delete apps/decompile_temp/: {e}")

def decompile(apk_path: Path) -> Path | None:
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

def scan(decompile_dir: Path, apk_stem: str) -> dict[str, str | int | list[Any]] | None:
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
        print(f"[INFO] No secrets found in {apk_stem}.")

    return report

def scan_all() -> None:
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

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    reports_dir = (APPS_DIR / "../reports").resolve()
    reports_dir.mkdir(exist_ok=True)
    all_reports = [r["report"] for r in results if "report" in r]
    combined_path = reports_dir / f"report_{timestamp}.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2)
    print(f"[REPORT] JSON report saved to: {combined_path}")

    generate_html(all_reports, reports_dir / f"report_{timestamp}.html")

    print("\n=== Summary ===")
    for r in results:
        if r["status"] == "ok":
            print(f"  {r['apk']}: {r['total_findings']} finding(s)")
        else:
            print(f"  {r['apk']}: {r['status']}")

    cleanup_decompile()