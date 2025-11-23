from __future__ import annotations

import html
import sys
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
from ..services.update_checker import UpdateChecker, UpdateInfo
from .region_selector import RegionSelector
from .resource_loader import ResourceLoader
from .settings_dialog import SettingsDialog
from .widgets import MapListItemWidget

logger = get_logger(__name__)

# Windows API 用于置顶窗口
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    # Windows 常量
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

    # 加载 user32.dll
    user32 = ctypes.windll.user32
    SetWindowPos = user32.SetWindowPos
    SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    SetWindowPos.restype = wintypes.BOOL


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
    chatRegionTrigger = QtCore.Signal()  # 聊天框区域选择触发信号

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
        self._region_selector: Optional[RegionSelector] = None
        self._update_checker = UpdateChecker()

        self._build_ui()
        self._connect_signals()
        self._populate_all_records(initial=True)

        self.hotkeyText.connect(self._handle_hotkey_text, QtCore.Qt.ConnectionType.QueuedConnection)
        self.chatRegionTrigger.connect(self._show_region_selector, QtCore.Qt.ConnectionType.QueuedConnection)
        self.hotkey_service.set_callback(self.hotkeyText.emit)
        try:
            self.hotkey_service.start()
            # 注册聊天框热键
            self.hotkey_service.register_hotkey(
                "chat",
                self.config.chat_hotkey,
                lambda _: self.chatRegionTrigger.emit()
            )
        except Exception as exc:
            logger.error("热键注册失败: %s", exc)
            self.statusBar().showMessage(f"热键注册失败: {exc}")

        # 应用置顶配置 (延迟到窗口显示后)
        if self.config.always_on_top:
            self.pin_button.blockSignals(True)
            self.pin_button.setChecked(True)
            self.pin_button.setText("📌 已置顶")
            self.pin_button.blockSignals(False)
            # 延迟应用置顶，等待窗口完全初始化
            QtCore.QTimer.singleShot(100, self._apply_initial_always_on_top)

        # 延迟检查更新（启动后 2 秒）
        QtCore.QTimer.singleShot(2000, self._check_for_updates)

    def _apply_initial_always_on_top(self) -> None:
        """初始化时应用置顶设置"""
        if sys.platform == "win32":
            hwnd = int(self.winId())
            result = SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
            )
            if result:
                logger.info("从配置加载窗口置顶状态: 已启用 (Windows API)")
            else:
                logger.warning("初始化置顶失败，恢复配置")
                self.config.always_on_top = False
                self.pin_button.setChecked(False)
                self.pin_button.setText("📌 置顶")
        else:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)
            self.show()
            logger.info("从配置加载窗口置顶状态: 已启用")

    def _check_for_updates(self) -> None:
        """检查更新"""
        logger.info("开始检查更新")
        self._update_checker.check_update_async(self._handle_update_result)

    @QtCore.Slot(object)
    def _handle_update_result(self, update_info: Optional[UpdateInfo]) -> None:
        """处理更新检查结果"""
        if update_info is None:
            logger.info("更新检查完成: 无法获取更新信息")
            return

        if not update_info.has_update:
            logger.info("更新检查完成: 当前已是最新版本")
            return

        # 有新版本可用
        logger.info("发现新版本: %s", update_info.latest_version)

        # 在主线程显示更新提示
        QtCore.QMetaObject.invokeMethod(
            self,
            "_show_update_dialog",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(object, update_info),
        )

    @QtCore.Slot(object)
    def _show_update_dialog(self, update_info: UpdateInfo) -> None:
        """显示更新对话框"""
        # 构建更新消息
        message = f"""
<h3>发现新版本 v{update_info.latest_version}</h3>
<p>当前版本: v{update_info.current_version}</p>

<h4>更新说明:</h4>
<p style="white-space: pre-wrap;">{self._format_release_notes(update_info.release_notes)}</p>

<p><b>下载地址:</b><br>
<a href="{update_info.download_url}">{update_info.download_url}</a></p>

<p><b>查看详情:</b><br>
<a href="{update_info.release_url}">{update_info.release_url}</a></p>
"""

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("更新提示")
        msg_box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msg_box.setText(message)
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msg_box.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Ignore
        )
        msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
        msg_box.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )

        # 修改按钮文本
        ok_button = msg_box.button(QtWidgets.QMessageBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("前往下载")

        ignore_button = msg_box.button(QtWidgets.QMessageBox.StandardButton.Ignore)
        if ignore_button:
            ignore_button.setText("稍后提醒")

        result = msg_box.exec()

        # 如果点击"前往下载"，打开下载链接
        if result == QtWidgets.QMessageBox.StandardButton.Ok:
            import webbrowser
            webbrowser.open(update_info.download_url)

    def _format_release_notes(self, notes: str) -> str:
        """格式化发布说明"""
        if not notes:
            return "暂无更新说明"

        # 简单的 Markdown 转 HTML（基础支持）
        lines = notes.split('\n')
        formatted_lines = []

        for line in lines[:10]:  # 最多显示 10 行
            # 转义 HTML 特殊字符
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            # 标题
            if line.startswith('# '):
                line = f'<b>{line[2:]}</b>'
            elif line.startswith('## '):
                line = f'<b>{line[3:]}</b>'
            elif line.startswith('### '):
                line = f'<b>{line[4:]}</b>'
            # 列表
            elif line.strip().startswith('- '):
                line = '  • ' + line.strip()[2:]
            elif line.strip().startswith('* '):
                line = '  • ' + line.strip()[2:]

            formatted_lines.append(line)

        result = '\n'.join(formatted_lines)
        if len(lines) > 10:
            result += '\n...'

        return result

    def _build_ui(self) -> None:
        self.setWindowTitle("Avalon Atlas")

        # 设置窗口图标
        icon_path = self.resource_loader.get_asset_path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

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

        # 添加一个状态消息标签，用于显示临时消息（替代状态栏）
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self.status_label.setText(""))

        # === 结果列表 ===
        self.selected_list = QtWidgets.QListWidget()
        self.selected_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.selected_list.setMinimumHeight(480)
        self.selected_list.setMouseTracking(True)
        # 启用右键菜单
        self.selected_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.selected_list.customContextMenuRequested.connect(self._show_context_menu)

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

        # === 底部区域 ===
        self.settings_button = QtWidgets.QPushButton("设置")
        self.help_button = QtWidgets.QPushButton("使用说明")
        self.pin_button = QtWidgets.QPushButton("📌 置顶")
        self.pin_button.setCheckable(True)  # 可切换状态
        self.pin_button.setToolTip("保持窗口始终在最前")

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.selected_label)  # 已选标签放在左侧
        button_layout.addWidget(self.status_label)    # 状态消息标签紧跟在已选标签后
        button_layout.addStretch()
        button_layout.addWidget(self.pin_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addWidget(self.help_button)

        # === 组装布局 ===
        layout.addLayout(controls)
        layout.addWidget(self.selected_list)
        layout.addLayout(button_layout)

        self.setCentralWidget(central)
        self.setMinimumWidth(480)
        self.resize(480, 760)

        # 隐藏状态栏，使用自定义的 status_label 代替
        self.setStatusBar(None)

        self._preview_label = QtWidgets.QLabel(self)
        self._preview_label.setWindowFlags(
            QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.NoDropShadowWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self._preview_label.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True
        )
        self._preview_label.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_AlwaysStackOnTop, True
        )
        self._preview_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(
            "background-color: #202020; border: 1px solid #555; padding: 6px; border-radius: 4px;"
        )
        self._preview_label.hide()

    @QtCore.Slot(str, int)
    def _show_status_message(self, message: str, duration: int = 2000) -> None:
        """在底部按钮区域显示状态消息"""
        self.status_label.setText(message)
        if self._status_timer.isActive():
            self._status_timer.stop()
        self._status_timer.start(duration)

    def _connect_signals(self) -> None:
        self.settings_button.clicked.connect(self._show_settings)
        self.help_button.clicked.connect(self._show_usage_help)
        self.pin_button.toggled.connect(self._toggle_always_on_top)
        self.search_button.clicked.connect(self.execute_search)
        self.clear_button.clicked.connect(self._handle_clear)
        self.search_input.returnPressed.connect(self._handle_return_pressed)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.selected_list.itemDoubleClicked.connect(self._copy_selected_name)
        self._popup_list.itemClicked.connect(self._handle_popup_selection)
        self._popup_list.itemActivated.connect(self._handle_popup_selection)

    def _show_settings(self) -> None:
        """显示设置对话框"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # 保存配置到文件
            save_config(self.config)

            # 更新热键注册
            try:
                self.hotkey_service.register_hotkey(
                    "ocr",
                    self.config.hotkey,
                    self.hotkeyText.emit
                )
                self.hotkey_service.register_hotkey(
                    "chat",
                    self.config.chat_hotkey,
                    lambda _: self.chatRegionTrigger.emit()
                )
                self._show_status_message("设置已保存并生效", 2000)
            except Exception as exc:
                logger.error("更新热键失败: %s", exc)
                self._show_status_message(f"热键更新失败: {exc}", 3000)

    def _toggle_always_on_top(self, checked: bool) -> None:
        """切换窗口置顶状态"""
        if sys.platform == "win32":
            # 使用 Windows API 直接设置窗口置顶，避免 setWindowFlags 导致的问题
            hwnd = int(self.winId())
            if checked:
                # 设置为置顶窗口
                result = SetWindowPos(
                    hwnd,
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
                if result:
                    self.pin_button.setText("📌 已置顶")
                    self._show_status_message("窗口已置顶", 2000)
                    logger.info("窗口置顶已启用 (Windows API)")
                else:
                    logger.warning("Windows API 设置置顶失败")
                    self.pin_button.setChecked(False)
                    return
            else:
                # 取消置顶
                result = SetWindowPos(
                    hwnd,
                    HWND_NOTOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
                if result:
                    self.pin_button.setText("📌 置顶")
                    self._show_status_message("已取消置顶", 2000)
                    logger.info("窗口置顶已禁用 (Windows API)")
                else:
                    logger.warning("Windows API 取消置顶失败")
                    self.pin_button.setChecked(True)
                    return
        else:
            # 非 Windows 系统使用 Qt 方式 (可能有问题)
            if checked:
                self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)
                self.pin_button.setText("📌 已置顶")
                logger.info("窗口置顶已启用")
            else:
                self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowStaysOnTopHint)
                self.pin_button.setText("📌 置顶")
                logger.info("窗口置顶已禁用")

            self.showNormal()
            self.activateWindow()
            self.raise_()

        # 保存配置
        self.config.always_on_top = checked
        save_config(self.config)

    def _restore_window_state(self, pos: QtCore.QPoint, size: QtCore.QSize) -> None:
        """恢复窗口位置和大小"""
        self.resize(size)
        self.move(pos)

    def _activate_window(self) -> None:
        """激活窗口并确保获得焦点"""
        self.raise_()
        self.activateWindow()
        # Windows 特定：强制设置前台窗口
        if hasattr(self, 'winId'):
            self.setFocus()

    def _show_usage_help(self) -> None:
        """显示使用说明对话框"""
        help_text = """
