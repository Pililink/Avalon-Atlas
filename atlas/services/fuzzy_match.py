from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

__all__ = ["MatchDetail", "subsequence_match"]


@dataclass(slots=True)
class MatchDetail:
    score: float
    positions: List[int]


BASE_MATCH_SCORE = 10.0
ADJACENT_BONUS = 14.0
WORD_START_BONUS = 8.0
START_OF_STRING_BONUS = 4.0
GAP_PENALTY = 2.0
NON_ALNUM_CHARS: Sequence[str] = ("-", "_", " ", "/")

# 相似字符映射 - 用于处理容易混淆的字符
SIMILAR_CHARS = {
    'i': {'i', 'l', '1', '|'},
    'l': {'i', 'l', '1', '|'},
    '1': {'i', 'l', '1', '|'},
    '|': {'i', 'l', '1', '|'},
    'o': {'o', '0'},
    '0': {'o', '0'},
    's': {'s', '5'},
    '5': {'s', '5'},
    'z': {'z', '2'},
    '2': {'z', '2'},
}


def _chars_match(ch1: str, ch2: str) -> bool:
    """判断两个字符是否匹配（完全相等或相似）"""
    if ch1 == ch2:
        return True
    similar_set = SIMILAR_CHARS.get(ch1)
    if similar_set and ch2 in similar_set:
        return True
    return False


def subsequence_match(query: str, candidate: str) -> MatchDetail | None:
    """
    子序列匹配 + 动态规划评分。

    返回最佳匹配的累计得分以及每个查询字符对应的索引（便于 UI 高亮）。
    """
    query = query.strip()
    if not query or not candidate:
        return None

    pattern = query.lower()
    target = candidate.lower()
    if len(pattern) > len(target):
        return None

    m = len(pattern)
    n = len(target)
    neg_inf = float("-inf")
    dp: List[List[float]] = [[neg_inf] * n for _ in range(m)]
    backtrack: List[List[int]] = [[-1] * n for _ in range(m)]

    for j, ch in enumerate(target):
        if _chars_match(pattern[0], ch):
            dp[0][j] = _score_position(candidate, j, prev_idx=-1)

    if max(dp[0]) == neg_inf:
        return None

    for i in range(1, m):
        for j, ch in enumerate(target):
            if not _chars_match(pattern[i], ch):
                continue
            best_score = neg_inf
            best_prev = -1
            for k in range(j):
                prev_score = dp[i - 1][k]
                if prev_score == neg_inf:
                    continue
                score = prev_score + _score_position(candidate, j, prev_idx=k)
                if score > best_score:
                    best_score = score
                    best_prev = k
            dp[i][j] = best_score
            backtrack[i][j] = best_prev

    best_final_idx = -1
    best_final_score = neg_inf
    for j, score in enumerate(dp[m - 1]):
        if score > best_final_score:
            best_final_score = score
            best_final_idx = j

    if best_final_idx == -1 or best_final_score == neg_inf:
        return None

    positions = [0] * m
    idx = best_final_idx
    for i in range(m - 1, -1, -1):
        positions[i] = idx
        idx = backtrack[i][idx] if i > 0 else -1
        if i > 0 and idx == -1:
            # 说明该路径无效
            return None

    return MatchDetail(score=best_final_score, positions=positions)


def _score_position(text: str, idx: int, prev_idx: int) -> float:
    score = BASE_MATCH_SCORE
    if _is_word_start(text, idx):
        score += WORD_START_BONUS
    if idx == 0:
        score += START_OF_STRING_BONUS

    if prev_idx == -1:
        score -= idx * GAP_PENALTY
    else:
        gap = idx - prev_idx - 1
        if gap <= 0:
            score += ADJACENT_BONUS
        else:
            score -= gap * GAP_PENALTY
    return score


def _is_word_start(text: str, idx: int) -> bool:
    if idx == 0:
        return True
    prev = text[idx - 1]
    if prev in NON_ALNUM_CHARS:
        return True
    curr = text[idx]
    return prev.islower() and curr.isupper()
