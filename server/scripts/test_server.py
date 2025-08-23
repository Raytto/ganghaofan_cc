#!/usr/bin/env python3
# 参考文档: doc/server_structure.md
# 简单的服务器测试脚本

import os
import sys
import time
import requests
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_server_startup():
    """测试服务器启动和基本功能"""
    
    print("=== 罡好饭API服务器测试 ===")
    
    # 设置环境变量
    os.environ['CONFIG_ENV'] = 'development'
    os.environ['PYTHONPATH'] = f"{os.environ.get('PYTHONPATH', '')}:{project_root}"
    
    print(f"工作目录: {project_root}")
    print(f"配置环境: {os.environ['CONFIG_ENV']}")
    
    try:
        # 导入应用
        from api.main import app
        print("✓ FastAPI应用导入成功")
        
        # 测试配置加载
        from utils.config import Config
        config = Config()
        print("✓ 配置加载成功")
        print(f"应用名称: {config.config['app']['name']}")
        print(f"应用版本: {config.config['app']['version']}")
        
        # 测试数据库连接
        from db.manager import DatabaseManager
        db_config = config.get_database_config()
        db_manager = DatabaseManager(db_config["path"], auto_connect=True)
        print("✓ 数据库连接成功")
        
        # 测试数据库表
        table_names = ['users', 'meals', 'addons', 'orders', 'ledger']
        for table_name in table_names:
            try:
                info = db_manager.get_table_info(table_name)
                print(f"✓ 表 {table_name}: {info['record_count']} 条记录")
            except Exception as e:
                print(f"✗ 表 {table_name} 检查失败: {e}")
        
        db_manager.close()
        
        print("\n=== 服务器基础组件测试通过 ===")
        print("可以使用以下命令启动服务器:")
        print("开发模式: ./scripts/start_dev.sh")
        print("远程开发: ./scripts/start_dev_remote.sh") 
        print("生产模式: ./scripts/start.sh")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_server_startup()
    sys.exit(0 if success else 1)