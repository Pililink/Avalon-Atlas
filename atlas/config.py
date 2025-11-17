from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from . import PACKAGE_ROOT


class OCRRegion(BaseModel):
    width: int = Field(410, ge=50, description="OCR 截图区域宽度，单位像素")
    height: int = Field(210, ge=40, description="OCR 截图区域高度，单位像素")
    vertical_offset: int = Field(
        0,
        description="鼠标与截图矩形底部之间的额外间距，正值意味着进一步向上偏移",
    )


class AppConfig(BaseModel):
    maps_data_path: Path = Field(
        default=PACKAGE_ROOT.parent / "static" / "data" / "maps.json",
        description="地图数据路径，支持绝对路径；若缺失则回退到内置资源",
    )
    static_root: Path = Field(default=PACKAGE_ROOT.parent / "static")
    hotkey: str = Field(default="ctrl+alt+m", description="触发 OCR 的热键组合")
    debounce_ms: int = Field(default=200, ge=0)
    ocr_backend: str = Field(default="rapidocr", description="rapidocr 或 tesseract")
    ocr_region: OCRRegion = Field(default_factory=OCRRegion)
    ocr_debug: bool = Field(default=True, description="是否输出 OCR 截图以便调试")
    debug_dir: Path = Field(default=PACKAGE_ROOT.parent / "debug")

    class Config:
        arbitrary_types_allowed = True


def load_config(path: Optional[Path] = None) -> AppConfig:
    """
    从磁盘加载配置（若不存在则使用默认值）
    """
    config_path = path or PACKAGE_ROOT.parent / "config.json"
    if not config_path.exists():
        return AppConfig()

    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        return AppConfig(**data)
    except ValidationError as exc:
        raise RuntimeError(f"配置文件 {config_path} 校验失败: {exc}") from exc