<h2>Avalon Atlas 使用说明</h2>

<h3>📝 手动搜索</h3>
<ul>
<li><b>模糊匹配</b>：输入地图名称的一部分即可搜索（如输入 "hirexo" 匹配 "Hiros-Exelos"）</li>
<li><b>字符相似性</b>：自动处理易混淆字符（i/l/1/|, o/0, s/5, z/2），提升匹配准确率</li>
<li><b>缩写查询</b>：支持缩写搜索，自动拆分匹配
  <ul>
    <li>两段地图名：如输入 "souuzu" 匹配 "Soues-Uzurtum"</li>
    <li>三段地图名：如输入 "qiiinvie" 匹配 "Qiient-In-Viesis"</li>
  </ul>
</li>
<li><b>查看详情</b>：点击候选项添加到列表，悬停预览完整地图，双击复制详细信息</li>
</ul>

<h3>⌨️ 双热键 OCR 识别</h3>

<h4>1️⃣ 鼠标 OCR（推荐热键：Ctrl+Shift+Q）</h4>
<ul>
<li>将鼠标移动到传送门图标处游戏内弹出地图名后，按下热键自动识别</li>
<li>支持图像预处理（灰度化、对比度增强、锐化），提升识别率</li>
</ul>

<h4>2️⃣ 聊天框 OCR（推荐热键：Ctrl+Shift+W）</h4>
<ul>
<li>按下热键后，拖动鼠标框选聊天框区域</li>
<li>自动识别区域内所有地图名</li>
<li>支持标准地图名和缩写格式（前3字符）</li>
<li>可同时识别多个地图名（如聊天框显示多个地图时）</li>
</ul>

