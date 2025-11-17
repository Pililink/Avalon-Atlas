# 地图查询算法与实现方式

## 参考项目
- 仓库：`https://github.com/lucioreyli/ava-maps`
- 本地路径：`D:/src_study/ava-maps`
- 关键文件：`src/routes/index.tsx`, `src/constants/maps.ts`
- 搜索库：`@nozbe/microfuzz`（轻量模糊搜索）

## 数据结构映射
- 数据源 `maps.ts` 与当前项目 `maps/maps.json` 字段一致：`name/tier/type/chests/dungeons/resources/brecilien`。
- 名称格式为纯英文小写（`xxx-xxx`、`xxx-xx-xxx`），用于静态资源映射。

## 算法流程
1. 启动时加载全部地图数组 `maps`，并缓存成 `MapRecord` 列表。
2. 查询阶段直接在内存中进行“子序列匹配 + 动态规划评分”：
   - 将用户输入统一为小写、trim，并要求长度 ≥ 2。
   - 遍历全部 `MapRecord`，对 `record.name` 执行 `subsequence_match(query, name)`。
   - 算法逐字符扫描候选串，通过 DP 比较 `query` 每个字符在目标串中的所有匹配位置，累积分值并记录路径：
     - 命中基础得分：例如 10 分。
     - 额外奖励：位于单词起始（`-/_/空格` 后）、字符串起始、连续相邻等。
     - 惩罚：跨越的非匹配字符越多，扣分越多。
   - 得分最高的路径会输出匹配索引数组 `positions`（用于 UI 高亮）。
3. 所有命中结果按 `score` → `tier` → `slug` 排序，截取前 `max_results`（默认 25）展示在弹出列表中。
4. 若整个查询没有 DP 命中，则回退至 `_fallback_match`（前后缀匹配 + 片段比对）确保仍能返回候选。
5. UI 层的行为保持不变：输入节流（200ms）触发搜索，得分最高的结果位于顶部；未来可根据 `positions` 渲染红色高亮。

## 集成方案
- 在 `atlas/services/fuzzy_match.py` 中实现 `subsequence_match`：
  - 输入：`query`、`candidate`。
  - 输出：`MatchDetail(score, positions)`，若不存在合法子序列则返回 `None`。
  - 采用二维 DP 表缓存每个 `query[:i]` 匹配到 `candidate[:j]` 的最高得分，以及回溯指针。
- `MapSearchService` 的 `_fuzzy_match` 遍历所有记录并调用上述函数，生成 `SearchResult(record, score, method='subsequence', positions=...)`。
- `_fallback_match` 仍保留，用于极端输入（如含特殊符号或 DP 无解）时保证最少结果。
- 缓存：对最近 64 次查询进行 LRU 缓存，复用上一轮结果。

## 示例伪代码
```python
def subsequence_match(pattern: str, text: str) -> MatchDetail | None:
    pattern = pattern.lower()
    text = text.lower()
    if len(pattern) > len(text):
        return None

    neg_inf = float("-inf")
    dp = [[neg_inf] * len(text) for _ in pattern]
    backtrack = [[-1] * len(text) for _ in pattern]

    # 初始化第一列
    for j, ch in enumerate(text):
        if ch == pattern[0]:
            dp[0][j] = base_score(j)

    for i in range(1, len(pattern)):
        for j, ch in enumerate(text):
            if ch != pattern[i]:
                continue
            best = neg_inf
            best_prev = -1
            for k in range(j):
                prev = dp[i - 1][k]
                if prev == neg_inf:
                    continue
                score = prev + transition_score(text, k, j)
                if score > best:
                    best = score
                    best_prev = k
            dp[i][j] = best
            backtrack[i][j] = best_prev

    # 取最后一行最高得分并回溯 positions
```
- `base_score`/`transition_score` 根据首字母、相邻字符、间隔惩罚等规则计算得分。
- 回溯得到的 `positions` 可直接用于 UI 高亮。

## 辅助查询方式
- 热键 OCR：识别出的地图名也通过同样的 `search()`，若返回多个结果，则自动选择得分最高的一项并填入详情。
- 历史记录：缓存最近 5 次查询，作为补充建议列表。

## 兼容性
- 算法为 O(N * M * L)（N=地图数量，M=关键字长度，L=候选名长度），在 400 条地图、每个名字 ~15 字符场景下性能仍然在毫秒级。
- 未来若需要 Web 同步体验，可在前端复用相同的子序列匹配规则，或使用已有的 fuzzy finder 算法（fzf/microfuzz）实现一致的得分策略。
