"""构建 Avalon Atlas 可执行文件的脚本"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
import os


def get_version() -> str:
    """从 atlas/version.py 读取版本号"""
    version_file = Path(__file__).parent / "atlas" / "version.py"
    if not version_file.exists():
        print("⚠️  未找到 version.py，使用默认版本 0.0.0")
        return "0.0.0"

    namespace = {}
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return namespace.get("__version__", "0.0.0")


def clean_build() -> None:
    """清理旧的构建产物"""
    print("🧹 清理旧构建...")
    for path_str in ["build", "dist"]:
        path = Path(path_str)
        if path.exists():
            shutil.rmtree(path)
            print(f"   ✓ 已删除 {path_str}/")
    print()


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
        "--collect-all",
        "rapidocr_onnxruntime",
        "main.py",
    ]

    env = dict(**os.environ)
    env.setdefault("PYINSTALLER_CONFIG_DIR", str(project_root / "build"))
    env.setdefault("PYINSTALLER_BOOTLOADER_IGNORE_SIGNALS", "True")

    print("🔨 开始构建可执行文件...")
    print(f"   📌 图标: {icon_path}")
    print(f"   📌 模式: 无控制台窗口 (windowed)")
    process = subprocess.run(cmd, cwd=project_root, env=env)

    if process.returncode == 0:
        print("   ✓ 构建成功\n")
    else:
        print("   ✗ 构建失败\n")

    return process.returncode


def verify_build() -> bool:
    """验证构建产物是否完整"""
    print("🔍 验证构建产物...")

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
            print(f"   ✓ {file_path.relative_to(dist_dir)}")
        else:
            print(f"   ✗ 缺失: {file_path.relative_to(dist_dir)}")
            all_ok = False

    # 检查可执行文件大小
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"   ℹ️  可执行文件大小: {size_mb:.1f} MB")

    if all_ok:
        print("   ✅ 验证通过\n")
    else:
        print("   ❌ 验证失败\n")

    return all_ok


def create_portable_zip(version: str) -> None:
    """创建便携版 ZIP 压缩包"""
    print("📦 打包便携版...")

    dist_dir = Path("dist/AvalonAtlas")
    output_zip = Path(f"dist/AvalonAtlas-v{version}-portable")

    if not dist_dir.exists():
        print("   ✗ dist/AvalonAtlas 目录不存在\n")
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
        print(f"   ✓ 已创建: {zip_file.name} ({size_mb:.1f} MB)\n")
    except Exception as e:
        print(f"   ✗ 打包失败: {e}\n")


def show_summary(version: str) -> None:
    """显示构建摘要"""
    print("=" * 60)
    print(f"🎉 Avalon Atlas v{version} 构建完成!")
    print("=" * 60)
    print("\n📂 输出文件:")
    print(f"   - 可执行文件: dist/AvalonAtlas/AvalonAtlas.exe")

    zip_file = Path(f"dist/AvalonAtlas-v{version}-portable.zip")
    if zip_file.exists():
        print(f"   - 便携版包: {zip_file.name}")

    print("\n📝 下一步:")
    print("   1. 测试运行 dist/AvalonAtlas/AvalonAtlas.exe")
    print("   2. 检查热键和 OCR 功能是否正常")
    print(f"   3. 解压 {zip_file.name} 测试便携版")
    print()


def main() -> int:
    """主构建流程"""
    version = get_version()

    print()
    print("=" * 60)
    print(f"🚀 Avalon Atlas v{version} 构建脚本")
    print("=" * 60)
    print()

    # 1. 清理
    clean_build()

    # 2. 构建
    ret = build_executable()
    if ret != 0:
        print("❌ 构建失败，退出")
        return ret

    # 3. 验证
    if not verify_build():
        print("⚠️  验证失败，但仍继续打包")

    # 4. 打包便携版
    create_portable_zip(version)

    # 5. 显示摘要
    show_summary(version)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\n\n⚠️  构建已取消")
        exit_code = 130
    except Exception as e:
        print(f"\n\n❌ 构建过程出现错误: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1

    raise SystemExit(exit_code)
