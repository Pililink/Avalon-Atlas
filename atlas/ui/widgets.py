from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ..data.models import MapRecord
from .resource_loader import ResourceLoader


class MapListItemWidget(QtWidgets.QWidget):
    hovered = QtCore.Signal(MapRecord)
    unhovered = QtCore.Signal()

    def __init__(self, record: MapRecord, loader: ResourceLoader, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.record = record
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 6, 6)
        layout.setSpacing(6)

        self.thumbnail_label = QtWidgets.QLabel()
        self.thumbnail_label.setFixedSize(96, 54)
        self.thumbnail_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        pixmap = loader.map_thumbnail(record.slug, size=(96, 54))
        self.thumbnail_label.setPixmap(pixmap)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        title_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel(f"{record.name} ({record.tier})")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        map_type_label = QtWidgets.QLabel(record.map_type.replace("_", " "))
        map_type_label.setStyleSheet("color: #666; margin-left: 8px;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(map_type_label, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        resource_grid = QtWidgets.QGridLayout()
        resource_grid.setHorizontalSpacing(6)
        resource_grid.setVerticalSpacing(4)
        resource_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        resource_map = [
            ("rock", record.resources.rock),
            ("wood", record.resources.wood),
            ("ore", record.resources.ore),
            ("fiber", record.resources.fiber),
            ("hide", record.resources.hide),
        ]
        resource_idx = 0
        for key, value in resource_map:
            if value <= 0:
                continue
            icon = loader.asset_icon(key)
            lbl = QtWidgets.QLabel()
            lbl.setPixmap(icon.scaled(20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
            lbl.setToolTip(f"{key}: {value}")
            count_label = QtWidgets.QLabel(str(value))
            row = resource_idx // 4
            col = (resource_idx % 4) * 2
            resource_grid.addWidget(lbl, row, col)
            resource_grid.addWidget(count_label, row, col + 1)
            resource_idx += 1

        chest_grid = QtWidgets.QGridLayout()
        chest_grid.setHorizontalSpacing(6)
        chest_grid.setVerticalSpacing(4)
        chest_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
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
        chest_idx = 0
        for icon_name, value in chest_info:
            if value <= 0:
                continue
            icon = loader.asset_icon(icon_name)
            lbl = QtWidgets.QLabel()
            lbl.setPixmap(icon.scaled(20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
            lbl.setToolTip(f"{icon_name}: {value}")
            count_label = QtWidgets.QLabel(str(value))
            row = chest_idx // 4
            col = (chest_idx % 4) * 2
            chest_grid.addWidget(lbl, row, col)
            chest_grid.addWidget(count_label, row, col + 1)
            chest_idx += 1

        text_layout.addLayout(title_row)
        if resource_idx:
            text_layout.addLayout(resource_grid)
        if chest_idx:
            text_layout.addLayout(chest_grid)
        text_layout.addStretch(1)

        layout.addWidget(self.thumbnail_label)
        layout.addSpacing(6)
        layout.addLayout(text_layout)
        layout.addStretch(1)

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self.hovered.emit(self.record)
        return super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.unhovered.emit()
        return super().leaveEvent(event)
