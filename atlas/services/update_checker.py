"""更新检查服务 - 从 GitHub Releases 检查新版本"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from ..logger import get_logger
from ..version import __version__

logger = get_logger(__name__)

# GitHub API 配置
GITHUB_REPO = "Pililink/Avalon-Atlas"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT = 10  # 秒


@dataclass(slots=True)
class UpdateInfo:
    """更新信息"""
    latest_version: str
    current_version: str
    download_url: str
    release_notes: str
    release_url: str

    @property
    def has_update(self) -> bool:
        """是否有可用更新"""
        return self._compare_versions(self.latest_version, self.current_version) > 0

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """
        比较版本号

        Returns:
            1 if v1 > v2
            0 if v1 == v2
            -1 if v1 < v2
        """
        def parse_version(v: str) -> tuple[int, ...]:
            # 移除 'v' 前缀并提取数字部分
            v = v.lstrip('v')
            # 提取版本号数字 (例如 "1.0.2-beta" -> "1.0.2")
            match = re.match(r'(\d+)\.(\d+)\.(\d+)', v)
            if match:
                return tuple(int(x) for x in match.groups())
            return (0, 0, 0)

        v1_tuple = parse_version(v1)
        v2_tuple = parse_version(v2)

        if v1_tuple > v2_tuple:
            return 1
        elif v1_tuple < v2_tuple:
            return -1
        else:
            return 0


class UpdateChecker:
    """更新检查器"""

    def __init__(self, current_version: str = __version__):
        self.current_version = current_version
        self._check_thread: Optional[threading.Thread] = None

    def check_update_async(self, callback: Callable[[Optional[UpdateInfo]], None]) -> None:
        """
        异步检查更新

        Args:
            callback: 检查完成后的回调函数，接收 UpdateInfo 或 None
        """
        if self._check_thread and self._check_thread.is_alive():
            logger.info("更新检查已在进行中，跳过本次请求")
            return

        def _worker():
            try:
                update_info = self._check_update()
                callback(update_info)
            except Exception as exc:
                logger.exception("更新检查失败: %s", exc)
                callback(None)

        self._check_thread = threading.Thread(target=_worker, name="update-checker", daemon=True)
        self._check_thread.start()

    def _check_update(self) -> Optional[UpdateInfo]:
        """
        检查更新（同步）

        Returns:
            UpdateInfo 如果成功获取信息，否则 None
        """
        logger.info("检查更新: 当前版本 %s", self.current_version)

        try:
            # 创建请求
            request = Request(
                GITHUB_API_URL,
                headers={
                    'User-Agent': f'Avalon-Atlas/{self.current_version}',
                    'Accept': 'application/vnd.github.v3+json'
                }
            )

            # 发送请求
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8'))

            # 解析响应
            latest_version = data.get('tag_name', '').lstrip('v')
            release_notes = data.get('body', '').strip()
            release_url = data.get('html_url', '')

            # 查找下载链接 - 优先选择 portable.zip
            download_url = ''
            assets = data.get('assets', [])
            for asset in assets:
                name = asset.get('name', '').lower()
                if 'portable' in name and name.endswith('.zip'):
                    download_url = asset.get('browser_download_url', '')
                    break

            # 如果没有 portable 版本，使用第一个资源
            if not download_url and assets:
                download_url = assets[0].get('browser_download_url', '')

            # 如果还是没有，使用 release 页面
            if not download_url:
                download_url = release_url

            if not latest_version:
                logger.warning("无法解析最新版本号")
                return None

            logger.info("最新版本: %s", latest_version)

            update_info = UpdateInfo(
                latest_version=latest_version,
                current_version=self.current_version,
                download_url=download_url,
                release_notes=release_notes[:500],  # 限制长度
                release_url=release_url
            )

            if update_info.has_update:
                logger.info("发现新版本: %s -> %s", self.current_version, latest_version)
            else:
                logger.info("当前已是最新版本")

            return update_info

        except HTTPError as exc:
            if exc.code == 404:
                logger.warning("GitHub Releases 未找到: %s", GITHUB_API_URL)
            else:
                logger.warning("HTTP 错误 %d: %s", exc.code, exc.reason)
            return None
        except URLError as exc:
            logger.warning("网络错误: %s", exc.reason)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("JSON 解析失败: %s", exc)
            return None
        except Exception as exc:
            logger.warning("更新检查异常: %s", exc)
            return None
