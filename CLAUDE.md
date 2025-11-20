# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Avalon-Online-Atlas 是一个桌面端辅助工具,用于查询阿瓦隆地图的箱子、资源、洞穴等信息。基于 PySide6 构建 GUI,支持手动输入或热键 OCR 捕捉屏幕上的地图名称,返回匹配结果并展示详情。

## 开发环境配置

### 运行程序
```bash
python main.py
```

### 构建可执行文件
```bash
python build.py
```
使用 PyInstaller 打包,生成的可执行文件位于 `dist/AvalonAtlas/` 目录。

### 依赖项
- PySide6: Qt GUI 框架
- pytesseract / RapidOCR: OCR 识别引擎
- pydantic: 数据模型验证
- mss: 屏幕截图
- pynput / keyboard: 热键监听

## 架构设计

### 核心模块结构

```
atlas/
├── config.py           # 配置管理(加载/保存 config.json)
├── logger.py           # 日志配置
├── data/
│   ├── models.py       # MapRecord 数据模型
│   └── repository.py   # MapRepository 数据访问层
├── services/
│   ├── fuzzy_match.py      # 子序列匹配 + 动态规划评分算法
│   ├── search_service.py   # MapSearchService 搜索服务
│   ├── ocr_service.py      # OCR 识别与文本归一化
│   └── hotkey_service.py   # 热键监听服务
└── ui/
    ├── main_window.py      # 主窗口(输入/结果列表/详情面板)
    ├── widgets.py          # MapListItemWidget 等自定义组件
    └── resource_loader.py  # 静态资源加载器
```

### 数据模型 (`atlas/maps/model.py`)

地图数据结构使用 Pydantic 验证:
- `MapMdoel`: 包含 `name`、`tier (T4/T6/T8)`、`map_type`(12 种隧道类型)
- `Chests`: blue/green/highGold/lowGold 箱子计数
- `Dungeons`: solo/group/avalon 洞穴计数
- `Resources`: rock/wood/ore/fiber/hide 资源权重
- `brecilien`: 布雷希恩传送门数量

**重要约束**: 地图名称必须是纯小写英文 + `-` 组合(如 `casos-aiagsum`),用于静态资源映射。

### 搜索算法 (`atlas/services/fuzzy_match.py`)

实现了**子序列匹配 + 动态规划评分**算法:

1. **DP 状态**: `dp[i][j]` 表示查询字符串前 i 个字符匹配候选串前 j 个字符的最高得分
2. **评分规则**:
   - `BASE_MATCH_SCORE = 10.0`: 基础匹配分
   - `ADJACENT_BONUS = 14.0`: 连续字符奖励
   - `WORD_START_BONUS = 8.0`: 单词起始位置奖励(识别 `-/_/空格` 后字符)
   - `START_OF_STRING_BONUS = 4.0`: 字符串起始奖励
   - `GAP_PENALTY = 2.0`: 跨越间隙惩罚
3. **回溯**: 记录最优路径,返回 `MatchDetail(score, positions)`,其中 `positions` 用于 UI 高亮
4. **兜底策略**: 若 DP 无解,`_fallback_match` 提供前后缀/片段匹配

**性能**: O(N × M × L) 复杂度,400 条地图场景下毫秒级响应,配合 LRU 缓存(64 条)。

### OCR 服务 (`atlas/services/ocr_service.py`)

#### 识别流程
1. 按快捷键触发 → 鼠标上方矩形区域截图(`ocr_region` 配置)
2. 调用 RapidOCR 或 pytesseract 识别
3. 文本归一化 → 匹配已知地图名称

#### 归一化策略
- **字符修正**: 数字误识别转换(如 `0→o`、`1→l`)
- **格式标准化**: 提取 `A-Z-A-Z(-A-Z)?` 模式,转小写,移除特殊符号
- **模糊匹配**: 使用 `difflib.SequenceMatcher` 与已知地图 slug 匹配(阈值 0.8)
- **调试模式**: `ocr_debug: true` 时保存截图到 `debug/` 目录

#### 截图区域计算
默认以鼠标位置为中心,向上偏移形成矩形(鼠标位于底边中点):
- `left = center_x - width/2`
- `top = center_y - height - vertical_offset`
- `bottom = center_y - vertical_offset`

需处理多屏/DPI 缩放/边界裁剪,避免越界异常。

### 配置管理 (`atlas/config.py`)

