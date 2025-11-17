"""uv build entry point for PyInstaller-based executable."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import os


def main() -> int:
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    spec_path = project_root / "atlas.spec"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "AvalonAtlas",
        "--onedir",
        "--add-data",
        f"static{os.pathsep}static",
        "main.py",
    ]

    env = dict(**os.environ)
    env.setdefault("PYINSTALLER_CONFIG_DIR", str(build_dir))
    env.setdefault("PYINSTALLER_BOOTLOADER_IGNORE_SIGNALS", "True")

    process = subprocess.run(cmd, cwd=project_root, env=env)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
