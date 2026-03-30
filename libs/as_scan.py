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
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from libs.as_report import generate_html

#
# Consts and Variables
#

APPS_DIR = Path(__file__).parent / "../apps"
DECOMPILE_DIR = APPS_DIR / "decompile_temp"
SCANNED_DIR = APPS_DIR / "scanned"

MAX_WORKERS = os.cpu_count() * 2
COL_APK = 30
COL_STAGE = 14
COL_LOG = 40

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_DIM = "\033[2m"
ANSI_HIDE_CUR = "\033[?25l"
ANSI_SHOW_CUR = "\033[?25h"

def _ansi_up(n): return f"\033[{n}A" if n > 0 else ""
def _ansi_clear_line(): return "\033[2K\r"

def _enable_ansi_windows():
    if platform.system().lower() == "windows":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

#
# States
#

class AppState:
    STAGES = ("download", "decompile", "scan")

    def __init__(self, name: str):
        self.name = name
        self.progress = {s: 0.0  for s in self.STAGES}
        self.done = {s: False for s in self.STAGES}
        self.failed = {s: False for s in self.STAGES}
        self.last_log = ""   # latest log line to show in table
        self.lock = threading.Lock()

    def set_progress(self, stage: str, pct: float):
        with self.lock: self.progress[stage] = max(0.0, min(1.0, pct))

    def set_log(self, line: str):
        with self.lock:
            clean = line.strip()
            if clean.startswith("{"):
                try:
                    obj = json.loads(clean)
                    clean = obj.get("DetectorName") or obj.get("detector_name") or clean
                    clean = f"Finding: {clean}"
                except Exception: clean = "(finding)"
            self.last_log = clean

    def finish(self, stage: str):
        with self.lock:
            self.done[stage] = True
            self.progress[stage] = 1.0

    def fail(self, stage: str):
        with self.lock: self.failed[stage] = True

_states      : dict[str, AppState] = {}
_states_lock = threading.Lock()
_errors      : list[str] = []
_errors_lock = threading.Lock()
_ui_stop = threading.Event()

#
# Helpers
#

def _add_error(msg: str):
    with _errors_lock: _errors.append(msg)


def _get_trufflehog() -> str:
    system = platform.system().lower()
    arch_map = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
    arch = arch_map.get(platform.machine().lower())
    if not arch: raise RuntimeError(f"Unsupported architecture: {platform.machine().lower()}")
    if system not in ("windows", "darwin", "linux"): raise RuntimeError(f"Unsupported OS: {system}")
    return str(Path(__file__).parent / f"trufflehog_{system}_{arch}{'.exe' if system == 'windows' else ''}")

def _get_apktool() -> str:
    return str(Path(__file__).parent / "apktool.jar")

