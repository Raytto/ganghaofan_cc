#!/usr/bin/env python3
"""
测试餐次取消功能
"""

import os
import sys
from pathlib import Path
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db.manager import DatabaseManager
from db.core_operations import CoreOperations

def test_meal_cancel():
    """测试餐次创建和取消"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 连接数据库
    db_path = os.path.join(project_root.parent, "data/gang_hao_fan_dev.db")
    db_manager = DatabaseManager(db_path)
    db_manager.connect()
    
    # 初始化核心操作
    core_ops = CoreOperations(db_manager)
    
    try:
        # 1. 创建测试餐次
        logger.info("=== 创建测试餐次 ===")
        
        meal_result = core_ops.admin_publish_meal(
            admin_user_id=3,
            date="2025-12-31", 
            slot="dinner",
            description="测试餐次",
            base_price_cents=1500,
            addon_config={},
            max_orders=50
        )
        
        meal_id = meal_result['meal_id']
        logger.info(f"创建餐次成功: meal_id={meal_id}")
        
        # 2. 取消餐次
        logger.info("=== 取消测试餐次 ===")
        
        cancel_result = core_ops.admin_cancel_meal(
            admin_user_id=3,
            meal_id=meal_id,
            cancel_reason="测试取消"
        )
        
        logger.info(f"取消餐次成功: {cancel_result['message']}")
        
        # 3. 验证状态
        meal_info = db_manager.execute_single(
            "SELECT status, canceled_by, canceled_reason FROM meals WHERE meal_id = ?", 
            [meal_id]
        ).fetchone()
        
        logger.info(f"餐次状态验证: status={meal_info[0]}, canceled_by={meal_info[1]}, reason={meal_info[2]}")
        
        print("✅ 测试成功: 餐次创建和取消都正常工作")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        
        # 打印详细错误信息
        import traceback
        traceback.print_exc()
        
    finally:
        db_manager.close()

if __name__ == "__main__":
    test_meal_cancel()