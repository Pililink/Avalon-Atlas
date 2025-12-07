# 修复打包后图片显示黑色问题

## 问题描述

打包后的程序在其他设备上运行时，地图缩略图显示为黑色方块，而不是正常的地图预览图。

## 根本原因

1. **Qt 图片格式插件缺失**：PyInstaller 默认打包时可能没有包含 Qt 的图片格式插件（特别是 WebP 格式支持）
2. **资源打包不完整**：某些情况下静态资源文件可能没有被完全打包到 `_internal/static/` 目录

## 解决方案

### 修改内容

#### 1. `build.py` - 改进 PyInstaller 配置

**新增功能：**
- 添加 `_get_qt_plugins_path()` 函数，自动检测并包含 Qt 插件目录
- 添加 `--collect-submodules PySide6.QtGui` 和 `--collect-submodules PySide6.QtCore` 参数
- 添加 `--collect-all PySide6` 参数，确保完整打包 PySide6
- 添加 `--add-binary` 参数，显式包含 Qt 图片格式插件

**改进验证：**
- 验证地图文件数量（PNG + WebP 应该约 800 个）
- 验证 Qt 图片插件目录是否存在
- 输出详细的文件统计信息

#### 2. `atlas/ui/resource_loader.py` - 添加详细日志

**新增功能：**
- 初始化时输出 `static_root` 路径和文件统计
- 图片加载时输出详细的调试信息
- 区分"文件不存在"和"文件存在但加载失败"两种情况

**日志输出示例：**
```
ResourceLoader 初始化 - static_root: E:\src\Avalon-Atlas\_internal\static
  - static_root 存在: True
  - maps 目录存在: True
  - 找到 400 个 PNG 文件, 400 个 WebP 文件
```

## 使用方法

### 检查 Qt 插件（可选）

在构建前，可以先检查当前环境的 Qt 插件是否正常：

```bash
# 使用 uv 运行检查脚本
uv run python tools/check_qt_plugins.py
```

预期输出应该显示：
```
✅ 所有必需的图片格式都支持
```

### 重新构建程序

```bash
# 使用 uv 运行构建脚本
uv run python build.py
```

或者直接使用 python（如果已激活虚拟环境）：
```bash
python build.py
```

构建过程会显示详细信息：
```
🔨 开始构建可执行文件...
   📌 图标: static\assets\icon.ico
   📌 模式: 无控制台窗口 (windowed)
   📌 Qt 插件: 已包含
   📌 找到 Qt 插件目录: C:\...\PySide6\plugins
```

### 验证构建结果

构建完成后，验证环节会检查：
```
🔍 验证构建产物...
   ✓ AvalonAtlas.exe
   ✓ _internal\static\data\maps.json
   ✓ _internal\static\maps
   ✓ _internal\static\assets
   ℹ️  地图文件: 400 PNG, 400 WebP (共 800 个)
   ✓ Qt 图片插件: 8 个
   ℹ️  可执行文件大小: 123.4 MB
   ✅ 验证通过
```

### 诊断问题

如果打包后仍然出现黑色图片，查看日志文件：

1. **检查资源路径**：启动程序后查看日志，确认 `static_root` 路径正确
2. **检查文件统计**：确认找到的文件数量符合预期（800 个）
3. **查看加载警告**：如果看到"文件存在但加载失败"，说明是 Qt 插件问题

## 预期效果

修复后：
- ✅ 地图缩略图正常显示
- ✅ WebP 和 PNG 格式都能正确加载
- ✅ 详细的日志便于问题诊断
- ✅ 构建验证更加完善

## 技术细节

### PyInstaller 参数说明

| 参数 | 作用 |
|------|------|
| `--collect-submodules PySide6.QtGui` | 收集 Qt GUI 相关子模块 |
| `--collect-submodules PySide6.QtCore` | 收集 Qt Core 相关子模块 |
| `--collect-all PySide6` | 收集 PySide6 所有依赖 |
| `--add-binary` | 显式添加 Qt 插件二进制文件 |

### Qt 图片格式插件

Qt 的 `QPixmap` 需要以下插件来支持不同图片格式：
- `qjpeg.dll` - JPEG 支持
- `qpng.dll` - PNG 支持
- `qwebp.dll` - WebP 支持
- `qgif.dll` - GIF 支持

这些插件位于 `PySide6/plugins/imageformats/` 目录。

## 后续建议

1. **测试多种环境**：在不同 Windows 版本和配置上测试
2. **监控日志**：关注用户反馈的日志信息
3. **备选方案**：如果 WebP 仍有问题，可考虑只使用 PNG 格式

## 相关文件

- `build.py` - 构建脚本（已修改）
- `atlas/ui/resource_loader.py` - 资源加载器（已添加日志）
- `atlas/config.py` - 配置管理（路径配置）

## 版本历史

- 2025-12-07: 修复 Qt 插件打包问题，添加详细日志和验证