def _on_rm_error(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception: pass

def cleanup_decompile() -> None:
    if DECOMPILE_DIR.is_dir():
        for attempt in range(3):
            try:
                shutil.rmtree(DECOMPILE_DIR, onerror=_on_rm_error)
                break
            except Exception as e:
                if attempt == 2: print(f"[INFO] Failed to delete apps/decompile_temp/: {e}")

def move_to_scanned(apk_path: Path) -> None:
    SCANNED_DIR.mkdir(parents=True, exist_ok=True)
    try: shutil.move(str(apk_path), SCANNED_DIR / apk_path.name)
    except Exception as e: _add_error(f"[WARNING] Could not move {apk_path.name}: {e}")

def delete_apk(apk_path: Path) -> None:
    try: apk_path.unlink()
    except Exception as e: _add_error(f"[WARNING] Could not delete {apk_path.name}: {e}")

#
# Line reader
#

def _stream_to_queue(stream, q: queue.Queue):
    try:
        for line in iter(stream.readline, ""): q.put(line)
    finally:
        stream.close()
        q.put(None)

#
# Progress bar
#

def _bar(pct: float, done: bool, failed: bool, width: int) -> tuple[str, str]:
    inner = width - 1
    if failed:
        filled = max(1, int(inner * pct))
        return ("=" * filled + "!" + " " * max(0, inner - filled))[:width], ANSI_RED
    if done: return ("=" * inner + "|")[:width], ANSI_GREEN
    if pct <= 0: return " " * width, ANSI_DIM
    filled = min(int(inner * pct), inner - 1)
    bar = "=" * filled + ">" + " " * max(0, inner - filled - 1)
    return bar[:width], ANSI_YELLOW

#
# UI
#

_prev_line_count = 0

def _render(states: list[AppState], first: bool):
    global _prev_line_count
    stage_labels = ("Download", "Decompile", "Scan")
    lines = []

    header = (
        f"{ANSI_BOLD}{ANSI_CYAN}"
        f"{'APK':<{COL_APK}} "
        + "  ".join(f"{lbl:^{COL_STAGE}}" for lbl in stage_labels)
        + f"  {'Log':<{COL_LOG}}"
        + ANSI_RESET
    )
    sep_width = COL_APK + 1 + (COL_STAGE + 2) * 3 + 2 + COL_LOG
    sep = ANSI_DIM + "─" * sep_width + ANSI_RESET
    lines.append(header)
    lines.append(sep)

    with _states_lock: snap = list(states)

    for st in snap:
        with st.lock:
            name = st.name
            progress = dict(st.progress)
            done = dict(st.done)
            failed = dict(st.failed)
            last_log = st.last_log

        display = name if len(name) <= COL_APK else name[:COL_APK - 1] + "…"
        row = f"{display:<{COL_APK}} "

        parts = []
        for stage in AppState.STAGES:
            bar_text, colour = _bar(progress[stage], done[stage], failed[stage], COL_STAGE)
            parts.append(f"{colour}{bar_text}{ANSI_RESET}")
        row += "  ".join(parts)

        # log column — truncate and dim
        log_display = last_log[:COL_LOG] if last_log else ""
        # clear the log once everything is done
        if all(done[s] for s in AppState.STAGES): log_display = ""
        row += f"  {ANSI_DIM}{log_display:<{COL_LOG}}{ANSI_RESET}"
        lines.append(row)

    output = ""
    if not first: output += _ansi_up(_prev_line_count)
    for line in lines: output += _ansi_clear_line() + line + "\n"
    _prev_line_count = len(lines)

    sys.stdout.write(output)
    sys.stdout.flush()

def _ui_loop(states: list[AppState]):
    first = True
    while not _ui_stop.is_set():
        _render(states, first)
        first = False
        time.sleep(0.1)
    _render(states, False)
    sys.stdout.write("\n")
    sys.stdout.flush()

#
# Workers
#

def _run_with_log(command: list[str], st: AppState, stage: str,
                  stdout_lines: list[str] | None = None,
                  stderr_lines: list[str] | None = None,
                  pulse_step: float = 0.02,
                  pulse_interval: float = 0.15) -> int:

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_q: queue.Queue[str | None] = queue.Queue()
    stderr_q: queue.Queue[str | None] = queue.Queue()

    threading.Thread(target=_stream_to_queue, args=(proc.stdout, stdout_q), daemon=True).start()
    threading.Thread(target=_stream_to_queue, args=(proc.stderr, stderr_q), daemon=True).start()

    pulse = 0.05
    stdout_done = False
    stderr_done = False

    while not (stdout_done and stderr_done) or proc.poll() is None:
        try:
            while True:
                item = stdout_q.get_nowait()
                if item is None: stdout_done = True
                else:
                    st.set_log(item)
                    if stdout_lines is not None: stdout_lines.append(item)
        except queue.Empty: pass

        try:
            while True:
                item = stderr_q.get_nowait()
                if item is None: stderr_done = True
                else:
                    st.set_log(item)
                    if stderr_lines is not None: stderr_lines.append(item)
        except queue.Empty: pass

        pulse = min(pulse + pulse_step, 0.9)
        st.set_progress(stage, pulse)
        time.sleep(pulse_interval)

    proc.wait()
    return proc.returncode


def _process_apk(apk_path: Path, keep: bool) -> dict:
    st = _states[apk_path.stem]

    # DECOMPILE
    command = ["java", "-jar", _get_apktool(), "d", str(apk_path), "-o", str(DECOMPILE_DIR / apk_path.stem), "-f"]

    rc = _run_with_log(command, st, "decompile", pulse_step=0.02, pulse_interval=0.15)
    out_dir = DECOMPILE_DIR / apk_path.stem

    if rc != 0 or not out_dir.is_dir():
        st.fail("decompile")
        _add_error(f"[ERROR] Decompilation failed: {apk_path.name}")
        return {"apk": apk_path.stem, "status": "decompile_failed"}

    st.finish("decompile")
    st.set_log("")

    # SCAN
    command = [_get_trufflehog(), "filesystem", str(out_dir), "--json", "--no-update"]
    stdout_lines : list[str] = []
    stderr_lines : list[str] = []

    rc = _run_with_log(command, st, "scan", stdout_lines=stdout_lines, stderr_lines=stderr_lines, pulse_step=0.005, pulse_interval=0.1)

    if rc not in (0, 1, 183):
        st.fail("scan")
        reason = " ".join(stderr_lines).strip() or f"exit code {rc}"
        _add_error(f"[ERROR] TruffleHog scan failed: {apk_path.name} — {reason}")
        return {"apk": apk_path.stem, "status": "scan_failed"}

    findings = []
    for line in stdout_lines:
        line = line.strip()
        if not line: continue
        try: findings.append(json.loads(line))
        except json.JSONDecodeError: findings.append({"raw": line})

    st.finish("scan")
    st.set_log("")

    if keep: move_to_scanned(apk_path)
    else: delete_apk(apk_path)

    return {
        "apk":    apk_path.stem,
        "status": "ok",
        "total_findings": len(findings),
        "report": {
            "apk":            apk_path.stem,
            "scan_time":      datetime.now(timezone.utc).isoformat(),
            "total_findings": len(findings),
            "findings":       findings,
        },
    }


#
# Entrypoint
#

def scan_all(keep: bool = False, version: str = "DEV") -> None:
    if not APPS_DIR.is_dir():
        print(f"[ERROR] Apps directory not found: {APPS_DIR}")
        sys.exit(1)

    apks = sorted(f for ext in ("*.apk", "*.apkm", "*.xapk", "*.apks") for f in APPS_DIR.glob(ext))
    ios = sorted(f for ext in (".ipa", ".app") for f in APPS_DIR.glob(ext))

    if ios: print("[WARNING] iOS apps found — iOS is not supported.")

    if not apks:
        print(f"[ERROR] No APK files found in {APPS_DIR}")
        sys.exit(1)

    DECOMPILE_DIR.mkdir(parents=True, exist_ok=True)
    _enable_ansi_windows()
    sys.stdout.write(ANSI_HIDE_CUR)
    sys.stdout.flush()

    with _states_lock:
        for apk in apks:
            st = AppState(apk.stem)
            st.finish("download")
            _states[apk.stem] = st

    state_list = [_states[apk.stem] for apk in apks]
    ui_thread = threading.Thread(target=_ui_loop, args=(state_list,), daemon=True)
    ui_thread.start()

    results = []
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_process_apk, apk, keep): apk for apk in apks}
            for future in as_completed(futures):
                apk = futures[future]
                try: results.append(future.result())
                except Exception as e:
                    _add_error(f"[ERROR] Unexpected error processing {apk.name}: {e}")
                    results.append({"apk": apk.stem, "status": "error"})
    finally:
        _ui_stop.set()
        ui_thread.join(timeout=2)
        sys.stdout.write(ANSI_SHOW_CUR)
        sys.stdout.flush()

    with _errors_lock: errs = list(_errors)
    if errs:
        print()
        for err in errs: print(f"{ANSI_RED}{err}{ANSI_RESET}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    reports_dir = (APPS_DIR / "../reports").resolve()
    reports_dir.mkdir(exist_ok=True)
    all_reports = [r["report"] for r in results if "report" in r]
    combined_path = reports_dir / f"report_{timestamp}.json"
    with open(combined_path, "w", encoding="utf-8") as f: json.dump(all_reports, f, indent=2)

    generate_html(all_reports, reports_dir / f"report_{timestamp}.html", version)

    print(f"\n[REPORT] Saved to: {combined_path}")
    print("\n=== Summary ===")
    for r in sorted(results, key=lambda x: x["apk"]):
        if r["status"] == "ok": print(f"  {r['apk']}: {r['total_findings']} finding(s)")
        else: print(f"  {r['apk']}: {r['status']}")

    cleanup_decompile()
