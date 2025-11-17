# 模块实现方案

## 1. 配置与数据
- `config.py`
  - 使用 `dataclasses` 或 `pydantic` 定义配置（OCR 截屏尺寸、热键组合、地图数据路径、最小匹配长度等）。
  - OCR 范围参数：`ocr_box_width`、`ocr_box_height`、`vertical_offset`。默认逻辑为以鼠标位置为中心，向上偏移半个高度形成一个长方形区域，确保鼠标位于矩形底边中心（参考示例图）。
  - 提供 `load_config()`：支持从 `config.json` 覆盖默认值。
- `assets/maps.json`
  - 结构示例：`{"id": 1, "name": "alpha-beta", "tags": ["森林"], "note": "Boss 点位"}`。
  - 允许手工扩展别名 `aliases` 列表，提升模糊匹配准确度。
  - 保证 `name` 为纯小写英文 + `-` 的组合，在加载阶段可统一 `name = name.lower()`，并通过正则 `^[a-z]+(-[a-z]+)+$` 校验，防止命名污染影响静态资源映射。

## 2. 数据访问层 `atlas/data/repository.py`
- `MapRepository`
  - `load()`：读取 JSON→`MapInfo` 对象缓存。
  - `search(keyword: str) -> list[MapInfo]`：委托 `SearchService`。
  - 提供 `get_recent(limit)` 用于下方展示历史。

## 3. 搜索服务 `atlas/services/search_service.py`
- 核心输入：用户关键字。
- 预处理：去空格、统一大小写、过滤非字母数字/`-`。
- 基础算法直接复用 `ava-maps` 项目（本地路径 `D:/src_study/ava-maps`）所采用的 `@nozbe/microfuzz` 思路：构建 `name` 索引并使用 aggressive 策略进行模糊匹配。Python 端推荐使用 `rapidfuzz`/`fuzz.WRatio` 还原同等效果。
- 匹配策略：
  1. `rapidfuzz.process.extract(keyword, maps, processor=lambda m: m.name)` 获取得分列表。
  2. 如果关键词完全匹配或命中别名，直接置顶，其余结果按得分排序。
  3. 若 `rapidfuzz` 分数低于阈值，再尝试自定义规则（前后三字符、按 `-` 分段首字符拼接等）作为补充。
- 排序：首先按 `rapidfuzz` 得分，其次按 `tier`、`name`（保证稳定顺序）。
- 输出：`SearchResult` 包含 map 信息、得分、匹配方式说明，供 UI 显示。

## 4. GUI 层
- `atlas/ui/main_window.py`
  - 使用 `QVBoxLayout`：顶部 `QLineEdit` + `QPushButton(查询/清除)`；中间 `QListWidget` 显示结果；底部 `QTextEdit` 或 `QLabel` 展示选中详情。
  - 信号：
    - 输入框 `returnPressed`、查询按钮 `clicked` → 调用 `SearchService`。
    - 清除按钮 → 清空输入/结果/详情。
    - 列表 `itemSelectionChanged` → 更新详情区域。
  - 状态提示：使用 `QStatusBar` 或临时 `QLabel` 提示 OCR 结果、错误信息。
- UI 线程安全
  - 热键/OCR 运行在后台线程，使用 `QtCore.Signal` 将文本传回主线程。

## 5. OCR 服务 `atlas/services/ocr_service.py`
- 依赖：`mss` 截屏、`Pillow` 处理、`pytesseract` 识别。
- `capture_region(center: QPoint, size: QSize) -> Image`：计算截屏区域，处理 DPI。默认实现按照配置中的宽高并以鼠标为中心，向上取矩形（`left = x - width/2`, `top = y - height`，`bottom = y`），使鼠标位于底边中点。需要对越界情况做裁剪（多屏/高 DPI 下以主屏边界为准），避免 `mss` 抛异常。
- `recognize(image) -> str`：可配置语言包（英文/中文）。
- 输出清洗：统一成地图命名格式（小写、用 `-` 连接、剔除空格）。
- 提供同步与异步接口，供热键服务调用。

