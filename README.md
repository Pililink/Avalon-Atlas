# Avalon-Online-Atlas

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

阿瓦隆地图查询桌面工具 - 支持智能搜索与 OCR 识别

[功能特性](#核心特性) • [快速开始](#快速开始) • [使用指南](#使用指南) • [配置说明](#配置说明) • [常见问题](#常见问题)

</div>

---

## 📖 简介

Avalon Atlas 是一款专为阿瓦隆在线（Albion Online）玩家设计的桌面端辅助工具，用于快速查询地图的箱子、资源、洞穴等详细信息。

支持两种查询方式：
- 🔍 **手动输入**：智能模糊搜索，支持拼写容错
- ⌨️ **热键 OCR**：游戏内一键截图识别地图名称

## ✨ 核心特性

### 🎯 智能搜索
- **子序列模糊匹配**：内置动态规划评分算法，即使输入不完整也能精准匹配
- **高亮显示**：搜索结果自动高亮匹配字符
- **实时预览**：鼠标悬停显示地图完整大图
- **快速排序**：按匹配度、地图等级智能排序

### 🖼️ OCR 识别
- **全局热键**：支持自定义快捷键（默认 `Ctrl+Shift+Q`）
- **智能矫正**：自动修正 OCR 常见识别错误（数字→字母）
- **双引擎支持**：RapidOCR（默认）或 Tesseract 可选
- **调试模式**：可保存截图用于排查识别问题

### 📊 数据展示
- **地图详情**：箱子数量、洞穴类型、资源分布、传送门数量
- **缩略图预览**：列表显示地图缩略图
- **等级标注**：T4/T6/T8 等级清晰标识
- **双击复制**：双击地图名称快速复制

### 🎨 用户界面
- **现代化设计**：基于 PySide6 (Qt6) 构建
- **响应式布局**：自适应窗口大小
- **深色主题**：护眼舒适的配色方案
- **无侵入性**：窗口置顶，不遮挡游戏

---

## 🚀 快速开始

### 系统要求

- **操作系统**: Windows 10/11 (64位)
- **内存**: 至少 4GB RAM
- **磁盘空间**: 约 500MB

### 下载与安装

#### 方式一：下载发行版（推荐）

1. 前往 [Releases](https://github.com/yourname/atlas/releases) 页面
2. 下载最新版本的 `AvalonAtlas-v1.0.0-portable.zip`
3. 解压到任意目录（建议路径不含中文）
4. 双击 `AvalonAtlas.exe` 启动

#### 方式二：从源码构建

```bash
# 克隆仓库
git clone https://github.com/yourname/atlas.git
cd atlas

# 安装依赖 (需要 Python 3.12+)
pip install -r requirements.txt

# 运行程序
python main.py

# 或构建可执行文件
python build.py
# 输出在 dist/AvalonAtlas/ 目录
```

### 首次运行

1. **自动生成配置**：首次运行会在程序目录生成 `config.json`
2. **设置热键**：点击"录制热键"按钮，按下想要的组合键（如 `Ctrl+Shift+Q`），然后点击"保存热键"
3. **测试搜索**：在搜索框输入地图名称（如 `casos`），查看结果

---

## 📚 使用指南

### 手动搜索

1. 在搜索框输入地图名称（支持部分拼写）
2. 程序自动显示匹配结果（最多 20 条）
3. 点击结果项添加到已选列表
4. 鼠标悬停在已选项上查看完整地图大图
5. 双击地图名称快速复制到剪贴板

**搜索技巧**：
- 输入 `cas` 可以匹配 `casos-aiagsum`
- 输入 `ca-ai` 可以匹配 `casos-aiagsum`
- 不区分大小写
- 支持拼写容错（如 `c4s0s` 会自动矫正为 `casos`）

### 热键 OCR

1. 确保热键已设置（状态栏显示当前热键）
2. 在游戏中，将鼠标移动到地图名称上方
3. 按下设置的热键（默认 `Ctrl+Shift+Q`）
4. 程序自动截取鼠标上方区域识别文字
5. 识别成功后自动添加到已选列表

**OCR 最佳实践**：
- 鼠标放在地图名称正下方（距离约 1-2 厘米）
- 确保地图名称清晰可见，无遮挡
- 避免在名称上有光标或高亮
- 如识别失败，可在 `debug/` 目录查看截图

### 热键录制

1. 点击"录制热键"按钮
2. 按下想要设置的组合键（如 `Ctrl+Alt+K`）
3. 程序自动捕获并显示在输入框
4. 点击"保存热键"确认
5. 配置自动保存到 `config.json`

**推荐组合键**：
- `Ctrl+Shift+Q`
- `Ctrl+Alt+M`
- `Ctrl+Shift+F`

---

## ⚙️ 配置说明

配置文件位于程序根目录的 `config.json`，支持以下选项：

```json
{
  "maps_data_path": "static/data/maps.json",  // 地图数据文件路径
  "static_root": "static",                     // 静态资源目录
  "hotkey": "ctrl+shift+q",                    // 全局热键
  "debounce_ms": 200,                          // 搜索防抖延迟(毫秒)
  "ocr_backend": "rapidocr",                   // OCR 引擎: rapidocr/tesseract/auto
  "ocr_region": {
    "width": 600,                              // 截图宽度
    "height": 60,                              // 截图高度
    "vertical_offset": 0                       // 垂直偏移量
  },
  "ocr_debug": false,                          // 是否保存 OCR 截图到 debug/
  "debug_dir": "debug"                         // 调试文件保存目录
}
```

### 配置项说明

#### OCR 引擎选择

- **`rapidocr`** (推荐): 无需额外安装，识别速度快
- **`tesseract`**: 需安装 Tesseract-OCR，准确率稍高
- **`auto`**: 优先 RapidOCR，失败时回退 Tesseract

#### OCR 区域调整

- `width`: 截图宽度，默认 600px（覆盖大部分地图名称）
- `height`: 截图高度，默认 60px（单行文本）
- `vertical_offset`: 向上偏移，默认 0（鼠标在底边中点）

如识别效果不佳，可尝试调整这些参数。

#### 调试模式

开启 `ocr_debug: true` 后，每次 OCR 会保存截图到 `debug/` 目录，文件名包含时间戳。可用于：
- 检查截图范围是否正确
- 排查 OCR 识别问题
- 调整 `ocr_region` 参数

---

## 🗂️ 项目结构

```
AvalonAtlas/
├── AvalonAtlas.exe           # 主程序
├── config.json               # 配置文件（自动生成）
├── static/                   # 静态资源目录
│   ├── data/
│   │   └── maps.json         # 地图数据（400+ 张地图）
│   ├── maps/                 # 地图预览图（.png/.webp）
│   └── assets/               # UI 图标资源
├── _internal/                # 运行时依赖（PyInstaller 打包）
└── debug/                    # OCR 调试截图（可选）
```

### 数据文件说明

#### `static/data/maps.json`
包含所有地图的详细信息：
- 名称、等级 (T4/T6/T8)
- 地图类型（王城/黑区/深层等 12 种）
- 箱子数量（蓝/绿/金箱、金王座）
- 洞穴数量（单人/蓝洞/金洞）
- 资源分布（石/木/矿/棉/皮）
- 传送门数量

#### `static/maps/`
地图预览图，命名格式：`地图名.png` 或 `地图名.webp`
- 示例：`casos-aiagsum.png`
- 支持 WebP 格式（体积更小）

---

## ❓ 常见问题

### 程序无法启动

**问题**：双击 exe 无反应或闪退
**解决**：
1. 检查是否被杀毒软件拦截（添加到白名单）
2. 确认系统为 Windows 10/11 64 位
3. 查看 `logs/` 目录是否有错误日志
4. 尝试以管理员身份运行

### 热键不生效

**问题**：按下热键无响应
**解决**：
1. 检查热键是否与其他软件冲突（如 QQ、微信）
2. 尝试更换其他组合键
3. 确认程序在后台运行（任务栏托盘）
4. 重启程序后重新设置热键

### OCR 识别失败

**问题**：热键触发后提示"未识别到有效文本"
**解决**：
1. 开启 `ocr_debug: true`，检查 `debug/` 目录截图
2. 确认鼠标位置在地图名称正下方
3. 调整 `ocr_region` 参数（增大 width 或 height）
4. 切换 OCR 引擎（`rapidocr` ↔ `tesseract`）
5. 确保地图名称清晰、无遮挡

### OCR 识别错误

**问题**：识别出的地图名不正确
**说明**：程序内置智能矫正，会自动修正常见错误：
- 数字 → 字母 (`0→o`, `1→l`, `5→s`)
- 特殊符号 → 连字符 (`_→-`)
- 模糊匹配已知地图名

如仍有问题：
1. 检查 `debug/` 截图是否包含完整地图名
2. 提交 Issue 附上截图，帮助改进算法

### 搜索无结果

**问题**：输入地图名但没有匹配结果
**解决**：
1. 检查输入长度（最少 2 个字符）
2. 尝试输入更多字符或部分拼写
3. 确认 `static/data/maps.json` 存在且未损坏
4. 查看日志是否有数据加载错误

### 配置文件丢失

**问题**：`config.json` 被删除或损坏
**解决**：
- 重新启动程序，会自动生成默认配置
- 或手动复制上述"配置说明"中的 JSON 内容

---

## 🔧 开发文档

- **架构设计**: 参见 `CLAUDE.md`
- **搜索算法**: 参见 `docs/plan/04_search_algorithm.md`
- **模块设计**: 参见 `docs/plan/02_module_design.md`
- **UI 交互**: 参见 `docs/plan/03_ui_interaction.md`

### 技术栈

- **GUI**: PySide6 (Qt 6.7+)
- **OCR**: RapidOCR / Tesseract
- **数据验证**: Pydantic
- **打包**: PyInstaller
- **热键**: keyboard / pynput
- **截图**: mss

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

### 第三方依赖

本项目使用以下开源库：
- **PySide6**: LGPL-3.0
- **RapidOCR**: Apache-2.0
- **PyInstaller**: GPL-2.0

完整依赖列表见 `pyproject.toml`。

### 数据来源

地图数据来源于 [ava-maps](https://github.com/lucioreyli/ava-maps)，感谢原作者的贡献。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 报告问题

如遇到问题，请提供：
1. 操作系统版本
2. 程序版本号
3. 错误截图或日志
4. 复现步骤

### 功能建议

欢迎在 [Issues](https://github.com/yourname/atlas/issues) 提出新功能建议。

---

## 🙏 致谢

- 地图数据提供：[lucioreyli/ava-maps](https://github.com/lucioreyli/ava-maps)
- 灵感来源：阿瓦隆在线玩家社区

---

<div align="center">

**如果这个工具对你有帮助，请给个 ⭐ Star 支持一下！**

</div>
