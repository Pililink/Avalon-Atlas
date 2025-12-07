"""构建 Avalon Atlas 可执行文件的脚本"""

from __future__ import annotations

import shutil
import subprocess
import sys
import os
from pathlib import Path

# 设置 UTF-8 编码（修复 GitHub Actions Windows 环境的编码问题）
if sys.platform == 'win32':
    import locale
    # 设置控制台编码为 UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'


def safe_print(*args, **kwargs):
    """安全打印函数，处理编码错误"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 如果 UTF-8 失败，移除所有非 ASCII 字符
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # 保留 ASCII 字符，替换其他字符
                safe_args.append(arg.encode('ascii', 'replace').decode('ascii'))
            else:
                safe_args.append(str(arg))
        print(*safe_args, **kwargs)


def get_version() -> str:
    """从 atlas/version.py 读取版本号"""
    version_file = Path(__file__).parent / "atlas" / "version.py"
    if not version_file.exists():
        safe_print("⚠️  未找到 version.py，使用默认版本 0.0.0")
        return "0.0.0"

    namespace = {}
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return namespace.get("__version__", "0.0.0")


def _get_qt_plugins_path() -> str | None:
    """获取 Qt 插件目录路径"""
    try:
        import PySide6
        pyside6_path = Path(PySide6.__file__).parent
        plugins_path = pyside6_path / "plugins"

        if plugins_path.exists():
            # 检查是否有 imageformats 插件
            imageformats = plugins_path / "imageformats"
            if imageformats.exists():
                safe_print(f"   📌 找到 Qt 插件目录: {plugins_path}")
                return str(plugins_path)

        safe_print("   ⚠️  未找到 Qt 插件目录，将依赖 PyInstaller 自动收集")
        return None
    except Exception as e:
        safe_print(f"   ⚠️  查找 Qt 插件失败: {e}")
        return None


def clean_build() -> None:
    """清理旧的构建产物"""
    safe_print("🧹 清理旧构建...")
    for path_str in ["build", "dist"]:
        path = Path(path_str)
        if path.exists():
            shutil.rmtree(path)
            safe_print(f"   ✓ 已删除 {path_str}/")
    safe_print()


def build_executable() -> int:
    """构建可执行文件"""
    project_root = Path(__file__).parent
    icon_path = project_root / "static" / "assets" / "icon.ico"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "AvalonAtlas",
        "--onedir",
        "--windowed",  # 关闭控制台窗口
        "--icon",
        str(icon_path),  # 设置应用图标
        "--add-data",
        f"static{os.pathsep}static",
        # 收集 PySide6 相关模块和插件
        "--collect-submodules",
        "PySide6.QtGui",
        "--collect-submodules",
        "PySide6.QtCore",
        "--collect-all",
        "PySide6",
        # 收集 OCR 依赖
        "--collect-all",
        "rapidocr_onnxruntime",
        # 确保包含 Qt 图片格式插件
        "--add-binary",
        f"{_get_qt_plugins_path()}/*{os.pathsep}PySide6/plugins" if _get_qt_plugins_path() else "",
        "main.py",
    ]

    # 过滤掉空字符串参数
    cmd = [arg for arg in cmd if arg]

    env = dict(**os.environ)
    env.setdefault("PYINSTALLER_CONFIG_DIR", str(project_root / "build"))
    env.setdefault("PYINSTALLER_BOOTLOADER_IGNORE_SIGNALS", "True")

    safe_print("🔨 开始构建可执行文件...")
    safe_print(f"   📌 图标: {icon_path}")
    safe_print(f"   📌 模式: 无控制台窗口 (windowed)")
    safe_print(f"   📌 Qt 插件: {'已包含' if _get_qt_plugins_path() else '依赖自动收集'}")
    process = subprocess.run(cmd, cwd=project_root, env=env)

    if process.returncode == 0:
        safe_print("   ✓ 构建成功\n")
    else:
        safe_print("   ✗ 构建失败\n")

    return process.returncode


def verify_build() -> bool:
    """验证构建产物是否完整"""
    safe_print("🔍 验证构建产物...")

    dist_dir = Path("dist/AvalonAtlas")
    exe_path = dist_dir / "AvalonAtlas.exe"
    internal_dir = dist_dir / "_internal"

    required_files = [
        exe_path,
        internal_dir / "static" / "data" / "maps.json",
        internal_dir / "static" / "maps",
        internal_dir / "static" / "assets",
    ]

    all_ok = True
    for file_path in required_files:
        if file_path.exists():
            safe_print(f"   ✓ {file_path.relative_to(dist_dir)}")
        else:
            safe_print(f"   ✗ 缺失: {file_path.relative_to(dist_dir)}")
            all_ok = False

    # 检查地图文件数量
    maps_dir = internal_dir / "static" / "maps"
    if maps_dir.exists():
        png_files = list(maps_dir.glob("*.png"))
        webp_files = list(maps_dir.glob("*.webp"))
        total_files = len(png_files) + len(webp_files)

        safe_print(f"   ℹ️  地图文件: {len(png_files)} PNG, {len(webp_files)} WebP (共 {total_files} 个)")

        # 期望至少有 700 个文件（400 PNG + 400 WebP，允许一些容错）
        if total_files < 700:
            safe_print(f"   ⚠️  地图文件数量不足 (期望 ~800，实际 {total_files})，请检查打包")
            all_ok = False
    else:
        safe_print(f"   ✗ 地图目录不存在")
        all_ok = False

    # 检查 Qt 插件
    qt_plugins_dir = internal_dir / "PySide6" / "plugins" / "imageformats"
    if qt_plugins_dir.exists():
        plugin_files = list(qt_plugins_dir.glob("*"))
        safe_print(f"   ✓ Qt 图片插件: {len(plugin_files)} 个")
    else:
        safe_print(f"   ⚠️  未找到 Qt 图片插件目录，图片加载可能失败")
        # 不标记为失败，因为 PyInstaller 可能以其他方式处理

    # 检查可执行文件大小
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        safe_print(f"   ℹ️  可执行文件大小: {size_mb:.1f} MB")

    if all_ok:
        safe_print("   ✅ 验证通过\n")
    else:
        safe_print("   ❌ 验证失败\n")

    return all_ok


def create_portable_zip(version: str) -> None:
    """创建便携版 ZIP 压缩包"""
    safe_print("📦 打包便携版...")

    dist_dir = Path("dist/AvalonAtlas")
    output_zip = Path(f"dist/AvalonAtlas-v{version}-portable")

    if not dist_dir.exists():
        safe_print("   ✗ dist/AvalonAtlas 目录不存在\n")
        return

    try:
        # 创建 zip 压缩包
        shutil.make_archive(
            str(output_zip),
            "zip",
            str(dist_dir.parent),
            "AvalonAtlas"
        )

        zip_file = output_zip.with_suffix(".zip")
        size_mb = zip_file.stat().st_size / 1024 / 1024
        safe_print(f"   ✓ 已创建: {zip_file.name} ({size_mb:.1f} MB)\n")
    except Exception as e:
        safe_print(f"   ✗ 打包失败: {e}\n")


def show_summary(version: str) -> None:
    """显示构建摘要"""
    safe_print("=" * 60)
    safe_print(f"🎉 Avalon Atlas v{version} 构建完成!")
    safe_print("=" * 60)
    safe_print("\n📂 输出文件:")
    safe_print(f"   - 可执行文件: dist/AvalonAtlas/AvalonAtlas.exe")

    zip_file = Path(f"dist/AvalonAtlas-v{version}-portable.zip")
    if zip_file.exists():
        safe_print(f"   - 便携版包: {zip_file.name}")

    safe_print("\n📝 下一步:")
    safe_print("   1. 测试运行 dist/AvalonAtlas/AvalonAtlas.exe")
    safe_print("   2. 检查热键和 OCR 功能是否正常")
    safe_print(f"   3. 解压 {zip_file.name} 测试便携版")
    safe_print()


def main() -> int:
    """主构建流程"""
    version = get_version()

    safe_print()
    safe_print("=" * 60)
    safe_print(f"🚀 Avalon Atlas v{version} 构建脚本")
    safe_print("=" * 60)
    safe_print()

    # 1. 清理
    clean_build()

    # 2. 构建
    ret = build_executable()
    if ret != 0:
        safe_print("❌ 构建失败，退出")
        return ret

    # 3. 验证
    if not verify_build():
        safe_print("⚠️  验证失败，但仍继续打包")

    # 4. 打包便携版
    create_portable_zip(version)

    # 5. 显示摘要
    show_summary(version)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        safe_print("\n\n⚠️  构建已取消")
        exit_code = 130
    except Exception as e:
        safe_print(f"\n\n❌ 构建过程出现错误: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1

    raise SystemExit(exit_code)
