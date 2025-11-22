"""区域选择器 - 用于框选屏幕区域进行 OCR"""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ..logger import get_logger

logger = get_logger(__name__)


class RegionSelector(QtWidgets.QWidget):
    """全屏半透明遮罩,支持鼠标框选区域"""

    region_selected = QtCore.Signal(int, int, int, int)  # left, top, width, height

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(QtCore.Qt.WindowState.WindowFullScreen)

        # 框选状态
        self._start_pos: Optional[QtCore.QPoint] = None
        self._current_pos: Optional[QtCore.QPoint] = None
        self._is_selecting = False

        # 设置鼠标光标
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)

    def showFullScreen(self) -> None:
        """显示全屏选择器"""
        # 重置选择状态，确保每次都是干净的状态
        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False

        # 获取所有屏幕的总区域
        screens = QtWidgets.QApplication.screens()
        if not screens:
            super().showFullScreen()
            return

        # 计算所有屏幕的边界
        total_rect = QtCore.QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())

        self.setGeometry(total_rect)
        super().show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """绘制半透明遮罩和选择框"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # 绘制半透明黑色背景
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 100))

        # 绘制选择框
        if self._start_pos and self._current_pos:
            rect = self._get_selection_rect()

            # 清除选择区域的遮罩(显示原始屏幕)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, QtCore.Qt.GlobalColor.transparent)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)

            # 绘制选择框边框
            pen = QtGui.QPen(QtGui.QColor(0, 120, 215), 2, QtCore.Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 显示尺寸信息
            text = f"{rect.width()} × {rect.height()}"
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)

            # 文本背景
            text_rect = painter.fontMetrics().boundingRect(text)
            text_rect.moveTopLeft(rect.topLeft() + QtCore.QPoint(5, -text_rect.height() - 5))
            painter.fillRect(text_rect.adjusted(-3, -2, 3, 2), QtGui.QColor(0, 0, 0, 180))

            # 绘制文本
            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """开始框选"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """更新框选区域"""
        if self._is_selecting:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """完成框选"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._is_selecting:
            self._current_pos = event.pos()
            self._is_selecting = False

            rect = self._get_selection_rect()
            if rect.width() > 10 and rect.height() > 10:  # 最小区域限制
                # 将widget坐标转换为全局屏幕坐标
                global_top_left = self.mapToGlobal(rect.topLeft())
                global_x = global_top_left.x()
                global_y = global_top_left.y()

                logger.info(
                    "区域选择完成 - Widget坐标: (%d, %d, %d, %d), 屏幕坐标: (%d, %d, %d, %d)",
                    rect.x(), rect.y(), rect.width(), rect.height(),
                    global_x, global_y, rect.width(), rect.height()
                )

                self.region_selected.emit(global_x, global_y, rect.width(), rect.height())

            self.close()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """ESC 键取消选择"""
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()

    def _get_selection_rect(self) -> QtCore.QRect:
        """获取标准化的选择矩形"""
        if not self._start_pos or not self._current_pos:
            return QtCore.QRect()

        return QtCore.QRect(self._start_pos, self._current_pos).normalized()
