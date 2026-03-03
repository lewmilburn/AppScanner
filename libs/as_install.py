"""
as_install.py — Installs Trufflehog binaries
"""

import tarfile
from pathlib import Path
import shutil
import re

libs_dir = Path(__file__).parent
installed_flag = libs_dir / "installed.conf"

def install_trufflehog():
    if installed_flag.exists(): return

    if input("[INFO] TruffleHog binaries are missing. Install now? (y/n): ").strip().lower() not in ("y", "yes"):
        print("[INFO] Installation canceled.")
        return

    for archive in libs_dir.glob("trufflehog_*.tar.gz"):
        target_name = re.sub(r"_[\d.]+|(\s*\(\d+\))", "", archive.stem[:-4])
        with tarfile.open(archive, "r:gz") as tar:
            binary = next(
                (m for m in tar.getmembers() if Path(m.name).name.lower() in ("trufflehog", "trufflehog.exe")),
                None
            )
            if not binary:
                print(f"[ERROR] No TruffleHog binary found in {archive.name}.")
                continue

            temp_dir = libs_dir / f"temp_{target_name}"
            temp_dir.mkdir(exist_ok=True)

            member_path = (temp_dir / binary.name).resolve()
            if temp_dir.resolve() not in member_path.parents:
                shutil.rmtree(temp_dir)
                raise Exception(f"[ERROR] Unsafe path in {archive.name}: {binary.name}")

            binary_ext = Path(binary.name).suffix
            dest = libs_dir / f"{target_name}{binary_ext}"
            tar.extract(binary, path=temp_dir)
            shutil.move(str(temp_dir / binary.name), dest)
            print(f"[INFO] Installed {dest.name}")
            shutil.rmtree(temp_dir)

        archive.unlink()
        print(f"[INFO] Deleted {archive.name}")

    installed_flag.touch()
    print(f"[INFO] Installation complete. Created {installed_flag}")