"""设置对话框 - 用于配置热键等选项"""
from __future__ import annotations

import threading
from typing import Optional

import keyboard
from PySide6 import QtCore, QtWidgets

from ..config import AppConfig
from ..logger import get_logger

logger = get_logger(__name__)


class SettingsDialog(QtWidgets.QDialog):
    """设置对话框"""

    def __init__(self, config: AppConfig, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.config = config
        self._recording_key: Optional[str] = None  # 当前正在录制的热键类型
        self._record_thread: Optional[threading.Thread] = None
        self._record_cancel = threading.Event()

        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(500, 300)

        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        """构建UI"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        # === 热键设置组 ===
        hotkey_group = QtWidgets.QGroupBox("热键设置")
        hotkey_layout = QtWidgets.QFormLayout(hotkey_group)
        hotkey_layout.setSpacing(10)

        # OCR 热键
        ocr_hotkey_layout = QtWidgets.QHBoxLayout()
        self.ocr_hotkey_input = QtWidgets.QLineEdit()
        self.ocr_hotkey_input.setReadOnly(True)
        self.ocr_hotkey_input.setPlaceholderText("点击录制按钮设置热键")
        self.ocr_hotkey_button = QtWidgets.QPushButton("录制")
        self.ocr_hotkey_button.setMaximumWidth(80)
        ocr_hotkey_layout.addWidget(self.ocr_hotkey_input)
        ocr_hotkey_layout.addWidget(self.ocr_hotkey_button)

        ocr_help = QtWidgets.QLabel("触发鼠标位置上方的 OCR 识别")
        ocr_help.setStyleSheet("color: gray; font-size: 11px;")

        # 聊天框热键
        chat_hotkey_layout = QtWidgets.QHBoxLayout()
        self.chat_hotkey_input = QtWidgets.QLineEdit()
        self.chat_hotkey_input.setReadOnly(True)
        self.chat_hotkey_input.setPlaceholderText("点击录制按钮设置热键")
        self.chat_hotkey_button = QtWidgets.QPushButton("录制")
        self.chat_hotkey_button.setMaximumWidth(80)
        chat_hotkey_layout.addWidget(self.chat_hotkey_input)
        chat_hotkey_layout.addWidget(self.chat_hotkey_button)

        chat_help = QtWidgets.QLabel("触发区域选择,识别聊天框中的多个地图名")
        chat_help.setStyleSheet("color: gray; font-size: 11px;")

        # 添加到布局
        hotkey_layout.addRow("鼠标 OCR 热键:", ocr_hotkey_layout)
        hotkey_layout.addRow("", ocr_help)
        hotkey_layout.addRow("聊天框 OCR 热键:", chat_hotkey_layout)
        hotkey_layout.addRow("", chat_help)

        layout.addWidget(hotkey_group)

        # === 其他设置 ===
        other_group = QtWidgets.QGroupBox("其他设置")
        other_layout = QtWidgets.QFormLayout(other_group)

        self.debug_checkbox = QtWidgets.QCheckBox("启用 OCR 调试模式")
        self.debug_checkbox.setToolTip("保存 OCR 截图到 debug 目录")

        other_layout.addRow("调试选项:", self.debug_checkbox)
        layout.addWidget(other_group)

        # === 按钮组 ===
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QtWidgets.QPushButton("保存")
        self.save_button.setDefault(True)
        self.cancel_button = QtWidgets.QPushButton("取消")

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # 连接信号
        self.ocr_hotkey_button.clicked.connect(lambda: self._start_recording("ocr"))
        self.chat_hotkey_button.clicked.connect(lambda: self._start_recording("chat"))
        self.save_button.clicked.connect(self._save_settings)
        self.cancel_button.clicked.connect(self.reject)

    def _load_settings(self) -> None:
        """加载当前配置"""
        self.ocr_hotkey_input.setText(self.config.hotkey)
        self.chat_hotkey_input.setText(self.config.chat_hotkey)
        self.debug_checkbox.setChecked(self.config.ocr_debug)

    def _start_recording(self, key_type: str) -> None:
        """开始录制热键"""
        self._recording_key = key_type

        if key_type == "ocr":
            button = self.ocr_hotkey_button
            input_widget = self.ocr_hotkey_input
        else:
            button = self.chat_hotkey_button
            input_widget = self.chat_hotkey_input

        button.setEnabled(False)
        button.setText("录制中...")
        input_widget.setText("请按下组合键...")

        self._record_cancel.clear()
        self._record_thread = threading.Thread(
            target=self._record_hotkey_thread,
            args=(key_type,),
            daemon=True,
        )
        self._record_thread.start()

    def _record_hotkey_thread(self, key_type: str) -> None:
        """录制热键的后台线程"""
        try:
            combo = keyboard.read_hotkey(suppress=False)
            if self._record_cancel.is_set():
                return

            # 标准化热键格式
            combo = self._normalize_hotkey(combo)

            # 更新 UI (在主线程)
            QtCore.QMetaObject.invokeMethod(
                self,
                "_finish_recording",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, key_type),
                QtCore.Q_ARG(str, combo),
            )
        except Exception as exc:
            logger.exception("录制热键失败: %s", exc)
            QtCore.QMetaObject.invokeMethod(
                self,
                "_finish_recording",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, key_type),
                QtCore.Q_ARG(str, ""),
            )

    @QtCore.Slot(str, str)
    def _finish_recording(self, key_type: str, combo: str) -> None:
        """完成热键录制"""
        if key_type == "ocr":
            button = self.ocr_hotkey_button
            input_widget = self.ocr_hotkey_input
        else:
            button = self.chat_hotkey_button
            input_widget = self.chat_hotkey_input

        button.setEnabled(True)
        button.setText("录制")

        if combo:
            input_widget.setText(combo)
        else:
            # 恢复原值
            if key_type == "ocr":
                input_widget.setText(self.config.hotkey)
            else:
                input_widget.setText(self.config.chat_hotkey)

        self._recording_key = None

    def _normalize_hotkey(self, combo: str) -> str:
        """标准化热键格式"""
        # 将 ctrl, alt, shift 统一为小写,排序
        parts = [p.strip().lower() for p in combo.split("+")]

        modifiers = []
        key = None

        for part in parts:
            if part in {"ctrl", "control"}:
                modifiers.append("ctrl")
            elif part == "alt":
                modifiers.append("alt")
            elif part == "shift":
                modifiers.append("shift")
            elif part in {"win", "windows"}:
                modifiers.append("win")
            else:
                key = part

        # 排序修饰键
        modifiers.sort()

        if key:
            return "+".join(modifiers + [key])
        return "+".join(modifiers)

    def _save_settings(self) -> None:
        """保存设置"""
        # 验证热键
        ocr_hotkey = self.ocr_hotkey_input.text().strip()
        chat_hotkey = self.chat_hotkey_input.text().strip()

        if not ocr_hotkey:
            QtWidgets.QMessageBox.warning(self, "警告", "鼠标 OCR 热键不能为空")
            return

        if not chat_hotkey:
            QtWidgets.QMessageBox.warning(self, "警告", "聊天框 OCR 热键不能为空")
            return

        if ocr_hotkey == chat_hotkey:
            QtWidgets.QMessageBox.warning(self, "警告", "两个热键不能相同")
            return

        # 更新配置
        self.config.hotkey = ocr_hotkey
        self.config.chat_hotkey = chat_hotkey
        self.config.ocr_debug = self.debug_checkbox.isChecked()

        self.accept()

    def closeEvent(self, event) -> None:
        """关闭事件"""
        self._record_cancel.set()
        super().closeEvent(event)
