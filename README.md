# Avalon Atlas

Avalon Atlas 是一个面向 Albion Online 阿瓦隆地图的 Windows 桌面查询工具。当前版本已经迁移到 Tauri v2 + Svelte 5 + Rust：前端负责搜索交互和结果展示，Rust 后端负责地图数据加载、模糊搜索、截图 OCR、全局热键和配置持久化。

## 当前能力

- 地图名模糊搜索：支持子序列匹配、字符高亮、相似字符容错，例如 `c4s0s` 可匹配 `casos-*`。
- 地图信息展示：显示等级、通道类型、箱子、洞穴、资源、布雷希恩入口等数据。
- 地图预览：鼠标悬停已选地图时显示 `public/static/maps/` 下的地图图片。
- 鼠标 OCR：默认 `Ctrl+Shift+Q`，截取鼠标上方区域并识别地图名。
- 框选 OCR：默认 `Ctrl+Shift+W`，打开透明遮罩窗口，拖拽选择屏幕区域后识别多个地图名。
- 热键设置：在应用内设置窗口录制热键，保存后立即重新注册。
- 窗口置顶：主界面可切换 always-on-top 状态。
- 多语言界面：内置中文和英文，可在设置窗口切换并持久化。
- 本地配置：首次运行自动生成 `config.json`，后续启动自动加载。

## 技术栈

- 前端：Svelte 5、TypeScript、Vite
- 桌面框架：Tauri v2
- 后端：Rust
- OCR：随应用打包的 Tesseract 可执行文件和 `eng.traineddata`
- 截图：`screenshots`
- 全局热键：`tauri-plugin-global-shortcut`

## 目录结构

```text
Avalon-Atlas/
├── .github/workflows/           # GitHub Actions 发布与构建流程
├── docs/                        # 设计、重构、发布和使用文档
├── src/                         # Svelte 前端
│   ├── App.svelte               # 主界面、热键事件、OCR 结果处理
│   ├── components/
│   │   ├── map/                 # 地图条目、地图信息展示
│   │   ├── overlay/             # 屏幕框选遮罩相关组件
│   │   ├── search/              # 搜索输入和候选结果
│   │   └── settings/            # 设置弹窗和语言切换
│   └── lib/
│       ├── i18n/                # 中英文词典和语言状态
│       ├── maps/                # 前端地图数据类型
│       └── tauri/               # 前端调用 Tauri command 的封装
├── src-tauri/                   # Rust / Tauri 后端
│   ├── src/
│   │   ├── commands/            # Tauri IPC 命令
│   │   ├── models/              # 配置和地图数据模型
│   │   ├── services/            # 搜索、OCR、热键服务
│   │   └── utils/               # 日志、截图、冻结画面、模糊匹配工具
│   ├── binaries/                # 打包用 Tesseract 和 tessdata
│   └── tauri.conf.json          # Tauri 构建和资源配置
├── public/static/data/maps.json # 地图数据
├── public/static/maps/          # 地图预览图，文件名对应地图 slug
├── public/static/assets/        # 箱子、洞穴、资源等图标
├── scripts/                     # 发布、清理和便携包脚本
├── index.html
├── region-selector.html         # 框选 OCR 遮罩页
├── package.json
├── package-lock.json            # npm 依赖锁定
└── vite.config.ts
```

当前主入口以根目录 `src/` 和 `src-tauri/` 为准。迁移过程副本和本地构建目录不参与当前应用入口。

### 忽略目录约定

`.gitignore` 将以下内容视为本地或生成内容：

- `node_modules/`、`dist/`、`build/`、`src-tauri/target/`、`target/`：依赖和构建产物。
- `*.log`、`debug/`、`logs/`：运行日志和调试输出。
- `.omc/`、`**/.omc/`：本地 agent 状态。
- `backend/`、`frontend/`、`resources/`：旧迁移副本或实验资源，已从主工作区清理。

`package-lock.json` 应提交以锁定 npm 依赖。`src-tauri/Cargo.lock` 也不再被忽略；这是桌面应用项目，建议在下一次整理提交时一并纳入版本控制以锁定 Rust 依赖。

