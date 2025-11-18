from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from . import PACKAGE_ROOT

logger = logging.getLogger(__name__)


class OCRRegion(BaseModel):
    width: int = Field(600, ge=50, description="OCR 截图区域宽度，单位像素")
    height: int = Field(80, ge=40, description="OCR 截图区域高度，单位像素")
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
    ocr_backend: str = Field(
        default="rapidocr",
        description="rapidocr / tesseract / auto（auto 表示 rapidocr 失败时才回退 tesseract）",
    )
    ocr_region: OCRRegion = Field(default_factory=OCRRegion)
    ocr_debug: bool = Field(default=True, description="是否输出 OCR 截图以便调试")
    debug_dir: Path = Field(default=PACKAGE_ROOT.parent / "debug")
    hotkey: str = Field(default="ctrl+alt+m", description="触发 OCR 的热键组合")
    debounce_ms: int = Field(default=200, ge=0)
    config_path: Optional[Path] = Field(default=None, exclude=True, description="当前配置文件路径")

    class Config:
        arbitrary_types_allowed = True


def load_config(path: Optional[Path] = None) -> AppConfig:
    """
    从磁盘加载配置；若文件不存在则生成包含默认热键在内的 config.json。
    """
    config_path = path or PACKAGE_ROOT.parent / "config.json"
    if not config_path.exists():
        config = AppConfig()
        config.config_path = config_path
        _write_config_file(config_path, config)
        logger.info("配置文件不存在，已生成默认配置: %s", config_path)
        return config

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.warning("配置文件 %s 无法解析（%s），已重建默认配置", config_path, exc)
        config = AppConfig()
        config.config_path = config_path
        _write_config_file(config_path, config)
        return config

    try:
        config = AppConfig(**data)
    except ValidationError as exc:
        raise RuntimeError(f"配置文件 {config_path} 校验失败: {exc}") from exc
    config.config_path = config_path
    return config


def save_config(config: AppConfig, path: Optional[Path] = None) -> None:
    target = path or config.config_path or (PACKAGE_ROOT.parent / "config.json")
    config.config_path = target
    _write_config_file(target, config)


def _write_config_file(config_path: Path, config: AppConfig) -> None:
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="json")
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as exc:  # pragma: no cover - 极端场景
        logger.warning("写入配置失败 %s: %s", config_path, exc)
