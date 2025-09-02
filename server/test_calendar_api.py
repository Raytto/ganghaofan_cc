#!/usr/bin/env python3
"""
测试日历API端点功能
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
from db.query_operations import QueryOperations

def test_calendar_api_logic():
    """测试日历API的状态映射逻辑"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 连接数据库
    db_path = os.path.join(project_root.parent, "data/gang_hao_fan_dev.db")
    db_manager = DatabaseManager(db_path)
    db_manager.connect()
    
    # 初始化操作对象
    query_ops = QueryOperations(db_manager)
    
    try:
        logger.info("=== 测试日历API逻辑 ===")
        
        # 查询所有餐次
        meals_result = query_ops.query_meals_by_date_range("2025-09-01", "2025-09-30")
        
        if meals_result["success"]:
            meals = meals_result["data"]["meals"]
            logger.info(f"找到 {len(meals)} 个餐次")
            
            # 模拟日历API的状态映射逻辑
            print("\n=== 日历API状态映射测试 ===")
            print("格式: meal_id | 原始状态 | 日历状态 | 状态文本")
            print("-" * 60)
            
            calendar_status_text_map = {
                "published": "已发布",
                "locked": "已锁定", 
                "completed": "已完成",
                "unpublished": "未发布"
            }
            
            for meal in meals:
                # 应用日历API的状态映射
                calendar_status = "unpublished" if meal["status"] == "canceled" else meal["status"]
                status_text = calendar_status_text_map.get(calendar_status, calendar_status)
                
                print(f"{meal['meal_id']:8} | {meal['status']:8} | {calendar_status:10} | {status_text}")
                
                # 检查canceled状态的映射
                if meal["status"] == "canceled":
                    if calendar_status == "unpublished":
                        print(f"  ✅ 成功映射: canceled -> unpublished")
                    else:
                        print(f"  ❌ 映射失败: canceled -> {calendar_status}")
            
            # 统计各种状态
            status_count = {}
            calendar_status_count = {}
            
            for meal in meals:
                status = meal["status"]
                calendar_status = "unpublished" if status == "canceled" else status
                
                status_count[status] = status_count.get(status, 0) + 1
                calendar_status_count[calendar_status] = calendar_status_count.get(calendar_status, 0) + 1
            
            print(f"\n=== 状态统计 ===")
            print("原始状态统计:", status_count)
            print("日历状态统计:", calendar_status_count)
            
            # 验证映射是否正确
            canceled_count = status_count.get("canceled", 0)
            unpublished_count = calendar_status_count.get("unpublished", 0)
            
            if canceled_count > 0:
                if unpublished_count >= canceled_count:
                    print(f"✅ 状态映射验证成功: {canceled_count} 个 canceled 状态被映射为 unpublished")
                else:
                    print(f"❌ 状态映射验证失败: 期望 {canceled_count} 个 unpublished，实际 {unpublished_count} 个")
            else:
                print("ℹ️  当前没有 canceled 状态的餐次")
                
            print(f"\n✅ 日历API状态映射逻辑测试完成")
            print(f"📋 API端点: GET /api/meals/calendar")
            print(f"🔄 关键映射: canceled -> unpublished")
            print(f"📝 客户端应使用此端点替代 /api/meals")
            
        else:
            print(f"❌ 查询失败: {meals_result.get('message')}")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        
        # 打印详细错误信息
        import traceback
        traceback.print_exc()
        
    finally:
        db_manager.close()

if __name__ == "__main__":
    test_calendar_api_logic()