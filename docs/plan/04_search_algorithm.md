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
1. 启动时加载全部地图数组 `maps`。
2. 创建 `searcher = createFuzzySearch(maps, { key: 'name', strategy: 'aggressive' })`。
   - `strategy: 'aggressive'` 会将关键字拆分多种模式（前缀、子串、跳字匹配），适合地图命名规则。
   - 库内部维护倒排索引，查询为 `searcher(keyword)`，返回命中项与得分。
3. 当用户输入关键字 `keyword` 后：
   - 统一转换为小写、trim、去掉多余空格/非 `a-z-` 字符。
   - 若字符串长度 ≥ 2 则调用 `searcher(keyword)`；否则直接返回空列表以免噪音。
4. 搜索结果按 `microfuzz` 默认得分排序，我们额外做以下处理：
   - 结果对象 `{ item, score }` → 仅取 `item`。
   - 将全部命中结果按得分排序展示在 GUI 列表中，用户可以滚动浏览；不再限制 Top 5。
   - 当关键字能完整匹配 `name` 时优先显示，并在 UI 中置顶。
5. 查询时的 UI 反馈：
   - 输入节流（200ms）后触发搜索。
   - 显示“共匹配 X 条（仅显示前 5 条）”。
   - 若无结果则提示“未找到”。

## 集成方案
- 在 `SearchService` 中引入 `microfuzz` 的 Python 实现方案：
  1. 可直接调用 `@nozbe/microfuzz` 通过 `pyodide`?（不可行）。
  2. 推荐方式：使用 Python 库 `rapidfuzz`（API 与 microfuzz 类似）并实现 `FuzzySearcher`：
     - 初始化时构建 `rapidfuzz.process.extract` 的索引。
     - 搜索时返回得分及对象，排序方式与微调相同。
  3. 另一个可选是使用 `microfuzz` WebAssembly 版本，通过 `py_mini_racer` 调用。考虑复杂度，本地 Python 采用 `rapidfuzz`/`fuzzywuzzy` 更简洁。
- 保留当前模块的自定义匹配策略作为保底：若 `rapidfuzz` 得分低于阈值，可 fallback 到前后三字符组合。
- 查询服务返回结构：`SearchResult(name, score, tier, map_type, match_reason)`，UI 读取 `score` 排序并显示 Top 5。

## 示例伪代码
```python
from rapidfuzz import process, fuzz

class MapSearcher:
    def __init__(self, maps):
        self.maps = maps

    def search(self, keyword: str):
        keyword = keyword.lower().strip()
        if len(keyword) < 2:
            return []
        matches = process.extract(
            keyword,
            self.maps,
            processor=lambda m: m.name,
            scorer=fuzz.WRatio,
            limit=None,  # 返回全部命中项
        )
        return [SearchResult(item=match[2], score=match[1]) for match in matches]
```
- `process.extract` 返回 `(candidate_name, score, original_obj)`，根据 score (0-100) 排序。
- 列表可根据需要在 UI 中滚动展示。

## 辅助查询方式
- 热键 OCR：识别出的地图名也通过同样的 `search()`，若返回多个结果，则自动选择得分最高的一项并填入详情。
- 历史记录：缓存最近 5 次查询，作为补充建议列表。

## 兼容性
- 即使未来数据量增大（几千条地图），`rapidfuzz`/`microfuzz` 都能在毫秒级返回结果。
- 若需要前端同样的体验，可在后续 Web 版直接沿用 `ava-maps` 的 React + microfuzz 实现。
