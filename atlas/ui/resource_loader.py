from __future__ import annotations

from pathlib import Path
from typing import Dict

from PySide6 import QtCore, QtGui

from ..logger import get_logger

logger = get_logger(__name__)


class ResourceLoader:
    def __init__(self, static_root: Path):
        self.static_root = static_root
        self._map_cache: Dict[str, QtGui.QPixmap] = {}
        self._asset_cache: Dict[str, QtGui.QPixmap] = {}

        # 初始化时输出路径信息，便于调试
        logger.info(f"ResourceLoader 初始化 - static_root: {static_root}")
        logger.info(f"  - static_root 存在: {static_root.exists()}")
        if static_root.exists():
            maps_dir = static_root / "maps"
            logger.info(f"  - maps 目录存在: {maps_dir.exists()}")
            if maps_dir.exists():
                png_count = len(list(maps_dir.glob("*.png")))
                webp_count = len(list(maps_dir.glob("*.webp")))
                logger.info(f"  - 找到 {png_count} 个 PNG 文件, {webp_count} 个 WebP 文件")

    def map_thumbnail(self, slug: str, size: tuple[int, int] = (160, 90)) -> QtGui.QPixmap:
        if slug in self._map_cache:
            return self._map_cache[slug]

        pixmap = self._load_map_image(slug)
        if pixmap.isNull():
            pixmap = QtGui.QPixmap(size[0], size[1])
            pixmap.fill(QtGui.QColor("#2b2b2b"))
        else:
            pixmap = pixmap.scaled(
                size[0],
                size[1],
                QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        self._map_cache[slug] = pixmap
        return pixmap

    def map_full_image(self, slug: str) -> QtGui.QPixmap:
        pixmap = self._load_map_image(slug)
        if pixmap.isNull():
            pixmap = QtGui.QPixmap(600, 400)
            pixmap.fill(QtGui.QColor("#1f1f1f"))
        return pixmap

    def asset_icon(self, name: str) -> QtGui.QPixmap:
        if name in self._asset_cache:
            return self._asset_cache[name]

        for ext in ("webp", "png"):
            path = self.static_root / "assets" / f"{name}.{ext}"
            if path.exists():
                pixmap = QtGui.QPixmap(str(path))
                self._asset_cache[name] = pixmap
                return pixmap

        placeholder = QtGui.QPixmap(32, 32)
        placeholder.fill(QtGui.QColor("#555555"))
        self._asset_cache[name] = placeholder
        return placeholder

    def _load_map_image(self, slug: str) -> QtGui.QPixmap:
        for ext in ("webp", "png"):
            path = self.static_root / "maps" / f"{slug}.{ext}"
            if path.exists():
                pixmap = QtGui.QPixmap(str(path))
                if pixmap.isNull():
                    logger.warning(f"文件存在但加载失败: {path} (可能缺少 Qt 图片插件)")
                else:
                    logger.debug(f"成功加载地图图片: {slug}.{ext}")
                    return pixmap

        logger.warning(f"未找到地图图片: {slug} (搜索路径: {self.static_root / 'maps'})")
        return QtGui.QPixmap()

    def get_asset_path(self, filename: str) -> Path:
        """获取资源文件路径"""
        return self.static_root / "assets" / filename
