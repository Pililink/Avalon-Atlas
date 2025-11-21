from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Sequence

from ..data.models import MapRecord
from ..data.repository import MapRepository
from ..logger import get_logger
from .fuzzy_match import subsequence_match

logger = get_logger(__name__)


@dataclass(slots=True)
class SearchResult:
    record: MapRecord
    score: float
    method: str
    positions: List[int] | None = None


class MapSearchService:
    def __init__(self, repository: MapRepository):
        self.repository = repository
        self._records: Sequence[MapRecord] = ()
        self._cache: OrderedDict[str, List[SearchResult]] = OrderedDict()
        self.max_results = 25
        self.min_chars = 2
        self._cache_size = 256  # 增加缓存容量以提升重复搜索性能

    def refresh(self) -> None:
        self.repository.ensure_loaded()
        self._records = self.repository.all()
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
            # 尝试缩写匹配
            results = self._abbreviation_match(query)
        if not results:
            results = self._fallback_match(query)
        self._remember(query, results)
        return results

    def _fuzzy_match(self, query: str) -> List[SearchResult]:
        matches: List[SearchResult] = []
        for record in self._records:
            detail = subsequence_match(query, record.name)
            if not detail:
                continue
            matches.append(
                SearchResult(
                    record=record,
                    score=detail.score,
                    method="subsequence",
                    positions=detail.positions,
                )
            )

        matches.sort(key=lambda r: (-r.score, r.record.tier, r.record.slug))
        return matches[: self.max_results]

    def _abbreviation_match(self, query: str) -> List[SearchResult]:
        """
        缩写匹配：支持将查询字符串拆分为多段，与地图名的各段匹配
        例如：souuzu 匹配 soues-uzurtum，qiiinvie 匹配 qiient-in-viesis
        """
        # 如果查询包含 '-'，则不使用缩写匹配
        if "-" in query:
            return []

        candidates: List[SearchResult] = []
        for record in self._records:
            score = self._match_abbreviation(query, record.slug)
            if score > 0:
                candidates.append(SearchResult(record=record, score=score, method="abbreviation"))

        candidates.sort(key=lambda r: (-r.score, r.record.tier, r.record.slug))
        return candidates[: self.max_results]

    def _match_abbreviation(self, query: str, slug: str) -> float:
        """
        尝试将查询字符串拆分为多段，与 slug 的各段匹配
        返回匹配得分，0 表示不匹配
        """
        parts = slug.split("-")
        num_parts = len(parts)

        # 地图名必须有 2-3 段
        if num_parts < 2 or num_parts > 3:
            return 0.0

        # 早期剪枝：查询长度太短或太长
        if len(query) < num_parts or len(query) > sum(len(p) for p in parts):
            return 0.0

        # 尝试不同的拆分方式
        best_score = 0.0

        if num_parts == 2:
            # 两段地图名：尝试所有可能的拆分点
            for split_pos in range(1, len(query)):
                q1, q2 = query[:split_pos], query[split_pos:]

                # 早期剪枝：检查第一段是否可能匹配
                if not self._is_prefix_or_contains(parts[0], q1):
                    continue

                if self._is_prefix_or_contains(parts[1], q2):
                    # 计算得分：前缀匹配得分更高
                    score = 0.0
                    if parts[0].startswith(q1):
                        score += 40.0 * (len(q1) / len(parts[0]))
                    else:
                        score += 30.0 * (len(q1) / len(parts[0]))

                    if parts[1].startswith(q2):
                        score += 40.0 * (len(q2) / len(parts[1]))
                    else:
                        score += 30.0 * (len(q2) / len(parts[1]))

                    best_score = max(best_score, score)

        elif num_parts == 3:
            # 三段地图名：尝试两个拆分点，增加早期剪枝
            for split1 in range(1, len(query) - 1):
                q1 = query[:split1]

                # 早期剪枝：第一段必须可能匹配
                if not self._is_prefix_or_contains(parts[0], q1):
                    continue

                for split2 in range(split1 + 1, len(query)):
                    q2, q3 = query[split1:split2], query[split2:]

                    if (
                        self._is_prefix_or_contains(parts[1], q2)
                        and self._is_prefix_or_contains(parts[2], q3)
                    ):
                        # 计算得分
                        score = 0.0
                        for part, q_part in zip(parts, [q1, q2, q3]):
                            if part.startswith(q_part):
                                score += 35.0 * (len(q_part) / len(part))
                            else:
                                score += 25.0 * (len(q_part) / len(part))

                        best_score = max(best_score, score)

        return best_score

    def _is_prefix_or_contains(self, text: str, query: str) -> bool:
        """检查 query 是否是 text 的前缀或包含在 text 中"""
        if not query:
            return False
        return text.startswith(query) or query in text

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
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
