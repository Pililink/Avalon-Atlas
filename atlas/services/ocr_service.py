from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Optional, Sequence

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
from ..data.repository import MapRepository
from ..logger import get_logger

logger = get_logger(__name__)
_MAP_CANDIDATE_PATTERN = re.compile(
    r"[A-Za-z]{2,}\s*-\s*[A-Za-z]{2,}(?:\s*-\s*[A-Za-z]{2,})?",
    re.MULTILINE,
)
_OCR_CHAR_FIXES = str.maketrans(
    {
        "0": "o",
        "1": "l",
        "2": "z",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "b",
        "7": "t",
        "8": "b",
        "9": "g",
        "|": "l",
        "¡": "l",
    }
)


@dataclass(slots=True)
class OCRResult:
    text: str
    image: Image.Image
    raw_text: str


class OcrService:
    def __init__(self, config: AppConfig, lang: str = "eng", *, repository: MapRepository | None = None):
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
        self._slug_lookup = self._build_slug_lookup(repository)
        self._match_cache: dict[str, str] = {}
        self._fuzzy_threshold = 0.8

    def _build_slug_lookup(self, repository: MapRepository | None) -> dict[str, str]:
        slug_lookup: dict[str, str] = {}
        records: Sequence | None = None
        source_repo = repository
        if source_repo is not None:
            try:
                source_repo.ensure_loaded()
                records = source_repo.all()
            except Exception as exc:
                logger.warning("从 MapRepository 读取地图数据失败: %s", exc)
        if records is None:
            try:
                fallback_repo = MapRepository(self.config.maps_data_path)
                fallback_repo.load()
                records = fallback_repo.all()
            except Exception as exc:
                logger.warning("无法加载地图名称用于 OCR 矫正: %s", exc)
                records = None
        if not records:
            return slug_lookup
        for record in records:
            slug_lookup[record.slug] = record.name
        logger.info("OCR map name lookup 构建完成，共 %s 条", len(slug_lookup))
        return slug_lookup

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
        返回所有条目的文本，按 RapidOCR 识别顺序拼接，便于后续正则提取地图名称。
        """
        if not rec_res:
            return ""

        # 若 rapidocr 返回 (result, elapsed)，取第 0 位
        if isinstance(rec_res, tuple) and len(rec_res) == 2 and isinstance(rec_res[0], (list, tuple)):
            rec_res = rec_res[0]

        texts: list[str] = []
        for item in rec_res:
            if not isinstance(item, (list, tuple)):
                continue
            if len(item) == 3:
                _, text, score = item
            elif len(item) == 2:
                text, score = item
            else:
                continue
            text_str = str(text).strip()
            if not text_str:
                continue
            texts.append(text_str)

        if not texts:
            return ""
        return "\n".join(texts)

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        resolved = self._resolve_map_name(text)
        if resolved:
            return resolved
        # Return empty when no known map name matched to avoid UI selection
        return ""

    def _resolve_map_name(self, text: str) -> str:
        if not text or not self._slug_lookup:
            return ""
        candidates = self._extract_map_candidates(text)
        for candidate in candidates:
            slug = self._standardize_candidate(candidate)
            match = self._match_known_slug(slug)
            if match:
                return match
        fallback_slug = self._standardize_candidate(text)
        return self._match_known_slug(fallback_slug)

    def _extract_map_candidates(self, text: str) -> Sequence[str]:
        normalized = text.replace("_", "-")
        return [match.group(0) for match in _MAP_CANDIDATE_PATTERN.finditer(normalized)]

    def _standardize_candidate(self, text: str) -> str:
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.translate(_OCR_CHAR_FIXES)
        normalized = normalized.replace("—", "-").replace("–", "-").replace("―", "-").replace("−", "-")
        normalized = normalized.replace("_", "-")
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z\- ]", "", normalized)
        normalized = normalized.replace(" ", "")
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        if not normalized or "-" not in normalized:
            return ""
        parts = [part for part in normalized.split("-") if part]
        if len(parts) < 2:
            return ""
        if len(parts) > 3:
            parts = parts[:3]
        slug = "-".join(parts)
        hyphen_count = slug.count("-")
        if hyphen_count not in (1, 2):
            return ""
        return slug

    def _match_known_slug(self, slug: str) -> str:
        if not slug or not self._slug_lookup:
            return ""
        direct = self._slug_lookup.get(slug)
        if direct:
            self._match_cache[slug] = direct
            return direct
        cached = self._match_cache.get(slug)
        if cached:
            return cached
        best_name = ""
        best_score = 0.0
        slug_hyphen = slug.count("-")
        for known_slug, name in self._slug_lookup.items():
            known_hyphen = known_slug.count("-")
            if abs(known_hyphen - slug_hyphen) > 1:
                continue
            length_diff = abs(len(known_slug) - len(slug))
            if length_diff > 4:
                continue
            score = SequenceMatcher(None, slug, known_slug).ratio()
            if score > best_score:
                best_score = score
                best_name = name
        if best_score >= self._fuzzy_threshold and best_name:
            self._match_cache[slug] = best_name
            return best_name
        return ""

    def _fallback_normalize(self, text: str) -> str:
        normalized = text.replace("\n", " ").replace("_", "-").strip().lower()
        normalized = re.sub(r"[^a-z0-9\- ]", "", normalized)
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = debug_dir / f"ocr_capture_{timestamp}.png"
        image.save(path)
        logger.info("已保存 OCR 调试截图: %s", path)