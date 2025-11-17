from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ..data.models import MapRecord
from ..services.search_service import SearchResult
from .resource_loader import ResourceLoader


def format_resources(record: MapRecord) -> str:
    res = record.resources
    return f"石:{res.rock} 木:{res.wood} 矿:{res.ore} 棉:{res.fiber} 皮:{res.hide}"


class MapListItemWidget(QtWidgets.QWidget):
    def __init__(self, record: MapRecord, loader: ResourceLoader, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        self.thumbnail_label = QtWidgets.QLabel()
        self.thumbnail_label.setFixedSize(120, 68)
        self.thumbnail_label.setScaledContents(True)
        pixmap = loader.map_thumbnail(record.slug, size=(120, 68))
        self.thumbnail_label.setPixmap(pixmap)

        self.title_label = QtWidgets.QLabel(f"{record.name} ({record.tier})")
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)

        self.info_label = QtWidgets.QLabel(format_resources(record))
        self.info_label.setStyleSheet("color: #888;")

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.info_label)
        text_layout.addStretch(1)

        layout.addWidget(self.thumbnail_label)
        layout.addLayout(text_layout)
        layout.addStretch(1)


class MapDetailWidget(QtWidgets.QWidget):
    def __init__(self, loader: ResourceLoader, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.loader = loader
        self._current: Optional[MapRecord] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.title_label = QtWidgets.QLabel("选择地图以查看详情")
        title_font = self.title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(200)

        self.info_text = QtWidgets.QTextEdit()
        self.info_text.setReadOnly(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.image_label)
        layout.addWidget(self.info_text)

    def set_record(self, record: Optional[MapRecord]) -> None:
        self._current = record
        if record is None:
            self.title_label.setText("选择地图以查看详情")
            self.image_label.clear()
            self.info_text.clear()
            return

        self.title_label.setText(f"{record.name} | {record.tier} | {record.map_type}")
        pixmap = self.loader.map_full_image(record.slug)
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.width(),
            320,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        ))
        info_lines = [
            f"传送门: {record.brecilien}",
            f"箱子: 蓝 {record.chests.blue}, 绿 {record.chests.green}, 金(王座) {record.chests.highGold}/{record.chests.lowGold}",
            f"洞穴: 单人 {record.dungeons.solo}, 蓝洞 {record.dungeons.group}, 金洞 {record.dungeons.avalon}",
            "资源:" + format_resources(record),
        ]
        self.info_text.setPlainText("\n".join(info_lines))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._current:
            pixmap = self.loader.map_full_image(self._current.slug)
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.width(),
                320,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            ))
