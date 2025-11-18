from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from atlas.config import load_config
from atlas.data.repository import MapRepository
from atlas.services.ocr_service import OcrService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用 Atlas OCR 服务批量识别 debug 目录中的截图",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="指定调试截图目录，默认读取配置中的 debug_dir",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    debug_dir = (args.dir or config.debug_dir).expanduser()
    if not debug_dir.exists():
        print(f"[WARN] 调试目录不存在: {debug_dir}")
        return 1

    png_files = sorted(debug_dir.glob("*.png"))
    if not png_files:
        print(f"[INFO] 未在 {debug_dir} 找到 PNG 图片")
        return 0

    repository = MapRepository(config.maps_data_path)
    repository.load()
    service = OcrService(config, repository=repository)
    for path in png_files:
        with Image.open(path) as img:
            raw_text, normalized = service.recognize_image(img)
        raw_display = raw_text if raw_text else "<空字符串>"
        normalized_display = normalized if normalized else "<空字符串>"
        print(f"{path.name}")
        print(f"  原始识别: {raw_display}")
        print(f"  规范化结果: {normalized_display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
