#!/usr/bin/env python3
# 数据库约束检查和修复脚本

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.manager import DatabaseManager

def main():
    """
    主函数：检查和修复数据库约束
    """
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 获取配置环境
    config_env = os.getenv('CONFIG_ENV', 'development')
    
    # 根据环境选择数据库路径
    if config_env == 'production':
        db_path = "data/gang_hao_fan.db"
    elif config_env == 'development-remote':
        db_path = "data/gang_hao_fan_dev_remote.db"
    else:  # development
        db_path = "data/gang_hao_fan_dev.db"
    
    # 转换为绝对路径
    db_path = os.path.join(project_root.parent, db_path)
    
    logging.info(f"开始检查数据库约束: {db_path}")
    logging.info(f"配置环境: {config_env}")
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager(db_path)
        db_manager.connect()
        
        # 检查所有表约束
        logging.info("=== 检查数据库表约束 ===")
        db_manager.check_table_constraints()
        
        # 修复约束问题
        logging.info("=== 修复约束问题 ===")
        try:
            db_manager.repair_table_constraints()
            logging.info("约束修复完成!")
        except Exception as e:
            logging.warning(f"约束修复过程中出现问题: {e}")
        
        # 再次检查约束状态
        logging.info("=== 修复后再次检查约束 ===")
        db_manager.check_table_constraints("meals")  # 重点检查meals表
        
        logging.info("数据库约束检查和修复完成!")
            
    except Exception as e:
        logging.error(f"数据库约束检查失败: {e}")
        sys.exit(1)
    finally:
        if 'db_manager' in locals():
            db_manager.close()

if __name__ == "__main__":
    main()