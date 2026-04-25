# Avalon Atlas

[English](README.en.md)

[![Release](https://img.shields.io/github/v/release/Pililink/Avalon-Atlas?label=release)](https://github.com/Pililink/Avalon-Atlas/releases)
[![Release Build](https://github.com/Pililink/Avalon-Atlas/actions/workflows/release.yml/badge.svg)](https://github.com/Pililink/Avalon-Atlas/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tauri](https://img.shields.io/badge/Tauri-v2-24C8DB)](https://tauri.app/)
[![Svelte](https://img.shields.io/badge/Svelte-5-FF3E00)](https://svelte.dev/)

Avalon Atlas 是一个轻量的 Windows 桌面助手，用于查询 Albion Online 阿瓦隆道路地图。它适合放在游戏窗口旁边，提供快速地图搜索，并支持通过 OCR 热键从屏幕上读取地图名称。

当前应用基于 Tauri v2、Svelte 5、TypeScript 和 Rust 构建。

> 这是 Albion Online 的非官方社区工具。Avalon Atlas 不需要游戏账号凭据，OCR 识别在本地运行。

## 截图

![Avalon Atlas compact in-game assistant panel](docs/assets/avalon-atlas-panel.png)

## 功能

- 快速模糊搜索阿瓦隆地图名称，支持容错和子序列匹配。
- 紧凑的游戏内助手风格界面，包含已选地图列表和地图预览。
- 展示地图等级、路线类型、宝箱、地下城、资源和布雷西林入口信息。
- 鼠标 OCR 热键：读取鼠标附近的地图名称。
- 区域 OCR 热键：框选屏幕区域并识别多个地图名称。
- 可自定义全局热键。
- 窗口置顶模式。
- 中文和英文界面。
- Windows 便携版内置 Tesseract OCR 运行时。

## 下载

从 GitHub Releases 下载最新 Windows 便携包：

https://github.com/Pililink/Avalon-Atlas/releases

下载 `avalon-atlas-v<version>-portable.zip`，解压后运行 `avalon-atlas.exe`。

便携包包含：

```text
avalon-atlas.exe
config.json
static/
binaries/
logs/
README.txt
```

日志会写入可执行文件旁边的 `logs/` 目录。

## 使用

### 搜索

在搜索框输入地图名称的一部分，然后从结果列表中选择地图。已选地图会保留在列表中，便于快速对比；鼠标悬停在已选地图上时会显示预览图。

### 鼠标 OCR

默认热键：`Ctrl+Shift+Q`

把鼠标移动到游戏里的地图图标上，等地图名称提示框弹出后按下热键。Avalon Atlas 会截取鼠标附近的一小块区域，识别提示框中的文本，并且只在结果足够可信时选择匹配的已知地图。

### 区域 OCR

默认热键：`Ctrl+Shift+W`

按下热键后，拖拽选择包含地图名称的屏幕区域，然后松开鼠标。应用会识别选区内的文本，并把匹配到的地图加入列表。

适用场景包括聊天记录、截图、网页或游戏内文本区域，适合一次处理多个地图名。

### 设置

从应用工具栏打开设置，可修改：

- 鼠标 OCR 热键
- 区域 OCR 热键
- 界面语言
- OCR 调试图片保存

设置会保存到 `config.json`。

## 开发

### 环境要求

- Windows 10/11 64 位
- Node.js 22 或更新版本
- Rust stable 工具链
- 用于 Tauri 构建的 Microsoft C++ Build Tools / Windows SDK

### 安装依赖

```bash
npm install
```

### 运行桌面应用

```bash
npm run tauri dev
```

Tauri 会在 `http://localhost:1420` 启动 Vite 开发服务器。

### 仅运行前端

```bash
npm run dev
```

仅前端模式适合 UI 开发。Tauri IPC、OCR、全局热键和窗口置顶行为需要通过 `npm run tauri dev` 测试。

### 检查

```bash
npm run check
cargo test --manifest-path src-tauri/Cargo.toml
```

### 构建

构建 Tauri 应用但不生成安装包：

```bash
npm run tauri build -- --no-bundle
```

主要构建产物：

```text
build/frontend/
build/target/release/avalon-atlas.exe
```

创建便携版目录和压缩包：

```bash
npm run package:portable
```

便携版输出：

```text
build/portable/avalon-atlas-v<version>-portable/
build/portable/avalon-atlas-v<version>-portable.zip
```

## 发布

推送 `v*` 标签时，GitHub Actions 会构建并发布 Windows 便携版。

```bash
git tag v2.0.1
git push origin v2.0.1
```

标签版本必须和以下文件一致：

- `package.json`
- `src-tauri/tauri.conf.json`
- `src-tauri/Cargo.toml`

发布工作流会安装依赖、运行前端检查、打包便携版、验证包内容，并把 zip 上传到 GitHub Releases。

## 项目结构

```text
Avalon-Atlas/
├── .github/workflows/      # CI 和发布工作流
├── docs/                   # 设计和维护说明
├── public/static/          # 地图数据、预览图和 UI 资源
├── scripts/                # 便携版打包脚本
├── src/                    # Svelte 前端
├── src-tauri/              # Rust/Tauri 后端
├── index.html
├── package.json
└── vite.config.ts
```

重要路径：

- `public/static/data/maps.json`：地图元数据。
- `public/static/maps/`：地图预览图。
- `src/lib/i18n/`：中文和英文界面文案。
- `src-tauri/binaries/tesseract/`：内置 Tesseract 运行时。
- `src-tauri/binaries/tessdata/`：内置 OCR 语言数据。
- `src-tauri/src/services/`：搜索、OCR、热键和辅助服务。

更多维护说明见 [docs/](docs/README.md)。

## 配置

缺少 `config.json` 时应用会自动创建。默认配置为：

```json
{
  "mouse_hotkey": "ctrl+shift+q",
  "chat_hotkey": "ctrl+shift+w",
  "ocr_debug": true,
  "ocr_region": {
    "width": 590,
    "height": 30,
    "vertical_offset": 50
  },
  "always_on_top": false,
  "debounce_ms": 200,
  "language": "zh-CN"
}
```

支持的语言为 `zh-CN` 和 `en-US`。

## 贡献

欢迎提交 issue 和 pull request。提交前请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

代码变更请保持范围聚焦，并在提交前运行相关检查：

```bash
npm run check
cargo test --manifest-path src-tauri/Cargo.toml
```

发布或打包相关变更还需要验证：

```bash
npm run package:portable
```

## 免责声明

Avalon Atlas 是非官方社区工具，不隶属于 Sandbox Interactive 或 Albion Online，也未获得其认可或赞助。

请负责任地使用 OCR 和全局热键，并遵守运行环境、软件和游戏的相关规则。

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE)。
