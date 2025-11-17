from __future__ import annotations

from pathlib import Path
from typing import Dict

from PySide6 import QtCore, QtGui


class ResourceLoader:
    def __init__(self, static_root: Path):
        self.static_root = static_root
        self._map_cache: Dict[str, QtGui.QPixmap] = {}
        self._asset_cache: Dict[str, QtGui.QPixmap] = {}

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
                return QtGui.QPixmap(str(path))
        return QtGui.QPixmap()
