from __future__ import annotations

from collections import OrderedDict
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


class RapidFuzzIndex:
    def __init__(self) -> None:
        self._records: Sequence[MapRecord] = ()
        self._slugs: List[str] = []

    def build(self, records: Sequence[MapRecord]) -> None:
        self._records = tuple(records)
        self._slugs = [rec.slug for rec in self._records]

    def query(self, query: str, limit: int, cutoff: int) -> List[SearchResult]:
        if not self._records:
            return []
        matches = process.extract(
            query,
            self._slugs,
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=cutoff,
        )
        results: List[SearchResult] = []
        for _slug, score, idx in matches:
            record = self._records[idx]
            results.append(SearchResult(record=record, score=float(score), method="rapidfuzz"))
        return results


class MapSearchService:
    def __init__(self, repository: MapRepository):
        self.repository = repository
        self._records: Sequence[MapRecord] = ()
        self._index = RapidFuzzIndex()
        self._cache: OrderedDict[str, List[SearchResult]] = OrderedDict()
        self.max_results = 25
        self.min_chars = 2
        self.score_cutoff = 55

    def refresh(self) -> None:
        self.repository.ensure_loaded()
        self._records = self.repository.all()
        self._index.build(self._records)
        self._cache.clear()
        logger.info("搜索索引构建完成，共 %s 条", len(self._records))

    def search(self, keyword: str) -> List[SearchResult]:
        query = keyword.strip().lower()
        if len(query) < self.min_chars:
            return []

        if not self._records:
            self.refresh()

        if query in self._cache:
            return self._cache[query]

        results = self._fuzzy_match(query)
        if not results:
            results = self._fallback_match(query)
        self._remember(query, results)
        return results

    def _fuzzy_match(self, query: str) -> List[SearchResult]:
        return self._index.query(query, limit=self.max_results, cutoff=self.score_cutoff)

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
        return candidates[: self.max_results]

    def _remember(self, query: str, results: List[SearchResult]) -> None:
        self._cache[query] = results
        if len(self._cache) > 64:
            self._cache.popitem(last=False)
