#!/usr/bin/env python3
"""
测试餐次取消后列表显示功能
"""

import os
import sys
from pathlib import Path
import logging
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db.manager import DatabaseManager
from db.core_operations import CoreOperations
from db.query_operations import QueryOperations

def test_cancel_display():
    """测试餐次取消后在列表中的显示"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 连接数据库
    db_path = os.path.join(project_root.parent, "data/gang_hao_fan_dev.db")
    db_manager = DatabaseManager(db_path)
    db_manager.connect()
    
    # 初始化操作对象
    core_ops = CoreOperations(db_manager)
    query_ops = QueryOperations(db_manager)
    
    try:
        # 1. 创建测试餐次
        logger.info("=== 创建测试餐次 ===")
        
        meal_result = core_ops.admin_publish_meal(
            admin_user_id=3,
            date="2025-12-25", 
            slot="lunch",
            description="圣诞节套餐",
            base_price_cents=2000,
            addon_config={},
            max_orders=30
        )
        
        meal_id = meal_result['meal_id']
        logger.info(f"创建餐次成功: meal_id={meal_id}")
        
        # 2. 查询列表，确认餐次存在
        logger.info("=== 查询餐次列表（取消前） ===")
        meals_result = query_ops.query_meals_by_date_range("2025-12-20", "2025-12-30")
        
        if meals_result["success"]:
            meals = meals_result["data"]["meals"]
            target_meal = None
            for meal in meals:
                if meal["meal_id"] == meal_id:
                    target_meal = meal
                    break
            
            if target_meal:
                logger.info(f"找到餐次: meal_id={target_meal['meal_id']}, status={target_meal['status']}, status_text='{target_meal.get('status_text', 'N/A')}'")
            else:
                logger.warning(f"未在列表中找到 meal_id={meal_id}")
        else:
            logger.error(f"查询餐次列表失败: {meals_result.get('message')}")
        
        # 3. 取消餐次
        logger.info("=== 取消测试餐次 ===")
        
        cancel_result = core_ops.admin_cancel_meal(
            admin_user_id=3,
            meal_id=meal_id,
            cancel_reason="测试取消显示"
        )
        
        logger.info(f"取消餐次成功: {cancel_result['message']}")
        
        # 4. 再次查询列表，确认已取消餐次是否显示
        logger.info("=== 查询餐次列表（取消后） ===")
        meals_result_after = query_ops.query_meals_by_date_range("2025-12-20", "2025-12-30")
        
        if meals_result_after["success"]:
            meals = meals_result_after["data"]["meals"]
            target_meal_after = None
            for meal in meals:
                if meal["meal_id"] == meal_id:
                    target_meal_after = meal
                    break
            
            if target_meal_after:
                logger.info(f"✅ 成功找到已取消餐次: meal_id={target_meal_after['meal_id']}, status={target_meal_after['status']}")
                logger.info(f"   餐次详情: date={target_meal_after['date']}, slot={target_meal_after['slot']}, description={target_meal_after['description']}")
                print(f"✅ 测试成功: 已取消餐次正确显示在列表中，状态为 '{target_meal_after['status']}'")
            else:
                logger.error(f"❌ 未在列表中找到已取消的 meal_id={meal_id}")
                print("❌ 测试失败: 已取消餐次未在列表中显示")
        else:
            logger.error(f"查询餐次列表失败: {meals_result_after.get('message')}")
        
        # 5. 验证API响应格式
        logger.info("=== 验证API响应格式 ===")
        if target_meal_after:
            expected_fields = ['meal_id', 'date', 'slot', 'description', 'status', 'base_price_cents', 'max_orders', 'current_orders']
            missing_fields = []
            for field in expected_fields:
                if field not in target_meal_after:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"响应缺少字段: {missing_fields}")
            else:
                logger.info("✅ API响应格式正确")
                
            # 显示完整响应数据
            logger.info(f"完整响应数据: {json.dumps(target_meal_after, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        
        # 打印详细错误信息
        import traceback
        traceback.print_exc()
        
    finally:
        db_manager.close()

if __name__ == "__main__":
    test_cancel_display()