# 参考文档: doc/server_structure.md 中间件部分
# CORS中间件配置

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any


def setup_cors_middleware(app: FastAPI, config: Dict[str, Any]):
    """
    设置CORS中间件
    
    Args:
        app: FastAPI应用实例
        config: 配置字典
    """
    cors_config = config.get('cors', {})
    
    # 默认CORS配置
    default_origins = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # 生产环境添加实际域名
    if config.get('app', {}).get('debug', False) is False:
        default_origins.extend([
            "https://pangruitao.com",
            "https://us.pangruitao.com"
        ])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get('allowed_origins', default_origins),
        allow_credentials=cors_config.get('allow_credentials', True),
        allow_methods=cors_config.get('allowed_methods', ["*"]),
        allow_headers=cors_config.get('allowed_headers', ["*"]),
    )