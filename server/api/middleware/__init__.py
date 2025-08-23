# 参考文档: doc/server_structure.md 中间件部分
# 中间件模块

from fastapi import FastAPI
from typing import Dict, Any

from .cors import setup_cors_middleware
from .logging import setup_logging_middleware  
from .security import setup_security_middleware


def setup_middleware(app: FastAPI, config: Dict[str, Any]):
    """
    设置所有中间件
    
    Args:
        app: FastAPI应用实例
        config: 配置字典
    """
    # 设置中间件（顺序很重要）
    setup_security_middleware(app, config)
    setup_logging_middleware(app, config)
    setup_cors_middleware(app, config)


__all__ = [
    "setup_middleware",
    "setup_cors_middleware",
    "setup_logging_middleware", 
    "setup_security_middleware"
]