# GitHub Actions 自动发布说明

本项目已配置 GitHub Actions 自动构建和发布流程。推送版本标签后，将自动构建 Windows 便携版并创建 Release。

---

## 🚀 快速开始

### 一键发布（推荐）

```bash
# 使用发布脚本自动处理整个流程
python scripts/release.py
```

脚本会引导你完成：
1. 检查工作区状态
2. 确认版本号
3. 创建并推送 Git 标签
4. 触发自动构建

### 手动发布

```bash
# 1. 更新版本号（atlas/version.py, pyproject.toml）
# 2. 更新 CHANGELOG.md
# 3. 提交变更
git add .
git commit -m "Release v1.0.1"

# 4. 创建标签（必须以 v 开头）
git tag -a v1.0.1 -m "Release v1.0.1"

# 5. 推送标签（触发 GitHub Actions）
git push origin v1.0.1
```

---

## 📦 自动构建流程

推送标签后，GitHub Actions 会自动执行以下步骤：

### 1️⃣ 环境准备
- ✅ 检出代码仓库
- ✅ 设置 Python 3.12 环境
- ✅ 安装项目依赖

### 2️⃣ 版本验证
- ✅ 对比 Git 标签与 `atlas/version.py` 版本号
- ✅ 确保版本号一致性

### 3️⃣ 构建应用
- ✅ 运行 `python build.py` 构建可执行文件
- ✅ 生成便携版 ZIP 压缩包

### 4️⃣ 质量检查
- ✅ 验证必需文件存在
- ✅ 检查文件大小合理性
- ✅ 列出构建产物清单

### 5️⃣ 创建发布
- ✅ 从 CHANGELOG.md 提取发布说明
- ✅ 创建 GitHub Release
- ✅ 上传便携版 ZIP
- ✅ 标记正式版或预发布版

---

## 🔍 查看构建状态

### 方法 1：GitHub Actions 页面

访问你的仓库 Actions 页面：
```
https://github.com/<your-username>/atlas/actions
```

### 方法 2：构建徽章（可选）

在 README.md 中添加：
```markdown
![Build Status](https://github.com/<your-username>/atlas/actions/workflows/release.yml/badge.svg)
```

---

## 📝 发布说明生成

工作流会自动从 `CHANGELOG.md` 提取当前版本的变更内容。

### CHANGELOG.md 格式要求

```markdown
## [1.0.1] - 2025-01-25

### 修复
- 修复 OCR 识别问题
- 修复热键冲突

### 新增
- 新增历史记录功能
```

**提示**：确保版本号格式为 `[版本号]`，方便自动提取。

---

## ⚙️ 工作流配置

配置文件位于：`.github/workflows/release.yml`

### 触发条件

```yaml
on:
  push:
    tags:
      - 'v*'  # 匹配 v1.0.0, v2.1.3-beta 等
```

### 预发布版本

标签名包含以下关键词时，会标记为预发布版：
- `alpha` - 内部测试版
- `beta` - 公开测试版
- `rc` - 候选发布版

示例：
```bash
git tag v1.0.0-beta.1    # 预发布版
git tag v1.0.0           # 正式版
```

### 构建平台

当前配置为 **Windows** 构建：
```yaml
runs-on: windows-latest
```

如需多平台支持，可配置矩阵构建：
```yaml
strategy:
  matrix:
    os: [windows-latest, macos-latest]
```

---

## 🐛 故障排除

### 问题 1：构建失败 - 版本号不一致

**错误信息**：
```
版本号不一致！请确保 git tag 与 atlas/version.py 中的版本号匹配。
```

**解决方案**：
1. 检查 `atlas/version.py` 中的 `__version__`
2. 确保与 Git 标签一致（不含 `v` 前缀）
3. 删除错误标签并重新创建

```bash
git tag -d v1.0.1
git push origin :refs/tags/v1.0.1
# 修复版本号后重新创建标签
```

### 问题 2：依赖安装失败

