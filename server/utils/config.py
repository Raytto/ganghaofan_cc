# 参考文档: doc/server_structure.md
# 配置管理工具

import json
import os
import logging
from typing import Dict, Any
import re

def _replace_env_vars(value: str) -> str:
    """
    替换环境变量占位符
    将 ${ENV_VAR} 格式的占位符替换为实际的环境变量值
    """
    def replace_match(match):
        env_var = match.group(1)
        return os.getenv(env_var, match.group(0))  # 如果环境变量不存在，保持原样
    
    return re.sub(r'\$\{([^}]+)\}', replace_match, value)

def _process_config_values(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归处理配置值，替换环境变量
    """
    if isinstance(config, dict):
        return {k: _process_config_values(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_process_config_values(item) for item in config]
    elif isinstance(config, str):
        return _replace_env_vars(config)
    else:
        return config

def load_config() -> Dict[str, Any]:
    """
    加载配置文件
    根据 CONFIG_ENV 环境变量选择配置文件
    参考文档: doc/server_structure.md - 配置管理
    
    Returns:
        配置字典
    """
    config_env = os.getenv('CONFIG_ENV', 'development')
    
    # 根据环境选择配置文件
    config_files = {
        'production': 'config/config-prod.json',
        'development': 'config/config-dev.json',
        'development-remote': 'config/config-dev-remote.json'
    }
    
    config_file = config_files.get(config_env, 'config/config.json')
    
    # 确保配置文件路径是绝对路径
    if not os.path.isabs(config_file):
        # 从server目录开始查找配置文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_dir = os.path.dirname(script_dir)  # 上一级目录就是server目录
        config_file = os.path.join(server_dir, config_file)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 处理环境变量替换
        config = _process_config_values(config)
        
        # 移除内部文档引用字段
        config.pop('_reference_doc', None)
        
        logging.info(f"成功加载配置文件: {config_file}")
        return config
        
    except FileNotFoundError:
        logging.error(f"配置文件不存在: {config_file}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"配置文件JSON格式错误: {e}")
        raise
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        raise

def get_database_path(config: Dict[str, Any]) -> str:
    """
    获取数据库路径（相对于项目根目录）
    
    Args:
        config: 配置字典
    
    Returns:
        数据库文件的绝对路径
    """
    db_path = config.get('database', {}).get('path', 'data/gang_hao_fan.db')
    
    if not os.path.isabs(db_path):
        # 从server目录计算路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_dir = os.path.dirname(script_dir)  # server目录
        db_path = os.path.join(server_dir, db_path)
    
    return db_path

def validate_config(config: Dict[str, Any]) -> bool:
    """
    验证配置文件的完整性
    
    Args:
        config: 配置字典
    
    Returns:
        验证结果
    """
    required_sections = ['app', 'server', 'database', 'auth', 'logging']
    
    for section in required_sections:
        if section not in config:
            logging.error(f"配置文件缺少必需的section: {section}")
            return False
    
    # 验证关键配置项
    auth_config = config.get('auth', {})
    if not auth_config.get('jwt_secret_key'):
        logging.error("JWT密钥未配置")
        return False
    
    return True


class Config:
    """
    配置管理类
    """
    def __init__(self):
        self.env = os.getenv('CONFIG_ENV', 'development')
        self.config = load_config()
        
        # 验证配置
        if not validate_config(self.config):
            raise ValueError("配置文件验证失败")
    
    def get(self, key: str, default=None):
        """
        获取配置项，支持点号分隔的嵌套键
        
        Args:
            key: 配置键，支持 'app.name' 格式
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        获取数据库配置
        
        Returns:
            数据库配置字典
        """
        db_config = self.config.get('database', {}).copy()
        db_config['path'] = get_database_path(self.config)
        return db_config