"""发布辅助脚本 - 创建版本标签并触发 GitHub Actions 自动发布"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def get_current_version() -> str:
    """从 atlas/version.py 读取当前版本号"""
    version_file = Path(__file__).parent / "atlas" / "version.py"
    if not version_file.exists():
        print("❌ 未找到 atlas/version.py")
        sys.exit(1)

    namespace = {}
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return namespace.get("__version__", "0.0.0")


def check_git_status() -> bool:
    """检查 Git 工作区状态"""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        print("❌ 无法检查 Git 状态，请确认是否在 Git 仓库中")
        return False

    if result.stdout.strip():
        print("⚠️  工作区有未提交的变更：")
        print(result.stdout)
        return False

    return True


def check_tag_exists(tag: str) -> bool:
    """检查标签是否已存在"""
    result = subprocess.run(
        ["git", "tag", "-l", tag],
        capture_output=True,
        text=True,
        check=False
    )

    return bool(result.stdout.strip())


def create_tag(version: str, message: str) -> bool:
    """创建 Git 标签"""
    tag = f"v{version}"

    if check_tag_exists(tag):
        print(f"⚠️  标签 {tag} 已存在")
        choice = input("是否删除旧标签并重新创建？(y/N): ").strip().lower()
        if choice == 'y':
            # 删除本地标签
            subprocess.run(["git", "tag", "-d", tag], check=False)
            # 删除远程标签
            subprocess.run(["git", "push", "origin", f":refs/tags/{tag}"], check=False)
            print(f"✓ 已删除旧标签 {tag}")
        else:
            print("❌ 操作已取消")
            return False

    # 创建标签
    result = subprocess.run(
        ["git", "tag", "-a", tag, "-m", message],
        check=False
    )

    if result.returncode != 0:
        print(f"❌ 创建标签失败")
        return False

    print(f"✓ 已创建标签 {tag}")
    return True


def push_tag(version: str) -> bool:
    """推送标签到远程仓库"""
    tag = f"v{version}"

    print(f"\n⚠️  准备推送标签到远程仓库，这将触发 GitHub Actions 自动发布")
    choice = input(f"确认推送标签 {tag}？(y/N): ").strip().lower()

    if choice != 'y':
        print("❌ 操作已取消")
        return False

    # 推送标签
    result = subprocess.run(
        ["git", "push", "origin", tag],
        check=True
    )

    if result.returncode != 0:
        print("❌ 推送标签失败")
        return False

    print(f"✓ 已推送标签 {tag} 到远程仓库")
    return True


def main():
    """主流程"""
    print()
    print("=" * 60)
    print("🚀 Avalon Atlas 发布脚本")
    print("=" * 60)
    print()

    # 1. 检查工作区状态
    print("📋 检查 Git 状态...")
    if not check_git_status():
        print("\n❌ 请先提交所有变更后再发布")
        print("   git add .")
        print('   git commit -m "Release vX.X.X"')
        sys.exit(1)
    print("✓ 工作区干净\n")

    # 2. 获取版本号
    version = get_current_version()
    print(f"📦 当前版本: {version}\n")

    # 3. 确认发布信息
    print("发布前检查清单：")
    print(f"  1. atlas/version.py 版本号已更新为 {version}")
    print(f"  2. CHANGELOG.md 已更新 [{version}] 部分")
    print(f"  3. pyproject.toml 版本号已更新为 {version}")
    print(f"  4. 所有变更已提交到 Git")
    print()

    choice = input("以上检查项是否都已完成？(y/N): ").strip().lower()
    if choice != 'y':
        print("\n❌ 请完成检查清单后再继续")
        sys.exit(1)

    # 4. 输入发布说明
    print()
    release_message = input(f"请输入发布说明（默认: Release v{version}）: ").strip()
    if not release_message:
        release_message = f"Release v{version}"

    # 5. 创建标签
    print()
    if not create_tag(version, release_message):
        sys.exit(1)

    # 6. 推送标签
    if not push_tag(version):
        print("\n💡 提示：标签已创建但未推送，可手动推送：")
        print(f"   git push origin v{version}")
        sys.exit(1)

    # 7. 完成
    print()
    print("=" * 60)
    print("✅ 发布流程已启动！")
    print("=" * 60)
    print()
    print("接下来：")
    print("  1. GitHub Actions 将自动构建应用")
    print("  2. 构建成功后自动创建 Release")
    print("  3. 便携版 ZIP 将自动上传到 Release")
    print()
    print(f"🔗 查看构建进度：")
    print(f"   https://github.com/<your-username>/atlas/actions")
    print()
    print(f"🎉 发布完成后，下载地址：")
    print(f"   https://github.com/<your-username>/atlas/releases/tag/v{version}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(130)
    except subprocess.CalledProcessError as e:
        print(f"\n\n❌ 命令执行失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