**错误信息**：
```
ERROR: Could not find a version that satisfies the requirement ...
```

**解决方案**：
1. 检查 `requirements.txt` 依赖版本
2. 确保依赖在 PyPI 可用
3. 考虑添加备用安装方案

### 问题 3：构建产物上传失败

**错误信息**：
```
Error: Resource not accessible by integration
```

**解决方案**：
1. 检查仓库 Settings → Actions → General
2. 确保 Workflow permissions 设置为 "Read and write permissions"
3. 或在工作流中添加 `permissions: contents: write`

### 问题 4：ZIP 文件未生成

**可能原因**：
- `build.py` 构建失败
- `dist/AvalonAtlas/` 目录不存在

**排查步骤**：
1. 查看 GitHub Actions 日志
2. 检查 "构建可执行文件" 步骤
3. 本地运行 `python build.py` 测试

---

## 🛠️ 自定义配置

### 修改构建选项

编辑 `.github/workflows/release.yml`：

```yaml
# 修改 Python 版本
env:
  PYTHON_VERSION: '3.12'  # 改为 '3.11' 等

# 修改构建超时
jobs:
  build-and-release:
    timeout-minutes: 30  # 默认 360 分钟
```

### 添加构建步骤

在 "构建可执行文件" 后添加自定义步骤：

```yaml
- name: 运行自定义测试
  run: python -m pytest tests/
```

### 修改 Release 内容

编辑工作流中的 "生成发布说明" 步骤，自定义发布说明模板。

---

## 📊 构建时间估算

典型构建时间（GitHub Actions）：

| 步骤 | 耗时 |
|------|------|
| 环境准备 | 1-2 分钟 |
| 安装依赖 | 2-3 分钟 |
| 构建应用 | 3-5 分钟 |
| 打包压缩 | 1-2 分钟 |
| 创建 Release | < 1 分钟 |
| **总计** | **约 8-13 分钟** |

**提示**：首次构建可能较慢（无缓存），后续构建会更快。

---

## 🔐 安全注意事项

### 1. 保护敏感信息

- ❌ 不要在工作流中硬编码密码、Token
- ✅ 使用 GitHub Secrets 存储敏感信息
- ✅ 使用 `GITHUB_TOKEN`（自动提供）

### 2. 权限最小化

工作流只需要以下权限：
```yaml
permissions:
  contents: write  # 创建 Release
```

### 3. 依赖安全

- 定期更新依赖版本
- 使用 Dependabot 监控漏洞
- 锁定关键依赖版本

---

## 📈 优化建议

### 1. 加速构建

**启用依赖缓存**：
```yaml
- name: 设置 Python
  uses: actions/setup-python@v5
  with:
    cache: 'pip'  # 缓存 pip 依赖
```

**使用 uv（更快的包管理器）**：
```yaml
- name: 安装依赖
  run: |
    pip install uv
    uv pip install -r requirements.txt
```

### 2. 并行构建

如需多平台支持：
```yaml
strategy:
  matrix:
    os: [windows-latest, macos-latest]
    python-version: ['3.12']
```

### 3. 构建缓存

缓存 PyInstaller 构建产物：
```yaml
- name: 缓存 PyInstaller
  uses: actions/cache@v4
  with:
    path: build/
    key: ${{ runner.os }}-pyinstaller-${{ hashFiles('**/*.py') }}
```

---

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/cn/actions)
- [工作流语法](https://docs.github.com/cn/actions/using-workflows/workflow-syntax-for-github-actions)
- [PyInstaller 文档](https://pyinstaller.org/en/stable/)
- [发布检查清单](./发布检查清单.md)

---

## 💡 提示

1. **首次配置**：推送第一个标签前，建议先在测试分支验证工作流
2. **调试技巧**：使用 `actions/upload-artifact` 上传中间产物调试
3. **版本管理**：遵循语义化版本规范，让 GitHub Actions 更好地识别预发布版

---

**祝自动发布顺利！** 🎉
