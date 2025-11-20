from __future__ import annotations

import html
import threading
from typing import List, Optional

import keyboard
from PySide6 import QtCore, QtGui, QtWidgets

from ..config import AppConfig, save_config
from ..data.models import MapRecord
from ..logger import get_logger
from ..services.hotkey_service import HotkeyService
from ..services.ocr_service import OcrService
from ..services.search_service import MapSearchService, SearchResult
from .resource_loader import ResourceLoader
from .widgets import MapListItemWidget

logger = get_logger(__name__)


class _HighlightDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        highlight_html = index.data(QtCore.Qt.ItemDataRole.UserRole + 1)

        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        painter.save()
        opt.text = ""
        style.drawControl(
            QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget
        )
        if highlight_html:
            text_rect = style.subElementRect(
                QtWidgets.QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget
            )
            painter.translate(text_rect.topLeft())
            doc = QtGui.QTextDocument()
            doc.setDefaultFont(opt.font)
            doc.setDefaultStyleSheet(
                f"body {{ color: {opt.palette.color(QtGui.QPalette.ColorRole.Text).name()}; }}"
            )
            doc.setHtml(f"<body>{highlight_html}</body>")
            clip = QtCore.QRectF(0, 0, text_rect.width(), text_rect.height())
            doc.drawContents(painter, clip)
        painter.restore()


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
        self._preview_pixmap: Optional[QtGui.QPixmap] = None
        self._last_query: str = ""

        self._debounce_timer = QtCore.QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self.execute_search)

        self.results: List[SearchResult] = []
        self._item_by_slug: dict[str, QtWidgets.QListWidgetItem] = {}
        self._hotkey_record_thread: Optional[threading.Thread] = None
        self._hotkey_record_cancel = threading.Event()

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

        # === 搜索区域 ===
        self.search_input = QtWidgets.QLineEdit()
        self._update_search_placeholder()
        self.search_button = QtWidgets.QPushButton("查询")
        self.clear_button = QtWidgets.QPushButton("清除")

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.search_input)
        controls.addWidget(self.search_button)
        controls.addWidget(self.clear_button)

        self.selected_label = QtWidgets.QLabel("已选 0 条")

        # === 结果列表 ===
        self.selected_list = QtWidgets.QListWidget()
        self.selected_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.selected_list.setMinimumHeight(480)
        self.selected_list.setMouseTracking(True)

        # === 弹出搜索列表 ===
        self._popup_list = QtWidgets.QListWidget()
        self._popup_list.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._popup_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self._popup_delegate = _HighlightDelegate(self._popup_list)
        self._popup_list.setItemDelegate(self._popup_delegate)
        self._popup_container = QtWidgets.QFrame(self)
        self._popup_container.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._popup_container.setWindowFlags(
            QtCore.Qt.WindowType.ToolTip | QtCore.Qt.WindowType.FramelessWindowHint
        )
        self._popup_container.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True
        )
        self._popup_container.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        popup_layout = QtWidgets.QVBoxLayout(self._popup_container)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.addWidget(self._popup_list)
        self._popup_container.hide()

        # === 热键配置区域 ===
        self.hotkey_input = QtWidgets.QLineEdit(self.config.hotkey)
        self.hotkey_input.setPlaceholderText("请点击下方按钮录制热键")
        self.hotkey_input.setReadOnly(True)
        self.hotkey_record_button = QtWidgets.QPushButton("录制热键")
        self.hotkey_button = QtWidgets.QPushButton("保存热键")
        self.help_button = QtWidgets.QPushButton("使用说明")

        hotkey_layout = QtWidgets.QHBoxLayout()
        hotkey_layout.addWidget(QtWidgets.QLabel("热键配置："))
        hotkey_layout.addWidget(self.hotkey_input)
        hotkey_layout.addWidget(self.hotkey_record_button)
        hotkey_layout.addWidget(self.hotkey_button)
        hotkey_layout.addWidget(self.help_button)

        # === 组装布局 ===
        layout.addLayout(controls)
        layout.addWidget(self.selected_label)
        layout.addWidget(self.selected_list)
        layout.addLayout(hotkey_layout)

        self.setCentralWidget(central)
        self.setMinimumWidth(480)
        self.resize(480, 760)
        self._preview_label = QtWidgets.QLabel(self)
        self._preview_label.setWindowFlags(
            QtCore.Qt.WindowType.ToolTip
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.NoDropShadowWindowHint
        )
        self._preview_label.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True
        )
        self._preview_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(
            "background-color: #202020; border: 1px solid #555; padding: 6px; border-radius: 4px;"
        )
        self._preview_label.hide()

    def _connect_signals(self) -> None:
        self.hotkey_record_button.clicked.connect(self._start_hotkey_recording)
        self.hotkey_button.clicked.connect(self._handle_hotkey_update)
        self.help_button.clicked.connect(self._show_usage_help)
        self.search_button.clicked.connect(self.execute_search)
        self.clear_button.clicked.connect(self._handle_clear)
        self.search_input.returnPressed.connect(self._handle_return_pressed)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.selected_list.itemDoubleClicked.connect(self._copy_selected_name)
        self._popup_list.itemClicked.connect(self._handle_popup_selection)
        self._popup_list.itemActivated.connect(self._handle_popup_selection)

    def _show_usage_help(self) -> None:
        """显示使用说明对话框"""
        help_text = """
<h2>Avalon Atlas 使用说明</h2>

<h3>📝 手动搜索</h3>
<ol>
<li>在搜索框输入地图名称，支持模糊匹配和部分拼写</li>
<li>点击候选项即可添加到已选列表</li>
<li>悬停候选可预览完整地图，双击可复制名称</li>
</ol>

<h3>⌨️ 热键 OCR</h3>
<ol>
<li>点击"录制热键"，按下目标组合键，再点"保存热键"完成设置</li>
<li>在游戏中，将鼠标移动到地图图标上，等待地图名称显示</li>
<li>地图名称出现后，按下热键即可自动识别并添加到列表</li>
</ol>

<h3>💡 使用技巧</h3>
<ul>
<li>搜索支持容错输入（如 c4s0s 会匹配 casos）</li>
<li>OCR 识别时，鼠标应停在地图名称正下方以获得最佳效果</li>
<li>OCR 失败时可打开调试模式查看截图与识别文本</li>
<li>推荐热键：Ctrl+Shift+Q 或 Ctrl+Alt+M</li>
<li>配置文件储存在程序目录的 config.json，方便备份同步</li>
</ul>

<hr>
<p><b>GitHub 仓库：</b><a href="https://github.com/Pililink/Avalon-Atlas">https://github.com/Pililink/Avalon-Atlas</a></p>
<p><b>问题反馈：</b>欢迎在 GitHub Issues 提交建议或错误报告</p>
        """

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("使用说明")
        msg_box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msg_box.setText(help_text)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg_box.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        msg_box.exec()

    def _handle_hotkey_text(self, text: str) -> None:
        normalized = text.strip()
        if not normalized:
            self.statusBar().showMessage("OCR 未识别到有效文本", 3000)
            return
        self.statusBar().showMessage(f"OCR 识别: {normalized}", 3000)
        self._popup_container.hide()
        self._add_map_from_hotkey(normalized)

    def _handle_hotkey_update(self) -> None:
        combo = self.hotkey_input.text().strip()
        if not combo:
            self.statusBar().showMessage("热键不能为空", 3000)
            self.hotkey_input.setText(self.config.hotkey)
            return
        if combo == self.config.hotkey:
            self.statusBar().showMessage("热键未变化", 2000)
            return
        previous_combo = self.config.hotkey
        try:
            self.hotkey_service.update_hotkey(combo)
        except Exception as exc:
            logger.error("热键注册失败: %s", exc)
            self.statusBar().showMessage(f"热键注册失败: {exc}", 5000)
            try:
                self.hotkey_service.update_hotkey(previous_combo)
            except Exception as rollback_exc:
                logger.error("回滚热键失败: %s", rollback_exc)
            self.hotkey_input.setText(previous_combo)
            return
        self.config.hotkey = combo
        try:
            save_config(self.config)
        except Exception as exc:
            logger.warning("保存热键配置失败: %s", exc)
            self.statusBar().showMessage(f"热键已切换，但写入配置失败: {exc}", 5000)
        else:
            self.statusBar().showMessage(f"热键已更新为 {combo}", 3000)
        self._update_search_placeholder()

    def _start_hotkey_recording(self) -> None:
        if self._hotkey_record_thread and self._hotkey_record_thread.is_alive():
            self.statusBar().showMessage("正在等待热键输入...", 3000)
            return
        self._hotkey_record_cancel.clear()
        self.hotkey_record_button.setEnabled(False)
        self.hotkey_record_button.setText("请按下热键...")
        self.statusBar().showMessage("请按下新的热键组合，录制完成后自动保存", 5000)
        worker = threading.Thread(target=self._record_hotkey_worker, daemon=True)
        self._hotkey_record_thread = worker
        worker.start()

    def _record_hotkey_worker(self) -> None:
        try:
            combo = keyboard.read_hotkey(suppress=False)
        except Exception as exc:
            QtCore.QMetaObject.invokeMethod(
                self,
                "_on_hotkey_record_failed",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, str(exc)),
            )
            return
        if self._hotkey_record_cancel.is_set():
            return
        QtCore.QMetaObject.invokeMethod(
            self,
            "_on_hotkey_recorded",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, combo),
        )

    @QtCore.Slot(str)
    def _on_hotkey_recorded(self, combo: str) -> None:
        self._hotkey_record_thread = None
        self.hotkey_record_button.setEnabled(True)
        self.hotkey_record_button.setText("录制热键")
        normalized = combo.split(",")[0].strip().lower().replace(" ", "")
        if not normalized:
            self.statusBar().showMessage("未捕获到热键，请重试", 4000)
            return
        self.hotkey_input.setText(normalized)
        self._handle_hotkey_update()

    @QtCore.Slot(str)
    def _on_hotkey_record_failed(self, message: str) -> None:
        self._hotkey_record_thread = None
        self.hotkey_record_button.setEnabled(True)
        self.hotkey_record_button.setText("录制热键")
        self.statusBar().showMessage(f"录制热键失败: {message}", 5000)

    def _update_search_placeholder(self) -> None:
        placeholder_hotkey = (
            self.config.hotkey.upper().replace(" ", "")
            if self.config.hotkey
            else "CTRL+ALT+M"
        )
        self.search_input.setPlaceholderText(
            f"输入地图名称或使用热键 {placeholder_hotkey} OCR"
        )

    def _add_map_from_hotkey(self, query: str) -> None:
        results = self.search_service.search(query)
        if not results:
            self.statusBar().showMessage("OCR 未匹配到任何地图", 4000)
            return
        result = results[0]
        self._add_selected_result(result)
        self.statusBar().showMessage(f"已添加 {result.record.name}", 3000)

    def _on_text_changed(self, _: str) -> None:
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
        self._debounce_timer.start(self.config.debounce_ms)

    def _handle_return_pressed(self) -> None:
        self.execute_search()
        if self._popup_list.count():
            first = self._popup_list.item(0)
            if first is not None:
                self._handle_popup_selection(first)

    def execute_search(self) -> None:
        keyword = self.search_input.text()
        self._last_query = keyword
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
            highlighted = self._build_highlighted_text(
                result, result.record.name, result.record.tier
            )
            item = QtWidgets.QListWidgetItem(text)
            thumb = self.resource_loader.map_thumbnail(
                result.record.slug, size=(64, 36)
            )
            item.setIcon(QtGui.QIcon(thumb))
            item.setToolTip(
                f"资源 {result.record.resources.rock}/{result.record.resources.wood}/{result.record.resources.ore}"
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, result)
            item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, highlighted)
            self._popup_list.addItem(item)

        self._update_popup_geometry(len(display_results))
        self._popup_container.show()
        self._popup_container.raise_()
        self.search_input.setFocus()

    def _build_highlighted_text(
        self, result: SearchResult, name: str, tier: str
    ) -> str:
        query = (self._last_query or "").strip()
        text_color = self.palette().color(QtGui.QPalette.ColorRole.Text).name()
        highlight_style = "color: #d33; font-weight: 600;"
        normal_style = f"color: {text_color};"

        def wrap(s: str, style: str) -> str:
            return f'<span style="{style}">{html.escape(s)}</span>'

        if result.positions:
            pos_set = {p for p in result.positions if 0 <= p < len(name)}
            parts = [
                wrap(ch, highlight_style if idx in pos_set else normal_style)
                for idx, ch in enumerate(name)
            ]
            highlighted_name = "".join(parts)
        elif query:
            lower_name = name.lower()
            lower_q = query.lower()
            start = lower_name.find(lower_q)
            if start != -1:
                end = start + len(query)
                highlighted_name = (
                    wrap(name[:start], normal_style)
                    + wrap(name[start:end], highlight_style)
                    + wrap(name[end:], normal_style)
                )
            else:
                highlighted_name = wrap(name, normal_style)
        else:
            highlighted_name = wrap(name, normal_style)

        return f"{highlighted_name} {wrap(f'({tier})', normal_style)}"

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
        self._hotkey_record_cancel.set()
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
            self.selected_list.scrollToItem(
                existing_item, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter
            )
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
        max_width = 520
        max_height = 420
        scaled = pixmap.scaled(
            max_width,
            max_height,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_pixmap = scaled
        self._preview_label.resize(scaled.size())
        self._preview_label.setPixmap(scaled)
        self._reposition_preview()
        self._preview_label.show()

    def _hide_preview(self) -> None:
        if self._preview_label:
            self._preview_label.hide()
            self._preview_pixmap = None

    def _update_popup_geometry(self, display_count: int) -> None:
        if display_count <= 0:
            self._popup_container.hide()
            return

        row_height = (
            self._popup_list.sizeHintForRow(0) if self._popup_list.count() else 24
        )
        height = min(320, row_height * display_count + 8)
        width = self.search_input.width()
        self._popup_container.resize(width, height)
        global_pos = self.search_input.mapToGlobal(
            QtCore.QPoint(0, self.search_input.height())
        )
        self._popup_container.move(global_pos)

    def moveEvent(self, event: QtGui.QMoveEvent) -> None:
        super().moveEvent(event)
        if self._popup_container.isVisible():
            self._update_popup_geometry(self._popup_list.count())
        self._reposition_preview()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._popup_container.isVisible():
            self._update_popup_geometry(self._popup_list.count())
        self._reposition_preview()

    def _reposition_preview(self) -> None:
        if (
            not self._preview_label
            or not self._preview_label.isVisible()
            or self._preview_pixmap is None
        ):
            return

        size = self._preview_pixmap.size()
        available = (
            self.screen() or QtGui.QGuiApplication.primaryScreen()
        ).availableGeometry()
        list_top_left = self.selected_list.mapToGlobal(QtCore.QPoint(0, 0))
        list_top_right = self.selected_list.mapToGlobal(
            QtCore.QPoint(self.selected_list.width(), 0)
        )

        preferred = QtCore.QPoint(list_top_right.x() + 12, list_top_right.y())
        pos = QtCore.QPoint(preferred)

        # If right side overflows, try left side of the list.
        if pos.x() + size.width() > available.right():
            candidate_left = list_top_left.x() - size.width() - 12
            if candidate_left >= available.left():
                pos.setX(candidate_left)
            else:
                pos.setX(
                    max(available.left() + 8, available.right() - size.width() - 8)
                )

        # Clamp vertical position within screen.
        pos.setY(
            max(
                available.top() + 8,
                min(list_top_left.y(), available.bottom() - size.height() - 8),
            )
        )

        self._preview_label.move(pos)
