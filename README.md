# Avalon-Online-Atlas

## 简介
桌面端辅助工具，用于查询阿瓦隆地图的箱子、资源、洞穴等信息。支持手动输入或热键 OCR 捕捉屏幕上的地图名称，返回匹配结果并展示缩略图/详情。

## 核心特性
- **PySide6 图形界面**：输入框（含查询/清除按钮）、滚动结果列表及详情面板，可快速浏览地图信息。
- **子序列模糊搜索**：内置“子序列匹配 + 动态规划评分”算法，依据首字母、单词边界、连续匹配等特征加权排序，同时输出匹配索引用于 UI 高亮；兜底策略会匹配前后缀或片段，保证始终有结果。
- **热键 OCR**：在任意窗口下按快捷键即可截取鼠标上方矩形区域，调用 `pytesseract`（或 RapidOCR）识别文字并自动触发搜索。
- **静态资源**：`static/maps` 提供地图缩略图，`static/assets` 包含箱子/资源等图标，用于列表和详情展示。
- **统一数据模型**：`maps/model.py` 描述 `tier`、`map_type`、`chests`、`dungeons`、`resources`、`brecilien` 等字段，读取时会校验名称格式（小写 + `-`）。

## 配置
首次运行若根目录不存在 `config.json`，程序会自动写入一份默认配置（包含 `hotkey`、OCR 区域等字段）。只需修改该文件即可调整热键，例如：
```json
{
  "hotkey": "ctrl+alt+k"
}
```
保存后重启应用即可生效。

## 项目结构
```
Atlas/
├─ main.py                  # 程序入口
├─ maps/                    # 地图模型与数据加载
├─ static/                  # 图片/图标资源
└─ docs/plan/               # 需求、模块、UI、搜索算法等规划
```

## 更多文档
- `docs/plan/01_overview.md`：需求与技术选型
- `docs/plan/02_module_design.md`：模块拆分及数据说明
- `docs/plan/03_ui_interaction.md`：界面与交互设计
- `docs/plan/04_search_algorithm.md`：搜索算法（子序列匹配 + 动态规划评分）与回退策略

## 地图数据来源
- https://github.com/lucioreyli/ava-maps