## 快速开始

### 环境要求

- Windows 10/11 64 位
- Node.js 18+ 和 npm
- Rust stable toolchain
- Windows 平台构建 Tauri 时需要可用的 MSVC / Windows SDK 环境

### 安装依赖

```bash
npm install
```

### 开发运行

```bash
npm run tauri dev
```

Tauri 会启动 Vite 开发服务，端口固定为 `1420`。如果端口被占用，开发命令会失败，需要先释放该端口。

### 前端预览

```bash
npm run dev
```

这个命令只启动 Web 前端。涉及 Tauri IPC、OCR、全局热键、窗口置顶的功能需要用 `npm run tauri dev`。

### 构建

```bash
npm run tauri build
```

仅验证 Tauri 应用本体、不生成安装包时可运行：

```bash
npm run tauri build -- --no-bundle
```

`build/target/release/` 是 Cargo/Tauri 编译输出目录，不建议直接作为分发目录。编译后的可执行文件位于：

```text
build/target/release/avalon-atlas.exe
```

Vite 前端构建产物位于：

```text
build/frontend/
```

安装包或便携包输出位于：

```text
build/target/release/bundle/
build/portable/
```

### 便携分发包

生成可直接压缩分发的目录和 zip：

```bash
npm run package:portable
```

交付目录：

```text
build/portable/avalon-atlas-v2.0.0-portable/
```

该目录只包含运行需要的文件：

```text
avalon-atlas.exe
config.json
static/
binaries/
logs/
README.txt
```

同时会生成：

```text
build/portable/avalon-atlas-v2.0.0-portable.zip
```

## 验证命令

```bash
npm run check
npm run build
cargo test --manifest-path src-tauri/Cargo.toml
cargo build --manifest-path src-tauri/Cargo.toml --release
npm run tauri build -- --no-bundle
```

当前重构后的基线验证：

- `npm run check`：Svelte 类型检查通过
- `npm run build`：Vite 生产构建通过
- `cargo test --manifest-path src-tauri/Cargo.toml`：Rust 单元测试通过
- `cargo build --manifest-path src-tauri/Cargo.toml --release`：release 编译通过
- `npm run tauri build -- --no-bundle`：Tauri no-bundle 构建通过

## 使用说明

### 手动搜索

1. 在顶部搜索框输入地图名或片段，例如 `casos`、`ca-ai`、`c4s0s`。
2. 下拉列表展示匹配结果。
3. 点击结果项添加到已选地图列表。
4. 鼠标悬停已选项查看地图预览。
5. 点击已选项右侧删除按钮可移除该地图。

### 鼠标 OCR

1. 将鼠标放到游戏内地图名称下方。
2. 按下默认热键 `Ctrl+Shift+Q`。
3. 应用截取鼠标上方区域，运行 OCR，并把匹配到的地图加入列表。

截图区域默认逻辑：

```text
left = mouse_x - width / 2
top  = mouse_y - height - vertical_offset
```

也就是说鼠标位于截图矩形底边中心附近。

### 框选 OCR

1. 按下默认热键 `Ctrl+Shift+W`。
2. 屏幕出现透明遮罩。
3. 拖拽选择聊天框或包含地图名的区域。
4. 应用识别区域内文本，并尝试把多个地图名加入列表。

### 设置

主界面右上角设置按钮可修改：

- 鼠标 OCR 热键
- 框选 OCR 热键
- 界面语言（中文 / English）
- OCR 调试开关

保存后会写入 `config.json`，并立即重新注册全局热键。

## 配置文件

`config.json` 位于应用当前工作目录。缺失时会自动生成；缺少字段时会使用默认值补齐。

当前支持字段：

```json
{
  "mouse_hotkey": "ctrl+shift+q",
  "chat_hotkey": "ctrl+shift+w",
  "ocr_debug": true,
  "ocr_region": {
    "width": 600,
    "height": 80,
    "vertical_offset": 0
  },
  "always_on_top": false,
  "debounce_ms": 200,
  "language": "zh-CN"
}
```

