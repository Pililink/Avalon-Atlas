#!/bin/bash
# Avalon-Atlas 便携式打包脚本 (Bash 版本)

VERSION="${1:-2.0.0}"

echo "=== Avalon-Atlas 便携式打包 ==="
echo "版本: $VERSION"
echo ""

# 1. 构建 Release 版本
echo "[1/5] 构建 Release 版本..."
npm run tauri build

if [ $? -ne 0 ]; then
    echo "构建失败！"
    exit 1
fi

# 2. 创建打包目录
PACKAGE_DIR="./dist/portable/avalon-atlas-v${VERSION}-portable"
echo "[2/5] 创建打包目录: $PACKAGE_DIR"

rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# 3. 复制可执行文件
echo "[3/5] 复制可执行文件..."
EXE_PATH="./backend/target/release/avalon-atlas.exe"

if [ ! -f "$EXE_PATH" ]; then
    echo "错误: 找不到可执行文件 $EXE_PATH"
    exit 1
fi

cp "$EXE_PATH" "$PACKAGE_DIR/avalon-atlas.exe"
EXE_SIZE=$(du -h "$EXE_PATH" | cut -f1)
echo "  ✓ avalon-atlas.exe ($EXE_SIZE)"

# 4. 复制资源文件
echo "[4/5] 复制资源文件..."

# 复制 resources 目录
cp -r ./resources "$PACKAGE_DIR/resources"
echo "  ✓ resources/ (配置文件、模型文件、数据文件)"

# 生成默认 config.json（首次运行也会自动生成，这里提供可编辑模板）
cat > "$PACKAGE_DIR/config.json" << 'EOF'
{
  "mouse_hotkey": "ctrl+shift+q",
  "chat_hotkey": "ctrl+shift+w",
  "ocr_debug": true,
  "log_level": "info",
  "ocr_region": {
    "width": 650,
    "height": 75,
    "vertical_offset": 0,
    "horizontal_offset": 0
  },
  "always_on_top": false,
  "debounce_ms": 200,
  "selected_monitor": 0
}
EOF
echo "  ✓ config.json (默认配置模板)"

# 创建 README
cat > "$PACKAGE_DIR/README.txt" << 'EOF'
# Avalon-Atlas - 便携版

## 使用方法

1. 双击 avalon-atlas.exe 启动程序
2. 热键:
   - Ctrl+Shift+Q: 鼠标区域 OCR
   - Ctrl+Shift+W: 自定义区域 OCR

## 目录结构

- avalon-atlas.exe: 主程序
- config.json: 配置文件
- resources/: 运行时资源目录
  - data/: 地图数据 (maps.json)
  - models/: OCR 模型 (text-detection.rten, text-recognition.rten)

## 系统要求

- Windows 10/11 (64-bit)
- 至少 100 MB 可用磁盘空间

## 注意事项

- 首次运行可能需要管理员权限（注册全局热键）
- 确保 resources/models/ 目录下的模型文件完整
EOF

echo "  ✓ README.txt (使用说明)"

# 5. 创建压缩包
echo "[5/5] 创建压缩包..."
ZIP_PATH="./dist/portable/avalon-atlas-v${VERSION}-portable.zip"

rm -f "$ZIP_PATH"
cd "$PACKAGE_DIR/.." && zip -r "avalon-atlas-v${VERSION}-portable.zip" "avalon-atlas-v${VERSION}-portable" > /dev/null
cd - > /dev/null

ZIP_SIZE=$(du -h "$ZIP_PATH" | cut -f1)
echo "  ✓ $ZIP_PATH ($ZIP_SIZE)"

# 完成
echo ""
echo "=== 打包完成 ==="
echo "压缩包位置: $ZIP_PATH"
echo "解压后即可使用，无需安装"
