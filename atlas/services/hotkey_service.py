from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

import keyboard

from ..config import AppConfig
from ..logger import get_logger
from .ocr_service import OcrService

logger = get_logger(__name__)


class HotkeyService:
    def __init__(self, config: AppConfig, ocr_service: OcrService):
        self.config = config
        self.ocr_service = ocr_service
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ocr")
        self._hotkey_handle: Optional[int] = None
        self._callback: Optional[Callable[[str], None]] = None
        self._lock = threading.Lock()
        self._ocr_lock = threading.Lock()
        self._current_combo: Optional[str] = None

    def set_callback(self, callback: Callable[[str], None]) -> None:
        self._callback = callback

    def start(self) -> None:
        with self._lock:
            if self._hotkey_handle is not None:
                return
            combo = self.config.hotkey
            self._register_hotkey(combo)

    def stop(self) -> None:
        with self._lock:
            if self._hotkey_handle is not None:
                keyboard.remove_hotkey(self._hotkey_handle)
                self._hotkey_handle = None
            self._current_combo = None
        self._executor.shutdown(wait=False, cancel_futures=True)

    def update_hotkey(self, combo: str) -> None:
        with self._lock:
            if combo == self._current_combo and self._hotkey_handle is not None:
                return
            if self._hotkey_handle is not None:
                keyboard.remove_hotkey(self._hotkey_handle)
                self._hotkey_handle = None
            self._register_hotkey(combo)

    def _register_hotkey(self, combo: str) -> None:
        logger.info("注册热键 %s", combo)
        handle = keyboard.add_hotkey(combo, self._handle_trigger)
        self._hotkey_handle = handle
        self._current_combo = combo

    def _handle_trigger(self) -> None:
        self._executor.submit(self._run_ocr)

    def _run_ocr(self) -> None:
        if not self._ocr_lock.acquire(blocking=False):
            logger.info("已有 OCR 任务正在执行，忽略本次触发")
            return
        try:
            logger.info("执行 OCR 捕获")
            result = self.ocr_service.capture_text()
        except Exception as exc:
            logger.exception("OCR 失败: %s", exc)
            return
        finally:
            self._ocr_lock.release()

        if not result:
            logger.info("OCR 未识别到文本")
            return
        logger.info("OCR 识别文本: %s", result.text)

        if self._callback:
            self._callback(result.text)
