from __future__ import annotations

import sys
from pathlib import Path

# PyInstaller 打包后，资源文件在 _MEIPASS 目录
if hasattr(sys, '_MEIPASS'):
    # PyInstaller 环境：_MEIPASS 指向解压的临时目录
    # 资源文件在 _MEIPASS/static
    PACKAGE_ROOT = Path(sys._MEIPASS)
else:
    # 开发环境：__file__ 在 atlas/ 目录中
    PACKAGE_ROOT = Path(__file__).resolve().parent

__all__ = ["PACKAGE_ROOT"]
