# 参考文档: doc/server_structure.md
# 日志配置管理工具

import logging
import logging.handlers
import os
from typing import Dict, Any

def _parse_size(size_str: str) -> int:
    """解析文件大小字符串，如 '10MB' -> 10485760"""
    size_str = size_str.upper()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)

def setup_logging(config: Dict[str, Any]):
    """
    根据配置设置日志系统
    参考文档: doc/server_structure.md - utils/logger.py
    """
    log_config = config.get('logging', {})
    
    # 创建日志目录
    log_dir = os.path.dirname(log_config.get('file_path', 'logs/app.log'))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # 配置根日志器
    logger = logging.getLogger()
    
    # 清除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
    
    # 格式化器
    formatter = logging.Formatter(log_config.get('format', 
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_config.get('file_enabled', True):
        file_path = log_config.get('file_path', 'logs/app.log')
        max_file_size = _parse_size(log_config.get('max_file_size', '10MB'))
        backup_count = log_config.get('backup_count', 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logging.info(f"日志系统初始化完成，级别: {log_config.get('level', 'INFO')}")

def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称
    
    Returns:
        日志器实例
    """
    return logging.getLogger(name)