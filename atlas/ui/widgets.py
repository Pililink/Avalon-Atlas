from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ..data.models import MapRecord
from .resource_loader import ResourceLoader


def format_resources(record: MapRecord) -> str:
    res = record.resources
    labels = [
        ("石", res.rock),
        ("木", res.wood),
        ("矿", res.ore),
        ("棉", res.fiber),
        ("皮", res.hide),
    ]
    parts = [f"{label}:{value}" for label, value in labels if value > 0]
    return " ".join(parts) if parts else "资源信息暂无"


class MapListItemWidget(QtWidgets.QWidget):
    hovered = QtCore.Signal(MapRecord)
    unhovered = QtCore.Signal()

    def __init__(self, record: MapRecord, loader: ResourceLoader, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.record = record
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        self.thumbnail_label = QtWidgets.QLabel()
        self.thumbnail_label.setFixedSize(120, 68)
        pixmap = loader.map_thumbnail(record.slug, size=(120, 68))
        self.thumbnail_label.setPixmap(pixmap)

        text_layout = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(f"{record.name} ({record.tier})")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        map_type_label = QtWidgets.QLabel(record.map_type.replace("_", " "))
        map_type_label.setStyleSheet("color: #666;")

        info = QtWidgets.QLabel(format_resources(record))
        info.setStyleSheet("color: #888;")

        resource_row = QtWidgets.QHBoxLayout()
        resource_map = [
            ("rock", record.resources.rock),
            ("wood", record.resources.wood),
            ("ore", record.resources.ore),
            ("fiber", record.resources.fiber),
            ("hide", record.resources.hide),
        ]
        resource_added = False
        for key, value in resource_map:
            if value <= 0:
                continue
            icon = loader.asset_icon(key)
            lbl = QtWidgets.QLabel()
            lbl.setPixmap(icon.scaled(20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
            lbl.setToolTip(f"{key}: {value}")
            count_label = QtWidgets.QLabel(str(value))
            resource_row.addWidget(lbl)
            resource_row.addWidget(count_label)
            resource_added = True
        if resource_added:
            resource_row.addStretch(1)

        chest_row = QtWidgets.QHBoxLayout()
        gold_total = record.chests.lowGold + record.chests.highGold
        chest_info = [
            ("blue-chest", record.chests.blue),
            ("green-chest", record.chests.green),
            ("gold-chest", gold_total),
            ("brecilien", record.brecilien),
            ("dg-solo", record.dungeons.solo),
            ("dg-group", record.dungeons.group),
            ("dg-ava", record.dungeons.avalon),
        ]
        chest_added = False
        for icon_name, value in chest_info:
            if value <= 0:
                continue
            icon = loader.asset_icon(icon_name)
            lbl = QtWidgets.QLabel()
            lbl.setPixmap(icon.scaled(20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
            lbl.setToolTip(f"{icon_name}: {value}")
            chest_row.addWidget(lbl)
            chest_row.addWidget(QtWidgets.QLabel(str(value)))
            chest_added = True
        if chest_added:
            chest_row.addStretch(1)

        text_layout.addWidget(title)
        text_layout.addWidget(map_type_label)
        text_layout.addWidget(info)
        if resource_added:
            text_layout.addLayout(resource_row)
        if chest_added:
            text_layout.addLayout(chest_row)
        text_layout.addStretch(1)

        layout.addWidget(self.thumbnail_label)
        layout.addLayout(text_layout)
        layout.addStretch(1)

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self.hovered.emit(self.record)
        return super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.unhovered.emit()
        return super().leaveEvent(event)
