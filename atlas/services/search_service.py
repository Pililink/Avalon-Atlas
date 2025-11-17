from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from rapidfuzz import fuzz, process

from ..data.models import MapRecord
from ..data.repository import MapRepository
from ..logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class SearchResult:
    record: MapRecord
    score: float
    method: str


class MapSearchService:
    def __init__(self, repository: MapRepository):
        self.repository = repository
        self._records: Sequence[MapRecord] = ()
        self._slugs: List[str] = []

    def refresh(self) -> None:
        self.repository.ensure_loaded()
        self._records = self.repository.all()
        self._slugs = [rec.slug for rec in self._records]
        logger.info("搜索索引构建完成，共 %s 条", len(self._records))

    def search(self, keyword: str) -> List[SearchResult]:
        query = keyword.strip().lower()
        if len(query) < 2:
            return []

        if not self._records:
            self.refresh()

        results = self._fuzzy_match(query)
        if not results:
            results = self._fallback_match(query)
        return results

    def _fuzzy_match(self, query: str) -> List[SearchResult]:
        matches = process.extract(
            query,
            self._slugs,
            scorer=fuzz.WRatio,
            limit=None,
            score_cutoff=35,
        )
        results: List[SearchResult] = []
        for slug, score, idx in matches:
            record = self._records[idx]
            results.append(SearchResult(record=record, score=float(score), method="rapidfuzz"))
        return results

    def _fallback_match(self, query: str) -> List[SearchResult]:
        candidates: List[SearchResult] = []
        for record in self._records:
            slug = record.slug
            score = 0.0
            method = None

            if slug.startswith(query) or slug.endswith(query):
                score = 70.0
                method = "prefix_suffix"
            else:
                parts = slug.split("-")
                stitched = "".join(chunk[:3] for chunk in parts if chunk)
                if query in stitched:
                    score = 60.0
                    method = "segment_match"

            if score:
                candidates.append(SearchResult(record=record, score=score, method=method or "heuristic"))

        candidates.sort(key=lambda r: (-r.score, r.record.tier, r.record.slug))
        return candidates
