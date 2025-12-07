#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 Qt 图片格式插件是否可用"""

from pathlib import Path
import sys
import os

# 设置 UTF-8 编码
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'


def check_pyside6_plugins():
    """检查 PySide6 插件"""
    print("=" * 60)
    print("Qt 插件检查工具")
    print("=" * 60)
    print()

    try:
        import PySide6
        from PySide6 import QtGui, QtWidgets

        pyside6_path = Path(PySide6.__file__).parent
        print(f"✓ PySide6 安装路径: {pyside6_path}")

        # 检查插件目录
        plugins_path = pyside6_path / "plugins"
        if plugins_path.exists():
            print(f"✓ 插件目录存在: {plugins_path}")

            # 检查 imageformats 插件
            imageformats_path = plugins_path / "imageformats"
            if imageformats_path.exists():
                print(f"✓ 图片格式插件目录存在: {imageformats_path}")
                print()
                print("找到的图片格式插件:")
                plugins = sorted(imageformats_path.glob("*"))
                for plugin in plugins:
                    print(f"  - {plugin.name}")
                print()
            else:
                print(f"✗ 图片格式插件目录不存在")
                return False
        else:
            print(f"✗ 插件目录不存在")
            return False

        # 测试图片格式支持
        print("测试图片格式支持:")
        app = QtWidgets.QApplication(sys.argv)

        # 获取支持的图片格式
        supported_read = [fmt.data().decode() for fmt in QtGui.QImageReader.supportedImageFormats()]
        supported_write = [fmt.data().decode() for fmt in QtGui.QImageWriter.supportedImageFormats()]

        print(f"  支持读取的格式: {', '.join(sorted(supported_read))}")
        print(f"  支持写入的格式: {', '.join(sorted(supported_write))}")
        print()

        # 检查关键格式
        required_formats = ['png', 'webp', 'jpg', 'jpeg']
        missing_formats = []

        for fmt in required_formats:
            if fmt in supported_read:
                print(f"  ✓ {fmt.upper()} 格式支持")
            else:
                print(f"  ✗ {fmt.upper()} 格式不支持")
                missing_formats.append(fmt)

        print()
        if missing_formats:
            print(f"⚠️  缺少以下格式支持: {', '.join(missing_formats)}")
            print("   这可能导致某些图片无法加载")
            return False
        else:
            print("✅ 所有必需的图片格式都支持")
            return True

    except ImportError as e:
        print(f"✗ PySide6 未安装或导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 检查过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    success = check_pyside6_plugins()
    print()
    print("=" * 60)
    if success:
        print("✅ Qt 插件检查通过，图片加载应该正常工作")
    else:
        print("❌ Qt 插件检查失败，可能会出现图片加载问题")
    print("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
