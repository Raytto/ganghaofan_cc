# 参考文档: doc/api.md 认证模块
# 认证相关API路由

import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import WeChatLoginRequest, RegisterRequest, LoginResponse, RefreshTokenResponse, TokenData, UserInfo
from .wechat_service import WeChatService
from db.manager import DatabaseManager
from db.supporting_operations import SupportingOperations
from utils.config import Config
from utils.security import JWTManager
from utils.response import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["认证"])

# 初始化服务
config = Config()
jwt_manager = JWTManager(
    secret_key=config.get("auth.jwt_secret_key", "development-secret-key"),
    algorithm=config.get("auth.jwt_algorithm", "HS256"),
    access_token_expire_minutes=config.get("auth.access_token_expire_minutes", 1440)
)
security = HTTPBearer()


def get_database():
    """获取数据库连接"""
    db_config = config.get_database_config()
    db_manager = DatabaseManager(db_config["path"], auto_connect=True)
    try:
        yield db_manager
    finally:
        db_manager.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_database)
) -> TokenData:
    """获取当前用户信息"""
    try:
        token = credentials.credentials
        payload = jwt_manager.decode_token(token)
        
        # 验证用户是否存在且状态正常
        support_ops = SupportingOperations(db)
        user_info = support_ops.get_user_by_id(payload["user_id"])
        
        if not user_info or user_info["status"] != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )
        
        return TokenData(
            user_id=payload["user_id"],
            open_id=payload["open_id"],
            is_admin=payload.get("is_admin", False)
        )
        
    except Exception as e:
        logger.error(f"用户认证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败，请重新登录"
        )


def get_admin_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """获取管理员用户（仅管理员可访问）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


@router.post("/wechat/login", response_model=Dict[str, Any])
async def wechat_login(
    login_request: WeChatLoginRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    微信静默登录 - 获取或创建用户
    
    参考文档: doc/api.md - 1.1 微信静默登录
    """
    try:
        # 1. 通过微信code获取openid
        wechat_service = WeChatService()
        wechat_data = await wechat_service.get_access_token(login_request.code)
        openid = wechat_data["openid"]
        
        # 2. 微信静默登录（获取或创建用户）
        support_ops = SupportingOperations(db)
        login_result = support_ops.wechat_silent_login(openid)
        
        if not login_result["success"]:
            logger.error(f"微信静默登录失败: {login_result.get('error')}")
            return create_error_response(login_result.get('error', '登录失败'))
        
        user_data = login_result["data"]
        
        # 3. 生成JWT Token
        token_payload = {
            "user_id": user_data["user_id"],
            "open_id": user_data["open_id"],
            "is_admin": user_data["is_admin"]
        }
        
        access_token = jwt_manager.create_token(token_payload)
        
        # 4. 构造响应数据
        user_info = UserInfo(
            user_id=user_data["user_id"],
            open_id=user_data["open_id"],
            wechat_name=user_data.get("wechat_name"),
            avatar_url=user_data.get("avatar_url"),
            balance_cents=user_data["balance_cents"],
            balance_yuan=user_data["balance_yuan"],
            is_admin=user_data["is_admin"],
            is_registered=user_data["is_registered"]
        )
        
        response_data = LoginResponse(
            access_token=access_token,
            user_info=user_info
        )
        
        # 记录日志
        if user_data["is_registered"]:
            logger.info(f"已注册用户登录: {user_data['wechat_name']} ({user_data['open_id']})")
        else:
            logger.info(f"未注册用户登录: {user_data['open_id']}")
        
        return create_success_response(
            data=response_data.dict(),
            message=login_result.get('message', '登录成功')
        )
        
    except Exception as e:
        logger.error(f"微信登录失败: {str(e)}")
        return create_error_response(f"登录失败: {str(e)}")


@router.post("/register", response_model=Dict[str, Any])
async def complete_user_registration(
    register_request: RegisterRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    完成用户注册 - 更新用户个人信息
    
    参考文档: doc/api.md - 1.2 完成用户注册
    """
    try:
        # 完成用户注册
        support_ops = SupportingOperations(db)
        register_result = support_ops.complete_user_registration(
            open_id=current_user.open_id,
            wechat_name=register_request.wechat_name,
            avatar_url=register_request.avatar_url
        )
        
        if not register_result["success"]:
            logger.error(f"完成用户注册失败: {register_result.get('error')}")
            return create_error_response(register_result.get('error', '注册失败'))
        
        user_data = register_result["data"]
        
        logger.info(f"用户注册完成: {user_data['wechat_name']} ({user_data['open_id']})")
        
        return create_success_response(
            data=user_data,
            message=register_result.get('message', '注册完成')
        )
        
    except Exception as e:
        logger.error(f"完成用户注册失败: {str(e)}")
        return create_error_response(f"注册失败: {str(e)}")


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    current_user: TokenData = Depends(get_current_user)
):
    """
    刷新访问令牌
    
    参考文档: doc/api.md - 1.2 刷新 Token
    """
    try:
        # 生成新的JWT Token
        token_payload = {
            "user_id": current_user.user_id,
            "open_id": current_user.open_id,
            "is_admin": current_user.is_admin
        }
        
        new_access_token = jwt_manager.create_token(token_payload)
        
        response_data = RefreshTokenResponse(
            access_token=new_access_token
        )
        
        return create_success_response(
            data=response_data.dict(),
            message="Token刷新成功"
        )
        
    except Exception as e:
        logger.error(f"Token刷新失败: {str(e)}")
        return create_error_response(f"Token刷新失败: {str(e)}")


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取当前用户信息（调试用）
    """
    try:
        support_ops = SupportingOperations(db)
        user_info = support_ops.get_user_by_id(current_user.user_id)
        
        if not user_info:
            return create_error_response("用户不存在")
        
        response_data = {
            "user_id": user_info["user_id"],
            "open_id": user_info["open_id"],
            "wechat_name": user_info["wechat_name"],
            "avatar_url": user_info.get("avatar_url"),
            "balance_cents": user_info["balance_cents"],
            "balance_yuan": user_info["balance_cents"] / 100.0,
            "is_admin": user_info["is_admin"],
            "status": user_info["status"],
            "created_at": user_info["created_at"],
            "last_login_at": user_info.get("last_login_at")
        }
        
        return create_success_response(
            data=response_data,
            message="获取用户信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return create_error_response(f"获取用户信息失败: {str(e)}")