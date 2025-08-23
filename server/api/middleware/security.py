# 参考文档: doc/server_structure.md 中间件部分
# 安全中间件

from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def setup_security_middleware(app: FastAPI, config: Dict[str, Any]):
    """
    设置安全中间件
    
    Args:
        app: FastAPI应用实例
        config: 配置字典
    """
    
    security_config = config.get('security', {})
    
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # 添加安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 仅在HTTPS下设置安全Cookie和HSTS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
    
    # 请求大小限制
    max_request_size = security_config.get('max_request_size', 1024 * 1024)  # 1MB默认
    
    @app.middleware("http")
    async def limit_request_size(request: Request, call_next):
        # 检查Content-Length
        content_length = request.headers.get('content-length')
        if content_length:
            content_length = int(content_length)
            if content_length > max_request_size:
                logger.warning(f"Request size {content_length} exceeds limit {max_request_size}")
                raise HTTPException(status_code=413, detail="Request entity too large")
        
        return await call_next(request)
    
    # IP访问频率限制（简单实现）
    request_counts = {}
    rate_limit = security_config.get('rate_limit', 100)  # 每分钟100请求
    
    @app.middleware("http") 
    async def rate_limiting(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        # 简单的内存计数器（生产环境应使用Redis）
        current_time = int(time.time() / 60)  # 分钟级别
        key = f"{client_ip}:{current_time}"
        
        if key in request_counts:
            request_counts[key] += 1
        else:
            request_counts[key] = 1
            
        # 清理旧的计数器
        old_keys = [k for k in request_counts.keys() if int(k.split(':')[1]) < current_time - 1]
        for old_key in old_keys:
            del request_counts[old_key]
        
        # 检查频率限制
        if request_counts[key] > rate_limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            raise HTTPException(status_code=429, detail="Too many requests")
            
        return await call_next(request)


import time