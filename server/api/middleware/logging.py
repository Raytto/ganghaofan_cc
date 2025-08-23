# 参考文档: doc/server_structure.md 中间件部分
# 日志中间件

import time
import uuid
import logging
from fastapi import FastAPI, Request, Response
from typing import Dict, Any

logger = logging.getLogger(__name__)


def setup_logging_middleware(app: FastAPI, config: Dict[str, Any]):
    """
    设置请求日志中间件
    
    Args:
        app: FastAPI应用实例 
        config: 配置字典
    """
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        
        # 记录请求开始
        start_time = time.time()
        
        # 记录请求信息
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"[{request_id}] {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] ERROR - {str(e)} - "
                f"Time: {process_time:.3f}s"
            )
            raise