首次运行自动生成 `config.json`:
```json
{
  "maps_data_path": "static/data/maps.json",
  "static_root": "static",
  "hotkey": "ctrl+shift+q",
  "debounce_ms": 200,
  "ocr_backend": "rapidocr",  // "tesseract" 或 "auto"
  "ocr_region": {
    "width": 600,
    "height": 60,
    "vertical_offset": 0
  },
  "ocr_debug": true,
  "debug_dir": "debug"
}
```

修改配置后可在 UI 中保存热键,或重启应用加载其他配置。

### UI 交互设计 (`atlas/ui/main_window.py`)

#### 组件布局
1. **热键设置区**: 输入框(只读) + 录制按钮 + 保存按钮
2. **搜索控制**: 输入框(节流 200ms) + 查询/清除按钮
3. **结果列表**: `QListWidget` 展示匹配地图(最多 20 条),支持:
   - 缩略图图标
   - 高亮匹配字符(红色加粗)
   - 双击复制地图名称
4. **详情预览**: 鼠标悬停在结果项上,右侧弹出完整地图大图

#### 关键交互
- **弹出列表**: 输入时自动显示在搜索框下方,点击选中后添加到已选列表
- **热键录制**: 线程安全捕获组合键,使用 `keyboard.read_hotkey()`,自动归一化格式
- **OCR 集成**: 热键触发 → OCR 识别 → 自动搜索 → 选择最佳匹配添加到列表
- **高亮渲染**: 使用 `_HighlightDelegate` + `QTextDocument` 渲染 HTML 高亮文本

#### 线程模型
- 主线程: Qt 事件循环
- OCR/热键监听: 后台线程,通过 `QtCore.Signal` 跨线程通信
- 关闭清理: `closeEvent` 中调用 `hotkey_service.stop()` 优雅停止

## 静态资源

### 目录结构
```
static/
├── assets/          # 通用图标(箱子/洞穴/资源/传送门等)
├── maps/            # 地图预览图(.png 和 .webp 双格式)
└── data/
    └── maps.json    # 地图数据源
```

### 资源加载策略
- 地图缩略图: 优先 `.webp` → `.png` → 占位图
- 文件命名: 严格遵循地图 `slug`(如 `casos-aiagsum.png`)
- 懒加载: 仅在需要时加载图片,找不到时记录日志

## 常见开发任务

### 添加新地图数据
1. 更新 `static/data/maps.json`,确保 `name` 符合命名规范
2. 添加对应的 `.png/.webp` 到 `static/maps/`
3. (可选)运行 `tools/generate_maps_json.py` 批量生成

### 调整搜索评分规则
修改 `atlas/services/fuzzy_match.py` 中的常量:
- `BASE_MATCH_SCORE`
- `ADJACENT_BONUS`
- `WORD_START_BONUS`
- `GAP_PENALTY`

### 切换 OCR 引擎
在 `config.json` 中设置 `ocr_backend`:
- `"rapidocr"`: 使用 RapidOCR(默认,无需额外安装)
- `"tesseract"`: 使用 pytesseract(需安装 Tesseract-OCR)
- `"auto"`: 优先 RapidOCR,失败回退 tesseract

### 调试 OCR 识别
1. 设置 `"ocr_debug": true`
2. 按热键触发 OCR
3. 检查 `debug/` 目录中的截图
4. 查看日志中的原始识别文本和归一化结果

## 编码规范要点

### 数据模型
- 所有地图相关类使用 Pydantic 验证
- `name` 字段必须符合 `^[a-z]+(-[a-z]+)+$` 正则

### 错误处理
- OCR/热键服务失败不应导致崩溃,记录日志并提示用户
- 配置加载失败时使用默认配置并写入文件
- 单个地图数据校验失败时跳过该条继续加载

### 性能优化
- 搜索结果缓存 LRU(64 条)
- 输入节流 200ms 避免频繁查询
- 图片懒加载

### UI 线程安全
- 后台线程使用 `QtCore.Signal` 通信
- `QtCore.QMetaObject.invokeMethod` 跨线程调用 Slot
- 避免直接从非主线程操作 UI 组件

## 关键依赖文档

- **搜索算法详细说明**: `docs/plan/04_search_algorithm.md`
- **模块设计文档**: `docs/plan/02_module_design.md`
- **UI 交互设计**: `docs/plan/03_ui_interaction.md`
- **需求与技术选型**: `docs/plan/01_overview.md`

## 外部数据源

地图数据来源于 https://github.com/lucioreyli/ava-maps,需保持数据格式兼容性。
