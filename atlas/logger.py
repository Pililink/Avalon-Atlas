from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


def configure_logging(level: int = logging.INFO, log_file: str | Path | None = None) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别
        log_file: 日志文件路径，默认为 debug/avalon_atlas.log
    """
    if logging.getLogger().handlers:
        return

    # 默认日志文件路径（使用 debug 目录）
    if log_file is None:
        log_dir = Path("debug")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "avalon_atlas.log"
    else:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（使用 RotatingFileHandler 防止日志文件过大）
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 记录日志系统初始化信息
    logging.info("日志系统已初始化，日志文件: %s", log_file)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name)
