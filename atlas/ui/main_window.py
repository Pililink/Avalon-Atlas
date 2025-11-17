from __future__ import annotations

from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ..config import AppConfig
from ..data.models import MapRecord
from ..services.hotkey_service import HotkeyService
from ..services.ocr_service import OcrService
from ..services.search_service import MapSearchService, SearchResult
from ..logger import get_logger
from .resource_loader import ResourceLoader
from .widgets import MapDetailWidget, MapListItemWidget

logger = get_logger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    hotkeyText = QtCore.Signal(str)

    def __init__(
        self,
        config: AppConfig,
        search_service: MapSearchService,
        hotkey_service: HotkeyService,
        ocr_service: OcrService,
        resource_loader: ResourceLoader,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.config = config
        self.search_service = search_service
        self.hotkey_service = hotkey_service
        self.ocr_service = ocr_service
        self.resource_loader = resource_loader

        self._debounce_timer = QtCore.QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self.execute_search)

        self.results: List[SearchResult] = []

        self._build_ui()
        self._connect_signals()

        self.hotkeyText.connect(self._handle_hotkey_text)
        self.hotkey_service.set_callback(self.hotkeyText.emit)
        try:
            self.hotkey_service.start()
        except Exception as exc:
            logger.error("热键注册失败: %s", exc)
            self.statusBar().showMessage(f"热键注册失败: {exc}")

    def _build_ui(self) -> None:
        self.setWindowTitle("Avalon Atlas")
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("输入地图名称或使用热键 Ctrl+Alt+M OCR")
        self.search_button = QtWidgets.QPushButton("查询")
        self.clear_button = QtWidgets.QPushButton("清除")

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.search_input)
        controls.addWidget(self.search_button)
        controls.addWidget(self.clear_button)

        self.result_label = QtWidgets.QLabel("准备就绪")

        self.results_list = QtWidgets.QListWidget()
        self.results_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.detail_widget = MapDetailWidget(self.resource_loader)
        self.detail_widget.setMinimumHeight(280)

        layout.addLayout(controls)
        layout.addWidget(self.result_label)
        layout.addWidget(self.results_list, 3)
        layout.addWidget(self.detail_widget, 2)

        self.setCentralWidget(central)
        self.resize(900, 700)

    def _connect_signals(self) -> None:
        self.search_button.clicked.connect(self.execute_search)
        self.clear_button.clicked.connect(self._handle_clear)
        self.search_input.returnPressed.connect(self.execute_search)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.results_list.currentItemChanged.connect(self._on_selection_changed)
        self.results_list.itemDoubleClicked.connect(self._copy_selected_name)

    def _handle_hotkey_text(self, text: str) -> None:
        self.statusBar().showMessage(f"OCR 识别: {text}", 3000)
        self.search_input.setText(text)
        self.execute_search()

    def _on_text_changed(self, _: str) -> None:
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
        self._debounce_timer.start(self.config.debounce_ms)

    def execute_search(self) -> None:
        keyword = self.search_input.text()
        if not keyword.strip():
            self.results_list.clear()
            self.detail_widget.set_record(None)
            self.result_label.setText("请输入关键字")
            return

        self.results = self.search_service.search(keyword)
        self._render_results()

    def _render_results(self) -> None:
        self.results_list.clear()
        if not self.results:
            self.result_label.setText("未找到匹配地图")
            self.detail_widget.set_record(None)
            return

        for result in self.results:
            item = QtWidgets.QListWidgetItem()
            widget = MapListItemWidget(result.record, self.resource_loader)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, result)
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

        self.result_label.setText(f"匹配 {len(self.results)} 条")
        self.results_list.setCurrentRow(0)

    def _on_selection_changed(self, current: Optional[QtWidgets.QListWidgetItem], previous):
        if current is None:
            self.detail_widget.set_record(None)
            return
        result = current.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(result, SearchResult):
            self.detail_widget.set_record(result.record)

    def _copy_selected_name(self, item: QtWidgets.QListWidgetItem) -> None:
        result = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(result, SearchResult):
            QtWidgets.QApplication.clipboard().setText(result.record.name)
            self.statusBar().showMessage(f"已复制 {result.record.name}", 2000)

    def _handle_clear(self) -> None:
        self.search_input.clear()
        self.results_list.clear()
        self.detail_widget.set_record(None)
        self.result_label.setText("已清除")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self.hotkey_service.stop()
            self.ocr_service.close()
        except Exception as exc:
            logger.warning("关闭服务异常: %s", exc)
        return super().closeEvent(event)
