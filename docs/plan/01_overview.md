# 游戏地图信息查询工具方案概述

## 需求要点
- 提供桌面 GUI，包含输入框、查询按钮、清除按钮、查询结果列表与当前选中地图展示区。
- 地图名命名规则 `xxx-xxx`、`xxx-xx-xxx`，需支持模糊匹配：前后三个字符组合、各段首字符/中间字符组合等。
- 支持热键触发 OCR：截取鼠标位置附近固定区域、识别文本、自动填入输入框并执行查询。
- 支持查询历史与选中结果在下方详细展示。

## 技术选择
- **语言/运行时**：Python 3.10+（方便快速迭代、OCR 库支持较好）。
- **GUI 框架**：PySide6（Qt for Python，跨平台、原生控件，易于自定义布局；如需 LGPL 可换 PyQt）。
- **数据管理**：使用本地 JSON/SQLite 存储地图信息与别名；首期直接加载 JSON 列表即可。
- **OCR**：pytesseract + Tesseract OCR（离线、效果稳定）；截图依赖 Pillow + mss。后续可扩展 paddleocr。
- **热键监听**：使用 keyboard 库（Windows 需管理员权限，跨平台可考虑 pynput）。
- **日志与配置**：Python logging + pydantic BaseSettings 或简单的 YAML/JSON。

## 项目结构草案
```
Atlas/
├─ main.py                # 程序入口，负责解析 CLI、启动 GUI
├─ atlas/
│  ├─ __init__.py
│  ├─ ui/
│  │  ├─ main_window.py   # Qt 主窗口定义
│  │  └─ widgets.py       # 如果需要自定义控件
│  ├─ data/
│  │  ├─ repository.py    # 地图数据加载、模糊搜索
│  │  └─ models.py        # MapInfo 数据类/结构
│  ├─ services/
│  │  ├─ search_service.py
│  │  ├─ ocr_service.py
│  │  └─ hotkey_service.py
│  └─ config.py           # 全局设置(截屏范围、热键等)
├─ assets/maps.json       # 地图基础数据
├─ requirements.txt / pyproject.toml
└─ docs/                  # 设计及规划
```

## 关键流程
1. 启动程序 → 加载配置/地图数据 → 初始化 GUI。
2. 用户输入或 OCR 触发 → 调用 SearchService 模糊匹配 → 更新结果列表。
3. 用户选中结果 → 在详情面板显示地图全名/附加信息 → 可复制。
4. 热键服务常驻后台：监听快捷键 → 截屏 → OCR → 将文本发布到 GUI 线程。
