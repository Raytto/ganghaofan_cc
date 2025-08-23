# 参考文档: doc/server_structure.md
# 安全工具（JWT、加密）

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from passlib.context import CryptContext

class JWTManager:
    """
    JWT令牌管理器
    参考文档: doc/server_structure.md - utils/security.py
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 access_token_expire_minutes: int = 1440):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """
        创建访问令牌
        
        Args:
            data: 要编码的数据（通常包含user_id, is_admin等）
        
        Returns:
            JWT令牌字符串
        """
        to_encode = data.copy()
        
        # 添加过期时间
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        # 编码JWT
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌字符串
        
        Returns:
            解码后的数据，验证失败返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            # 令牌过期
            return None
        except jwt.JWTError:
            # 令牌无效
            return None
    
    def refresh_token(self, token: str) -> Optional[str]:
        """
        刷新JWT令牌
        
        Args:
            token: 原JWT令牌字符串
        
        Returns:
            新的JWT令牌字符串，验证失败返回None
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        # 移除过期时间和签发时间，重新生成
        payload.pop('exp', None)
        payload.pop('iat', None)
        
        return self.create_access_token(payload)
    
    def create_token(self, data: Dict[str, Any]) -> str:
        """
        创建令牌（create_access_token的别名）
        """
        return self.create_access_token(data)
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        解码令牌（verify_token的别名）
        """
        return self.verify_token(token)

# 全局密码上下文（暂时不用于微信登录，但可用于其他功能）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    哈希密码
    
    Args:
        password: 明文密码
    
    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
    
    Returns:
        验证结果
    """
    return pwd_context.verify(plain_password, hashed_password)