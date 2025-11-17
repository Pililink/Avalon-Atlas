from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

import mss
import numpy as np
from PIL import Image
from pynput import mouse

try:
    import pytesseract
except ImportError:  # pragma: no cover - 可选依赖
    pytesseract = None  # type: ignore[assignment]

from rapidocr_onnxruntime import RapidOCR

from ..config import AppConfig
from ..logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class OCRResult:
    text: str
    image: Image.Image
    raw_text: str


class OcrService:
    def __init__(self, config: AppConfig, lang: str = "eng"):
        self.config = config
        self.lang = lang
        self._mouse = mouse.Controller()
        self._backend = self.config.ocr_backend.lower()
        self._rapid: Optional[RapidOCR] = None
        if self._backend in {"rapidocr", "auto"}:
            try:
                self._rapid = RapidOCR()
            except Exception as exc:
                if self._backend == "rapidocr":
                    logger.warning("RapidOCR 初始化失败: %s", exc)
                else:
                    logger.warning("RapidOCR 初始化失败，将回退 tesseract: %s", exc)

    def capture_text(self) -> OCRResult | None:
        with mss.mss() as sct:
            bbox = self._compute_bbox(sct)
            shot = sct.grab(bbox)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        self._maybe_save_debug(image)
        raw_text, cleaned = self.recognize_image(image)
        if not cleaned:
            return None
        return OCRResult(text=cleaned, image=image, raw_text=raw_text)

    def recognize_image(self, image: Image.Image) -> tuple[str, str]:
        raw_text = self._do_ocr(image) or ""
        cleaned = self._normalize_text(raw_text)
        return raw_text, cleaned

    def _do_ocr(self, image: Image.Image) -> str:
        backend = self._backend
        if backend == "rapidocr":
            return self._run_rapidocr(image)
        if backend == "tesseract":
            return self._run_tesseract(image)
        if backend == "auto":
            text = self._run_rapidocr(image)
            if text:
                return text
            return self._run_tesseract(image)
        logger.warning("未知 OCR backend: %s", self.config.ocr_backend)
        return ""

    def _run_rapidocr(self, image: Image.Image) -> str:
        if self._rapid is None:
            logger.warning("RapidOCR backend 未正确初始化，无法执行 rapidocr OCR")
            return ""
        img_np = np.array(image.convert("RGB"))
        try:
            rec_res = self._rapid(img_np)
        except Exception as exc:
            logger.warning("RapidOCR 调用失败: %s", exc)
            return ""
        return self._extract_rapid_text(rec_res)

    def _run_tesseract(self, image: Image.Image) -> str:
        if pytesseract is None:
            logger.warning("pytesseract 未安装，无法使用 tesseract backend")
            return ""
        try:
            return pytesseract.image_to_string(image, lang=self.lang)
        except Exception as exc:
            logger.warning("tesseract 调用失败: %s", exc)
            return ""

    def _extract_rapid_text(self, rec_res) -> str:
        """
        RapidOCR 返回值兼容处理：
        - 形式通常为 [ [points, text, score], ... ] 或 [ [text, score], ... ]
        """
        if not rec_res:
            return ""

        # 若 rapidocr 返回 (result, elapsed)，取第 0 位
        if isinstance(rec_res, tuple) and len(rec_res) == 2 and isinstance(rec_res[0], (list, tuple)):
            rec_res = rec_res[0]

        candidates = []
        for item in rec_res:
            if not isinstance(item, (list, tuple)):
                continue
            if len(item) == 3:
                _, text, score = item
            elif len(item) == 2:
                text, score = item
            else:
                continue
            try:
                score_val = float(score)
            except Exception:
                score_val = 0.0
            candidates.append((str(text), score_val))

        if not candidates:
            return ""
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _normalize_text(self, text: str) -> str:
        normalized = text.replace("\n", " ").replace("_", "-").strip().lower()
        normalized = re.sub(r"[^a-z0-9\- ]", "", normalized)
        # normalized = normalized.replace(" ", "")
        return normalized

    def _compute_bbox(self, sct: mss.mss) -> dict:
        width = self.config.ocr_region.width
        height = self.config.ocr_region.height
        extra = self.config.ocr_region.vertical_offset

        pos = self._mouse.position
        center_x, center_y = int(pos[0]), int(pos[1])

        left = center_x - width // 2
        top = center_y - height - max(0, extra)
        bottom = center_y - max(0, extra)

        monitor = sct.monitors[0]
        left = max(monitor["left"], left)
        top = max(monitor["top"], top)
        right = min(monitor["left"] + monitor["width"], left + width)
        bottom = min(monitor["top"] + monitor["height"], bottom)

        width = max(1, right - left)
        height = max(1, bottom - top)
        bbox = {"left": left, "top": top, "width": width, "height": height}
        return bbox

    def close(self) -> None:
        pass

    def _maybe_save_debug(self, image: Image.Image) -> None:
        if not self.config.ocr_debug:
            return
        debug_dir = self.config.debug_dir
        debug_dir.mkdir(parents=True, exist_ok=True)
        path = debug_dir / "ocr_capture.png"
        image.save(path)
        logger.info("已保存 OCR 调试截图: %s", path)
