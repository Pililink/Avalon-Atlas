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
from .widgets import MapListItemWidget

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
        self._preview_label: Optional[QtWidgets.QLabel] = None

        self._debounce_timer = QtCore.QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self.execute_search)

        self.results: List[SearchResult] = []
        self._item_by_slug: dict[str, QtWidgets.QListWidgetItem] = {}
        self._preview_label: Optional[QtWidgets.QLabel] = None

        self._build_ui()
        self._connect_signals()
        self._populate_all_records(initial=True)

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

        self.selected_label = QtWidgets.QLabel("已选 0 条")

        self.selected_list = QtWidgets.QListWidget()
        self.selected_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.selected_list.setMinimumHeight(480)
        self.selected_list.setMouseTracking(True)

        self._popup_list = QtWidgets.QListWidget()
        self._popup_list.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._popup_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._popup_container = QtWidgets.QFrame(self)
        self._popup_container.setWindowFlags(
            QtCore.Qt.WindowType.Popup | QtCore.Qt.WindowType.FramelessWindowHint
        )
        self._popup_container.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup_layout = QtWidgets.QVBoxLayout(self._popup_container)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.addWidget(self._popup_list)
        self._popup_container.hide()

        layout.addLayout(controls)
        layout.addWidget(self.selected_label)
        layout.addWidget(self.selected_list)

        self.setCentralWidget(central)
        self.setMinimumWidth(380)
        self.resize(460, 760)
        self._preview_label = QtWidgets.QLabel(self)
        self._preview_label.setWindowFlags(QtCore.Qt.WindowType.ToolTip)
        self._preview_label.hide()

    def _connect_signals(self) -> None:
        self.search_button.clicked.connect(self.execute_search)
        self.clear_button.clicked.connect(self._handle_clear)
        self.search_input.returnPressed.connect(self.execute_search)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.selected_list.itemDoubleClicked.connect(self._copy_selected_name)
        self._popup_list.itemClicked.connect(self._handle_popup_selection)
        self._popup_list.itemActivated.connect(self._handle_popup_selection)

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
            self._popup_container.hide()
            return

        self.results = self.search_service.search(keyword)
        self._show_popup_results()

    def _show_popup_results(self) -> None:
        self._popup_list.clear()
        if not self.results:
            self._popup_container.hide()
            return

        display_results = self.results[:20]
        for result in display_results:
            text = f"{result.record.name} ({result.record.tier})"
            item = QtWidgets.QListWidgetItem(text)
            thumb = self.resource_loader.map_thumbnail(result.record.slug, size=(64, 36))
            item.setIcon(QtGui.QIcon(thumb))
            item.setToolTip(f"资源 {result.record.resources.rock}/{result.record.resources.wood}/{result.record.resources.ore}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, result)
            self._popup_list.addItem(item)

        row_height = self._popup_list.sizeHintForRow(0) if self._popup_list.count() else 24
        height = min(320, row_height * len(display_results) + 8)
        width = self.search_input.width()
        self._popup_container.resize(width, height)
        global_pos = self.search_input.mapToGlobal(QtCore.QPoint(0, self.search_input.height()))
        self._popup_container.move(global_pos)
        self._popup_container.show()
        self._popup_container.raise_()
        self._popup_list.setCurrentRow(0)
        self.search_input.setFocus()

    def _copy_selected_name(self, item: QtWidgets.QListWidgetItem) -> None:
        result = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(result, SearchResult):
            QtWidgets.QApplication.clipboard().setText(result.record.name)
            self.statusBar().showMessage(f"已复制 {result.record.name}", 2000)

    def _handle_clear(self) -> None:
        self.search_input.clear()
        self._populate_all_records()
        self._hide_preview()
        self._popup_container.setVisible(False)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self.hotkey_service.stop()
            self.ocr_service.close()
        except Exception as exc:
            logger.warning("关闭服务异常: %s", exc)
        self._preview_label.hide()
        return super().closeEvent(event)

    def _handle_popup_selection(self, item: QtWidgets.QListWidgetItem) -> None:
        result = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self._popup_container.hide()
        if isinstance(result, SearchResult):
            self._add_selected_result(result)

    def _populate_all_records(self, initial: bool = False) -> None:
        self.selected_list.clear()
        self._item_by_slug.clear()
        self._all_records = []
        self.selected_label.setText("已选 0 条" if not initial else "已选 0 条")

    def _add_selected_result(self, result: SearchResult) -> None:
        existing_item = self._item_by_slug.get(result.record.slug)
        if existing_item:
            row = self.selected_list.row(existing_item)
            self.selected_list.setCurrentRow(row)
            self.selected_list.scrollToItem(existing_item, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
            return

        item = QtWidgets.QListWidgetItem()
        widget = MapListItemWidget(result.record, self.resource_loader)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, result)
        item.setSizeHint(widget.sizeHint())
        self.selected_list.insertItem(0, item)
        self.selected_list.setItemWidget(item, widget)
        self.selected_list.setCurrentItem(item)
        widget.hovered.connect(self._show_preview)
        widget.unhovered.connect(self._hide_preview)
        self._item_by_slug[result.record.slug] = item
        self.selected_label.setText(f"已选 {self.selected_list.count()} 条")

    def _show_preview(self, record: MapRecord) -> None:
        if not self._preview_label:
            return
        pixmap = self.resource_loader.map_full_image(record.slug)
        scaled = pixmap.scaled(
            360,
            360,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled)
        cursor_pos = QtGui.QCursor.pos()
        self._preview_label.move(cursor_pos + QtCore.QPoint(20, 20))
        self._preview_label.show()

    def _hide_preview(self) -> None:
        if self._preview_label:
            self._preview_label.hide()
