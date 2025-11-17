# Avalon-Online-Atlas

# 简介
桌面端辅助工具，用于查询阿瓦隆地图的箱子、资源、洞穴等信息。支持手动输入或热键 OCR 捕捉屏幕上的地图名称，返回匹配结果并展示详情与缩略图。

## 核心特性
- PySide6 图形界面：输入框 + 查询/清除按钮、滚动结果列表、详情面板（显示地图大图与完整信息）。
- 模糊搜索：复用 `ava-maps` 项目中的搜索策略，Python 侧使用 `rapidfuzz` 构建索引，可快速匹配 `xxx-xxx`、`xxx-xx-xxx` 格式的地图名称。
- 热键 OCR：在任意窗口下按快捷键即可截取鼠标上方矩形区域（以鼠标为底边中心），调用 `pytesseract` 识别文字后填入搜索框。
- 静态资源：`static/maps` 提供地图缩略图（`.webp/.png`），`static/assets` 包含箱子、资源、传送门等图标，用于结果列表与详情区展示。
- 数据模型：`maps/model.py` 定义 `MapMdoel`（包含 `tier`, `map_type`, `chests`, `dungeons`, `resources`, `brecilien` 等）。加载时会校验名称必须为纯小写英文 + `-`。

## 项目结构
```
Atlas/
├─ main.py                  # 程序入口
├─ maps/                    # 地图模型与数据加载
├─ static/                  # 图片与通用图标
└─ docs/plan/               # 规划文档（架构、模块、UI、搜索算法等）
```

更多实现细节可查看：
- `docs/plan/01_overview.md`：需求与技术选型。
- `docs/plan/02_module_design.md`：模块设计与数据说明。
- `docs/plan/03_ui_interaction.md`：界面与交互方案。
- `docs/plan/04_search_algorithm.md`：搜索算法及 `rapidfuzz` 集成流程。

## 地图数据来源
- https://github.com/lucioreyli/ava-maps