## 6. 热键服务 `atlas/services/hotkey_service.py`
- 使用 `keyboard` 或 `pynput` 监听设定热键（如 `Ctrl+Alt+M`）。
- 被触发时：
  1. 获取当前鼠标坐标（`pyautogui.position()` 或 `pynput.mouse.Controller()`）。
  2. 调用 `OcrService.capture + recognize`。
  3. 将识别文本通过回调/Qt Signal 发送给 GUI。
- 运行方式：在应用启动时开线程常驻，退出时优雅停止。提供 `start()/stop()` 接口，由 `MainWindow.closeEvent` 调用 `stop()` 与 `join()`，确保不会留下监听线程阻塞进程。

## 7. 事件流整合
1. `MainWindow` 初始化 → 创建 `SearchService`, `OcrService`, `HotkeyService`。
2. `HotkeyService` 设置回调 `on_new_text` → Qt Slot `handle_hotkey_text`。
3. Slot 更新输入框内容并调用 `trigger_search()`。
4. `trigger_search()` 调用 `repository.search`，将结果模型转成 `QListWidgetItem`。
5. 列表选中后，详情区域展示 `name / tags / note`，并提供复制按钮。

## 8. 错误处理与用户反馈
- 配置/数据加载失败 → 弹窗 + 日志记录。
- OCR 失败或为空 → 在状态区域提示“未识别出地图名”。
- 热键冲突检测：启动时验证注册结果。

## 9. 后续扩展
- 支持多语言 UI（Qt 翻译文件）。
- 引入 SQLite 存储地图扩展属性、收藏夹。
- 使用更精准的 OCR（如 `paddleocr`）并加入模型下载提示。

## 10. 地图数据与静态资源现状
- **地图结构**（`maps/model.py`）  
  - `MapMdoel` 通过 Pydantic 校验，字段包含：`name`、`tier (T4/T6/T8)`、`map_type`（覆盖王城/黑区/深层等 12 种隧道类型）、`chests`（蓝/绿/金箱、金王座数量）、`dungeons`（单人/蓝洞/金洞数量）、`resources`（石/木/矿/棉/皮资源权重）、`brecilien`（布雷希恩传送门数）。  
  - 子模型 `Chests`、`Dungeons`、`Resources` 对计数字段进行类型约束，确保 JSON 中的统计数据合法。  
  - `maps/maps.py` 在加载 JSON 时会把原始字段 `type` 转换为 `map_type` 并依次校验，若单个条目失败则打印警告继续，其余数据可用。
- **数据来源**  
  - `maps/maps.json` 已整理为结构化列表，可直接映射 `MapMdoel`。后续如需添加别名/关键词，可在 JSON 每个对象中加自定义字段并在模型中扩展。
- **静态资源**（`static/`）  
  - `static/assets/` 存放通用图标：箱子、洞穴、资源类别、布雷希恩传送门等，命名与 `MapMdoel` 字段对应，GUI 可依据 `tier`、`map_type` 或资源分布展示相应图标。  
  - `static/maps/` 包含每张地图的预览图（`.png` 与 `.webp` 双格式），文件名严格遵循地图名称：纯英文小写+`-` 组合，无其它符号（示例 `casos-aiagsum.png`）。GUI 加载顺序建议为 `.webp` → `.png` → 默认占位图。  
  - 静态文件已经分好目录，可在构建阶段复制到发布目录或通过 `importlib.resources` 动态加载。

## 11. 搜索与数据更新补充
- 搜索排序策略：  
  1. 完整匹配或别名匹配权重最高。  
  2. 前后三字符组合、段首字符拼接等策略命中时赋予次级权重。  
  3. `rapidfuzz` 模糊得分用于排序，不再截断结果，列表可无限滚动查看。  
  4. 若得分相同，按 `tier` 与 `name` 字典序排序，确保结果稳定。  
- 数据更新：`maps.json` 可通过外部脚本（位于 `tools/`）定期生成，应用启动时检测文件更新时间；必要时在 GUI 中提供“刷新数据”按钮调用 `MapRepository.reload()`，避免重启。对静态图片则按需懒加载，找不到图片可记录日志以便补齐资源。