<h3>💡 高级技巧</h3>
<ul>
<li><b>自动更新</b>：程序启动时自动检查 GitHub 新版本，发现更新后提示下载</li>
<li><b>调试模式</b>：在设置中开启"OCR调试"，查看识别截图和原始文本（保存在 debug/ 文件夹）</li>
<li><b>查看日志</b>：状态栏会显示OCR识别的原始文本和匹配结果，详细日志保存在 debug/avalon_atlas.log</li>
<li><b>缩写查询</b>：OCR 识别到的缩写文本也能自动匹配完整地图名</li>
<li><b>批量添加</b>：使用聊天框 OCR 可一次添加多个地图</li>
<li><b>配置备份</b>：配置文件储存在程序目录的 config.json，方便备份同步</li>
</ul>

<h3>🔧 设置说明</h3>
<ul>
<li><b>鼠标 OCR 热键</b>：用于识别鼠标位置的地图名</li>
<li><b>聊天框 OCR 热键</b>：用于框选区域批量识别</li>
<li><b>OCR 引擎</b>：可选择 RapidOCR（默认）或 Tesseract</li>
<li><b>OCR 调试</b>：开启后会保存截图和识别文本到 debug/ 文件夹</li>
</ul>

<hr>
<p><b>GitHub 仓库：</b> <a href="https://github.com/Pililink/Avalon-Atlas">https://github.com/Pililink/Avalon-Atlas</a></p>
<p><b>问题反馈：</b> 欢迎在 GitHub Issues 提交建议或错误报告</p>
<p style="color: #888; font-size: 10px;">提示：双击此对话框中的链接可以复制</p>
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
            self._show_status_message("OCR 未识别到有效文本", 3000)
            return

        # 显示OCR识别的文本
        self._show_status_message(f"OCR 识别: {normalized}", 5000)
        logger.info("鼠标 OCR 识别: %s", normalized)

        self._popup_container.hide()
        self._add_map_from_hotkey(normalized)

    def _update_search_placeholder(self) -> None:
        placeholder_hotkey = (
            self.config.hotkey.upper().replace(" ", "")
            if self.config.hotkey
            else "CTRL+ALT+q"
        )
        self.search_input.setPlaceholderText(
            f"输入地图名称或使用热键识别"
        )

    def _add_map_from_hotkey(self, query: str) -> None:
        results = self.search_service.search(query)
        if not results:
            self._show_status_message("OCR 未匹配到任何地图", 4000)
            return
        result = results[0]
        self._add_selected_result(result)
        self._show_status_message(f"已添加 {result.record.name}", 3000)

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
            # 格式化地图详细信息
            record = result.record
            formatted_text = self._format_map_details(record)
            QtWidgets.QApplication.clipboard().setText(formatted_text)
            self._show_status_message(f"已复制 {record.name} 详细信息", 2000)

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        """显示右键上下文菜单"""
        item = self.selected_list.itemAt(pos)
        if not item:
            return

        menu = QtWidgets.QMenu(self)

        # 复制操作
        copy_action = menu.addAction("复制详细信息")
        copy_action.triggered.connect(lambda: self._copy_selected_name(item))

        # 删除操作
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self._delete_selected_item(item))

        # 在鼠标位置显示菜单
        menu.exec(self.selected_list.mapToGlobal(pos))

    def _delete_selected_item(self, item: QtWidgets.QListWidgetItem) -> None:
        """删除选中的列表项"""
        result = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(result, SearchResult):
            slug = result.record.slug
            # 从字典中移除
            if slug in self._item_by_slug:
                del self._item_by_slug[slug]

            # 从列表中移除
            row = self.selected_list.row(item)
            self.selected_list.takeItem(row)

            # 更新计数
            self.selected_label.setText(f"已选 {self.selected_list.count()} 条")
            self._show_status_message(f"已删除 {result.record.name}", 2000)

    def _format_map_details(self, record) -> str:
        """格式化地图详细信息为可读文本"""
        # 地图类型中文映射（根据 model.py 注释）
        map_type_names = {
            "TUNNEL_ROYAL": "通向外界-皇家大陆(蓝/黄区)",
            "TUNNEL_ROYAL_RED": "通向外界-皇家大陆(红区)",
            "TUNNEL_BLACK_LOW": "通向外界-黑区外圈",
            "TUNNEL_BLACK_MEDIUM": "通向外界-黑区中圈",
            "TUNNEL_BLACK_HIGH": "通向外界-黑区内圈",
            "TUNNEL_DEEP": "阿瓦隆通道-深层",
            "TUNNEL_LOW": "阿瓦隆通道-外层",
            "TUNNEL_MEDIUM": "阿瓦隆通道-中层",
            "TUNNEL_HIGH": "阿瓦隆通道-内层",
            "TUNNEL_DEEP_RAID": "金门",
            "TUNNEL_HIDEOUT": "地堡-普通",
            "TUNNEL_HIDEOUT_DEEP": "地堡-深层",
        }

        # 提取等级数字
        tier_number = record.tier.replace("T", "")

        # 地图类型
        map_type_cn = map_type_names.get(record.map_type, record.map_type)

        # 格式化输出
        lines = [
            f"地图名: {record.name}",
            f"级别: {tier_number}",
            f"类型: {map_type_cn}",
            "",
            "资源数量:",
        ]

        # 洞穴信息（按注释：金洞、蓝洞、绿洞）
        dungeon_parts = []
        if record.dungeons.avalon > 0:
            dungeon_parts.append(f"金洞: {record.dungeons.avalon}")
        if record.dungeons.group > 0:
            dungeon_parts.append(f"蓝洞: {record.dungeons.group}")
        if record.dungeons.solo > 0:
            dungeon_parts.append(f"绿洞: {record.dungeons.solo}")

        if dungeon_parts:
            lines.append(" | ".join(dungeon_parts))

        # 资源点信息（按注释顺序：石点、木点、矿点、棉点、皮点）
        resource_parts = []
        if record.resources.rock > 0:
            resource_parts.append(f"石点: {record.resources.rock}")
        if record.resources.wood > 0:
            resource_parts.append(f"木点: {record.resources.wood}")
        if record.resources.ore > 0:
            resource_parts.append(f"矿点: {record.resources.ore}")
        if record.resources.fiber > 0:
            resource_parts.append(f"棉点: {record.resources.fiber}")
        if record.resources.hide > 0:
            resource_parts.append(f"皮点: {record.resources.hide}")

        if resource_parts:
            lines.append(" | ".join(resource_parts))

        # 箱子信息（按注释：蓝箱、绿箱、金王座、金箱）
        chest_parts = []
        if record.chests.blue > 0:
            chest_parts.append(f"蓝箱: {record.chests.blue}")
        if record.chests.green > 0:
            chest_parts.append(f"绿箱: {record.chests.green}")
        if record.chests.highGold > 0:
            chest_parts.append(f"金王座: {record.chests.highGold}")
        if record.chests.lowGold > 0:
            chest_parts.append(f"金箱: {record.chests.lowGold}")

        if chest_parts:
            lines.append(" | ".join(chest_parts))

        # 兔子洞
        if record.brecilien > 0:
            lines.append("")
            lines.append(f"兔子洞: {record.brecilien}")

        return "\n".join(lines)

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

    def _show_region_selector(self) -> None:
        """显示区域选择器"""
        logger.info("显示聊天框区域选择器")
        if self._region_selector is None:
            self._region_selector = RegionSelector()
            self._region_selector.region_selected.connect(self._handle_region_selected)

        self._region_selector.showFullScreen()

    def _handle_region_selected(self, left: int, top: int, width: int, height: int) -> None:
        """处理区域选择完成，立即执行OCR"""
        logger.info("选择区域: left=%d, top=%d, width=%d, height=%d", left, top, width, height)

        # 立即执行 OCR（不保存区域）
        threading.Thread(
            target=self._run_chat_ocr,
            args=(left, top, width, height),
            daemon=True
        ).start()

    def _run_chat_ocr(self, left: int, top: int, width: int, height: int) -> None:
        """在后台线程执行聊天框 OCR"""
        try:
            logger.info("执行聊天框 OCR")
            result = self.ocr_service.capture_chat_region(left, top, width, height)
        except Exception as exc:
            logger.exception("聊天框 OCR 失败: %s", exc)
            QtCore.QMetaObject.invokeMethod(
                self,
                "_show_status_message",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, f"聊天框 OCR 失败: {exc}"),
                QtCore.Q_ARG(int, 5000),
            )
            return

        if not result:
            logger.info("聊天框 OCR 未识别到内容")
            QtCore.QMetaObject.invokeMethod(
                self,
                "_show_status_message",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, "聊天框 OCR 未识别到内容"),
                QtCore.Q_ARG(int, 3000),
            )
            return

        # 输出原始识别内容
        raw_text_preview = result.raw_text.replace('\n', ' | ')[:200]
        logger.info("聊天框 OCR 原始文本: %s", result.raw_text)

        if not result.map_names:
            logger.info("聊天框 OCR 未从原始文本中提取到地图名")
            QtCore.QMetaObject.invokeMethod(
                self,
                "_show_status_message",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, f"OCR原始: {raw_text_preview} | 未识别到地图名"),
                QtCore.Q_ARG(int, 5000),
            )
            return

        logger.info("聊天框 OCR 识别到 %d 个地图名: %s", len(result.map_names), result.map_names)

        # 在状态栏显示原始文本和识别结果
        status_msg = f"OCR原始: {raw_text_preview} | 识别到 {len(result.map_names)} 个地图: {', '.join(result.map_names)}"
        QtCore.QMetaObject.invokeMethod(
            self,
            "_show_status_message",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, status_msg),
            QtCore.Q_ARG(int, 8000),
        )

        # 在主线程中添加到搜索结果
        for map_name in result.map_names:
            QtCore.QMetaObject.invokeMethod(
                self,
                "_add_map_by_name",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, map_name),
            )

    @QtCore.Slot(str)
    def _add_map_by_name(self, map_name: str) -> None:
        """根据地图名添加到列表"""
        # 搜索地图
        results = self.search_service.search(map_name)
        if not results:
            logger.warning("未找到地图: %s", map_name)
            self._show_status_message(f"未找到地图: {map_name}", 3000)
            return

        # 选择最佳匹配
        best_result = results[0]
        logger.info("添加地图: %s (匹配度: %.2f)", best_result.record.name, best_result.score)

        # 添加到已选列表
        self._add_selected_result(best_result)
        self._show_status_message(f"已添加: {best_result.record.name}", 2000)

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
        if not self._preview_label or self._preview_pixmap is None:
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
