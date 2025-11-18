from __future__ import annotations

import ctypes
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

import keyboard
from ctypes import wintypes

from ..config import AppConfig
from ..logger import get_logger
from .ocr_service import OcrService

logger = get_logger(__name__)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
_MODIFIER_MAP = {
    "ctrl": 0x0002,
    "control": 0x0002,
    "alt": 0x0001,
    "shift": 0x0004,
    "win": 0x0008,
    "windows": 0x0008,
}
_SPECIAL_KEYS = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "capslock": 0x14,
    "numlock": 0x90,
    "scrolllock": 0x91,
    "minus": 0xBD,
    "plus": 0xBB,
    "equals": 0xBB,
    "comma": 0xBC,
    "period": 0xBE,
    "slash": 0xBF,
    "backslash": 0xDC,
    "semicolon": 0xBA,
    "quote": 0xDE,
    "bracketleft": 0xDB,
    "bracketright": 0xDD,
}


class HotkeyRegistrationError(RuntimeError):
    pass


class _WinHotkeyListener:
    """
    Windows RegisterHotKey based listener to ensure hotkeys work in fullscreen games.
    """

    def __init__(self, callback: Callable[[], None]):
        self._callback = callback
        self._thread: Optional[threading.Thread] = None
        self._thread_id: int = 0
        self._stop_event = threading.Event()
        self._combo: str = ""
        self._modifiers = 0
        self._vk = 0
        self._registered = False

    def register(self, combo: str) -> None:
        self.unregister()
        modifiers, vk = self._parse_combo(combo)
        self._combo = combo
        self._modifiers = modifiers
        self._vk = vk
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="hotkey-win", daemon=True)
        self._thread.start()

    def unregister(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread.join(timeout=2)
        self._thread = None
        self._thread_id = 0
        self._registered = False

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()

        if not user32.RegisterHotKey(None, 1, self._modifiers, self._vk):
            logger.error("Windows 全局热键注册失败: %s", self._combo)
            return
        self._registered = True

        msg = wintypes.MSG()
        while True:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0 or result == -1:
                break
            if msg.message == WM_HOTKEY and msg.wParam == 1:
                try:
                    self._callback()
                except Exception:
                    logger.exception("执行热键回调失败")
            if self._stop_event.is_set():
                break

        if self._registered:
            user32.UnregisterHotKey(None, 1)
            self._registered = False

    def _parse_combo(self, combo: str) -> tuple[int, int]:
        if not combo:
            raise HotkeyRegistrationError("热键内容为空")
        parts = [part.strip().lower() for part in combo.split("+") if part.strip()]
        modifiers = 0
        key_name: Optional[str] = None
        for part in parts:
            if part in _MODIFIER_MAP:
                modifiers |= _MODIFIER_MAP[part]
            else:
                if key_name is not None:
                    raise HotkeyRegistrationError(f"热键只支持一个主键: {combo}")
                key_name = part
        if key_name is None:
            raise HotkeyRegistrationError(f"缺少主键: {combo}")
        vk = self._resolve_vk(key_name)
        if vk is None:
            raise HotkeyRegistrationError(f"不支持的按键: {key_name}")
        return modifiers, vk

    def _resolve_vk(self, name: str) -> Optional[int]:
        if name in _SPECIAL_KEYS:
            return _SPECIAL_KEYS[name]
        if len(name) == 1:
            return ord(name.upper())
        if name.startswith("f") and name[1:].isdigit():
            num = int(name[1:])
            if 1 <= num <= 24:
                return 0x70 + num - 1
        return None


class HotkeyService:
    def __init__(self, config: AppConfig, ocr_service: OcrService):
        self.config = config
        self.ocr_service = ocr_service
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ocr")
        self._hotkey_handle: Optional[int] = None
        self._win_listener: Optional[_WinHotkeyListener] = _WinHotkeyListener(self._handle_trigger) if sys.platform == "win32" else None
        self._callback: Optional[Callable[[str], None]] = None
        self._lock = threading.Lock()
        self._ocr_lock = threading.Lock()
        self._current_combo: Optional[str] = None

    def set_callback(self, callback: Callable[[str], None]) -> None:
        self._callback = callback

    def start(self) -> None:
        with self._lock:
            if self._current_combo:
                return
            combo = self.config.hotkey
            self._register_hotkey(combo)

    def stop(self) -> None:
        with self._lock:
            self._unregister_hotkey()
            self._current_combo = None
        self._executor.shutdown(wait=False, cancel_futures=True)

    def update_hotkey(self, combo: str) -> None:
        with self._lock:
            if combo == self._current_combo:
                return
            self._unregister_hotkey()
            self._register_hotkey(combo)

    def _unregister_hotkey(self) -> None:
        if self._hotkey_handle is not None:
            keyboard.remove_hotkey(self._hotkey_handle)
            self._hotkey_handle = None
        if self._win_listener is not None:
            self._win_listener.unregister()

    def _register_hotkey(self, combo: str) -> None:
        logger.info("注册热键 %s", combo)
        if self._win_listener is not None:
            try:
                self._win_listener.register(combo)
                self._current_combo = combo
                return
            except HotkeyRegistrationError as exc:
                logger.warning("Windows 全局热键解析失败，回退 keyboard backend: %s", exc)
            except Exception as exc:  # pragma: no cover - native errors unlikely locally
                logger.warning("Windows 全局热键注册失败，回退 keyboard backend: %s", exc)
                self._win_listener.unregister()
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
