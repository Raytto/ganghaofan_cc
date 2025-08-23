# 参考文档: doc/api.md 认证模块
# 微信OAuth服务

import httpx
import logging
from typing import Dict, Any, Optional
from utils.config import Config

logger = logging.getLogger(__name__)


class WeChatService:
    """微信OAuth服务类"""
    
    def __init__(self):
        self.config = Config()
        self.app_id = self.config.get("wechat.app_id")
        self.app_secret = self.config.get("wechat.app_secret")
        
        if not self.app_id or not self.app_secret:
            logger.warning("微信配置缺失，将使用模拟模式")
            self.mock_mode = True
        else:
            self.mock_mode = False
    
    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """
        通过授权码获取access_token
        
        Args:
            code: 微信授权码
            
        Returns:
            包含access_token和openid的字典
            
        Raises:
            Exception: 获取token失败时抛出异常
        """
        if self.mock_mode:
            return self._mock_get_access_token(code)
        
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if "errcode" in data and data["errcode"] != 0:
                    error_msg = data.get("errmsg", "微信接口调用失败")
                    logger.error(f"微信接口错误: {data['errcode']} - {error_msg}")
                    raise Exception(f"微信认证失败: {error_msg}")
                
                if "openid" not in data:
                    logger.error(f"微信接口返回数据异常: {data}")
                    raise Exception("微信接口返回数据异常")
                
                logger.info(f"微信认证成功，获取到openid: {data['openid'][:8]}***")
                
                return {
                    "openid": data["openid"],
                    "session_key": data.get("session_key"),
                    "unionid": data.get("unionid")
                }
                
        except httpx.RequestError as e:
            logger.error(f"微信接口请求失败: {str(e)}")
            raise Exception(f"微信接口请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"微信认证过程出错: {str(e)}")
            raise
    
    def _mock_get_access_token(self, code: str) -> Dict[str, Any]:
        """
        模拟微信认证（开发环境使用）
        
        Args:
            code: 模拟授权码
            
        Returns:
            模拟的认证数据
        """
        logger.info(f"使用模拟微信认证，code: {code}")
        
        # 根据code生成不同的模拟openid
        if code == "admin_test_code":
            openid = "mock_admin_openid_12345"
        elif code == "user_test_code":
            openid = "mock_user_openid_67890"
        else:
            # 基于code生成唯一openid
            import hashlib
            hash_object = hashlib.md5(code.encode())
            openid = f"mock_openid_{hash_object.hexdigest()[:16]}"
        
        return {
            "openid": openid,
            "session_key": "mock_session_key",
            "unionid": None
        }
    
    async def get_user_info(self, access_token: str, openid: str) -> Optional[Dict[str, Any]]:
        """
        获取微信用户信息（如果需要的话）
        
        Args:
            access_token: 微信access_token
            openid: 用户openid
            
        Returns:
            用户信息字典或None
        """
        if self.mock_mode:
            return None
        
        # 注意：小程序的jscode2session接口不会返回用户信息
        # 用户信息需要通过小程序端的wx.getUserProfile接口获取
        # 这里预留接口，实际可能不会使用
        return None