字段说明：

- `mouse_hotkey`：鼠标 OCR 全局热键。
- `chat_hotkey`：框选 OCR 全局热键。
- `ocr_debug`：保留给 OCR 调试流程，默认开启。
- `ocr_region.width`：鼠标 OCR 截图宽度。
- `ocr_region.height`：鼠标 OCR 截图高度。
- `ocr_region.vertical_offset`：鼠标 OCR 截图区域向上的额外偏移。
- `always_on_top`：窗口置顶状态。
- `debounce_ms`：搜索防抖配置，当前前端搜索逻辑仍以组件实现为准。
- `language`：界面语言，当前支持 `zh-CN` 和 `en-US`。缺失或非法值会回退到 `zh-CN`。

热键字符串使用 `ctrl`、`shift`、`alt`、`super` 作为修饰键，例如：

```text
ctrl+shift+q
ctrl+alt+m
ctrl+super+w
```

## 数据和资源

### 地图数据

地图数据文件：

```text
public/static/data/maps.json
```

每条记录包含：

- `name`
- `tier`
- `type`
- `chests`
- `dungeons`
- `resources`
- `brecilien`

Rust 后端加载时会把原始 `type` 字段映射为前端使用的 `map_type`。

### 地图图片

地图预览图目录：

```text
public/static/maps/
```

图片文件名应和地图 slug 对应，例如：

```text
casos-aiagsum.webp
```

主界面加载 `.webp`。旧 `.png` 预览图体积较大，当前主工程不再保留。

### 打包资源

`src-tauri/tauri.conf.json` 会把以下资源加入 Tauri bundle：

```text
../public/static/data/maps.json -> static/data/maps.json
src-tauri/binaries/tesseract/   -> binaries/tesseract/
src-tauri/binaries/tessdata/    -> binaries/tessdata/
```

开发环境会从仓库路径读取数据；打包后会从 Tauri resource 目录读取。

## 常见问题

### 搜索没有结果

- 输入至少 2 个有效字符。
- 确认 `public/static/data/maps.json` 存在且 JSON 可解析。
- 尝试输入更长片段，例如从 `ca` 改为 `casos`。

### 地图类型显示为空或原始英文

- 确认后端返回字段为 `map_type`。
- 未在前端映射表中的类型会直接显示原始值。

### OCR 没有识别到地图

- 调整鼠标位置，让地图名完整落在鼠标上方截图区域。
- 增大 `ocr_region.width` 或 `ocr_region.height`。
- 调整 `ocr_region.vertical_offset`。
- 确认 `src-tauri/binaries/tesseract/tesseract.exe` 和 `src-tauri/binaries/tessdata/eng.traineddata` 存在。

### 热键不生效

- 检查热键是否被其他程序占用。
- 尝试换成其他组合键后保存。
- 以管理员身份运行可能改善部分游戏或全屏场景下的热键捕获。

### Tauri 构建提示版本不匹配

确保 npm 侧 `@tauri-apps/api`、`@tauri-apps/cli` 与 Rust 侧 Tauri 版本在同一 minor 系列。当前 npm 侧为 `2.10.1`，Rust lock 中 Tauri 为 `2.10.x`。

## 开发文档

- `docs/Tauri重构设计方案.md`
- `docs/plan/01_overview.md`
- `docs/plan/02_module_design.md`
- `docs/plan/03_ui_interaction.md`
- `docs/plan/04_search_algorithm.md`
- `docs/CHAT_OCR_GUIDE.md`
- `docs/产品化与打包发布规范.md`
- `docs/发布检查清单.md`

## 当前限制

- 当前 OCR 实现使用 Tesseract；README 不再声明 RapidOCR 已集成。
- 当前仓库未实现自动更新检查。
- 当前日志主要是控制台输出；README 不再声明文件日志轮转已实现。
- 跨平台能力来自 Tauri 技术栈，但当前验证重点是 Windows。

## 许可证和数据来源

本项目使用 MIT License。地图数据来源于 ava-maps 相关数据整理，静态资源与打包资源随项目一起发布。
