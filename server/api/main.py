# 参考文档: doc/server_structure.md 主应用部分
# FastAPI主应用

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

# 导入配置和中间件
from utils.config import Config
from utils.logger import setup_logging
from api.middleware import setup_middleware

# 导入所有路由
from api.auth import auth_router
from api.users import users_router
from api.meals import meals_router
from api.orders import orders_router
from api.admin import admin_router

# 全局配置实例
config = Config()

# 设置日志
setup_logging(config.config)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("罡好饭API服务启动中...")
    logger.info(f"环境: {config.env}")
    logger.info(f"调试模式: {config.config['app']['debug']}")
    
    yield
    
    # 关闭时执行
    logger.info("罡好饭API服务关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title=config.config['app']['name'],
    version=config.config['app']['version'],
    description=config.config['app']['description'],
    debug=config.config['app']['debug'],
    lifespan=lifespan
)

# 设置中间件
setup_middleware(app, config.config)

# 注册路由
app.include_router(auth_router, tags=["认证"])
app.include_router(users_router, tags=["用户"])
app.include_router(meals_router, tags=["餐次"])
app.include_router(orders_router, tags=["订单"])
app.include_router(admin_router, tags=["管理员"])


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "data": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "data": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


# 根路径
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "罡好饭API服务运行中",
        "version": config.config['app']['version'],
        "status": "healthy"
    }


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 这里可以添加数据库连接检查等
        return {
            "status": "healthy",
            "version": config.config['app']['version'],
            "environment": config.env
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


# API信息端点
@app.get("/api/info")
async def api_info():
    """API信息端点"""
    return {
        "name": config.config['app']['name'],
        "version": config.config['app']['version'],
        "description": config.config['app']['description'],
        "environment": config.env,
        "endpoints": {
            "auth": "/api/auth",
            "users": "/api/users", 
            "meals": "/api/meals",
            "orders": "/api/orders",
            "admin": "/api/admin"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # 从配置获取服务器设置
    server_config = config.config['server']
    
    uvicorn.run(
        "main:app",
        host=server_config.get('host', '127.0.0.1'),
        port=server_config.get('port', 8000),
        reload=server_config.get('reload', False),
        workers=1 if server_config.get('reload', False) else server_config.get('workers', 1),
        log_level="debug" if config.config['app']['debug'] else "info"
    )