from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

from importlib import resources
import sys

from .. import PACKAGE_ROOT
from ..maps.model import MapMdoel

from ..logger import get_logger
from .models import MapRecord

logger = get_logger(__name__)


class MapRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._records: List[MapRecord] = []
        self._by_slug: dict[str, MapRecord] = {}

    def load(self) -> Sequence[MapRecord]:
        payload = self._read_json(self.data_path)

        records: List[MapRecord] = []
        for raw in payload:
            item = dict(raw)
            if "type" in item:
                item["map_type"] = item.pop("type")

            model = MapMdoel(**item)
            record = MapRecord.from_model(model)
            records.append(record)

        self._records = records
        self._by_slug = {rec.slug: rec for rec in records}
        logger.info("加载 %s 条地图数据", len(records))
        return tuple(self._records)

    def _read_json(self, path: Path) -> list[dict]:
        candidates = [path]

        # 在 PyInstaller 环境中，数据可能位于 _MEIPASS/static
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "static" / "data" / "maps.json")

        # 本地开发默认 static 目录
        candidates.append(PACKAGE_ROOT.parent / "static" / "data" / "maps.json")

        for candidate in candidates:
            if candidate and candidate.exists():
                with candidate.open("r", encoding="utf-8") as f:
                    return json.load(f)

        # 最后尝试读取打包在模块中的 JSON（向后兼容）
        try:
            package_file = resources.files("atlas.maps").joinpath("maps.json")
            with package_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"地图数据文件不存在: {path}") from exc

    def all(self) -> Sequence[MapRecord]:
        return tuple(self._records)

    def get_by_slug(self, slug: str) -> MapRecord | None:
        return self._by_slug.get(slug.lower())

    def ensure_loaded(self) -> None:
        if not self._records:
            self.load()

    def __len__(self) -> int:
        return len(self._records)
