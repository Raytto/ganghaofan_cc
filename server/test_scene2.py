#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scene2 情景测试脚本
参考: doc/test/scene2.md

完整的后端逻辑+前端数据接口检查的情景测试
包括：餐次发布、订单管理、余额管理、退款机制等
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_DATE = "2025-09-24"
TEST_SLOT = "dinner"

class AdminUser:
    """管理员用户类"""
    
    def __init__(self, name: str, base_url: str = BASE_URL):
        self.name = name
        self.base_url = base_url
        self.token = None
        self.user_info = None
    
    def login_admin(self, admin_name: str):
        """管理员登录"""
        # 1. 模拟微信登录获取token
        login_data = {
            "code": f"mock_code_for_admin_{admin_name.lower()}_scene2"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/wechat/login", json=login_data)
        if response.status_code != 200:
            raise Exception(f"登录失败: {response.text}")
        
        login_result = response.json()
        if not login_result.get('success'):
            raise Exception(f"登录失败: {login_result.get('error')}")
        
        self.token = login_result['data']['access_token']
        print(f"✅ 管理员{admin_name}获取token成功")
        
        # 调试：查看登录数据
        print(f"DEBUG: 登录返回数据: {login_result}")
        
        # 2. 如果是新用户，进行注册
        if login_result['data'].get('is_new_user', False):
            register_data = {
                "wechat_name": f"管理员{admin_name}",
                "avatar_url": "https://example.com/avatar.jpg"
            }
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(f"{self.base_url}/api/auth/register", json=register_data, headers=headers)
            if response.status_code != 200:
                raise Exception(f"注册失败: {response.text}")
            
            register_result = response.json()
            if not register_result.get('success'):
                raise Exception(f"注册失败: {register_result.get('error')}")
            
            print(f"✅ 管理员{admin_name}注册成功")
        else:
            print(f"DEBUG: 用户{admin_name}不是新用户或不需要注册")
        
        # 3. 获取用户信息确认管理员权限
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/auth/me", headers=headers)
        if response.status_code != 200:
            raise Exception(f"获取用户信息失败: {response.text}")
        
        me_result = response.json()
        if not me_result.get('success'):
            raise Exception(f"获取用户信息失败: {me_result.get('error')}")
        
        self.user_info = me_result['data']
        print(f"✅ 管理员{admin_name}信息: {self.user_info['wechat_name']}, is_admin: {self.user_info['is_admin']}")
        
    def recharge_user(self, user_id: int, amount_yuan: float, reason: str = "测试充值"):
        """给用户充值"""
        recharge_data = {
            "target_user_id": user_id,
            "amount_cents": int(amount_yuan * 100),
            "reason": reason
        }
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/admin/users/{user_id}/recharge", 
            json=recharge_data, 
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"充值失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"充值失败: {result.get('error')}")
        
        return result['data']
    
    def get_calendar_meals(self, start_date: str, end_date: str):
        """获取日历页面餐次数据"""
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = requests.get(f"{self.base_url}/api/meals/calendar", params=params, headers=headers)
        if response.status_code != 200:
            raise Exception(f"获取日历餐次失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"获取日历餐次失败: {result.get('error')}")
        
        # 添加调试信息
        print(f"DEBUG: Calendar API response: {result}")
        
        return result['data']['meals']  # 返回餐次列表而不是整个data对象
    
    def publish_meal(self, date: str, slot: str, description: str, base_price_yuan: float, 
                    addon_config: Dict[str, int], max_orders: int):
        """发布餐次"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 先获取active的附加项
        response = requests.get(f"{self.base_url}/api/admin/addons", 
                              params={"status": "active"}, headers=headers)
        if response.status_code != 200:
            raise Exception(f"获取附加项失败: {response.text}")
        
        addons_result = response.json()
        if not addons_result.get('success'):
            raise Exception(f"获取附加项失败: {addons_result.get('error')}")
        
        # 发布餐次
        meal_data = {
            "date": date,
            "slot": slot,
            "description": description,
            "base_price_cents": int(base_price_yuan * 100),  # 转换为分
            "addon_config": addon_config,
            "max_orders": max_orders
        }
        
        response = requests.post(f"{self.base_url}/api/admin/meals", json=meal_data, headers=headers)
        if response.status_code not in [200, 201]:
            raise Exception(f"发布餐次失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"发布餐次失败: {result.get('error')}")
        
        return result['data']
    
    def cancel_meal(self, meal_id: int, cancel_reason: str = "管理员取消"):
        """取消餐次"""
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {
            "cancel_reason": cancel_reason
        }
        
        response = requests.delete(f"{self.base_url}/api/admin/meals/{meal_id}", 
                                 json=data, headers=headers)
        if response.status_code != 200:
            raise Exception(f"取消餐次失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"取消餐次失败: {result.get('error')}")
        
        return result['data']
    
    def create_order(self, meal_id: int, addon_selections: Optional[Dict[str, int]] = None):
        """创建订单"""
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {
            "meal_id": meal_id,
            "addon_selections": addon_selections or {}
        }
        
        response = requests.post(f"{self.base_url}/api/orders", json=data, headers=headers)
        if response.status_code != 200:
            return {"success": False, "error": response.json().get("error", response.text)}
        
        result = response.json()
        return result
    
    def get_profile(self):
        """获取用户资料（包括余额）"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(f"{self.base_url}/api/users/profile", headers=headers)
        if response.status_code != 200:
            raise Exception(f"获取用户资料失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"获取用户资料失败: {result.get('error')}")
        
        return result['data']
    
    def get_other_user_balance(self, target_user_id: int):
        """管理员查询其他用户的余额（通过管理员API）"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 尝试通过管理员用户列表API获取用户信息
        response = requests.get(f"{self.base_url}/api/admin/users", headers=headers)
        if response.status_code != 200:
            raise Exception(f"获取用户列表失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"获取用户列表失败: {result.get('error')}")
        
        # 在用户列表中找到目标用户
        users = result['data']
        for user in users:
            if user['user_id'] == target_user_id:
                return user['balance_yuan']
        
        raise Exception(f"未找到用户ID {target_user_id}")


def find_meal_by_date_slot(meals: List[Dict], date: str, slot: str) -> Optional[Dict]:
    """在餐次列表中查找指定日期和时段的餐次"""
    for meal in meals:
        if meal['date'] == date and meal['slot'] == slot:
            return meal
    return None


def main():
    """主测试函数"""
    try:
        print("🚀 开始Scene2情景测试：完整的餐次发布-订单-退款流程")
        print(f"测试目标: {TEST_DATE} {TEST_SLOT}")
        
        # 初始化管理员用户
        admin_a = AdminUser("A")
        admin_b = AdminUser("B")
        
        # 步骤1: 管理员A登录
        print(f"\n📋 步骤1: 管理员A登录")
        admin_a.login_admin("A")
        
        # 步骤2: 检查管理员A的calendar页面2025年9月24日的晚餐状态
        print(f"\n📋 步骤2: 检查管理员A的calendar页面{TEST_DATE}的{TEST_SLOT}状态")
        meals_a1 = admin_a.get_calendar_meals(TEST_DATE, TEST_DATE)
        dinner_meal_a1 = find_meal_by_date_slot(meals_a1, TEST_DATE, TEST_SLOT)
        
        if dinner_meal_a1:
            raise Exception(f"预期错误: 晚餐状态为 {dinner_meal_a1['status']}，应该是未发布")
        else:
            print("✅ 预期正确: 晚餐不存在（未发布状态）")
        
        # 步骤3: 管理员B登录
        print(f"\n📋 步骤3: 管理员B登录")
        admin_b.login_admin("B")
        
        # 步骤4: 管理员B发布晚餐
        print(f"\n📋 步骤4: 管理员B发布{TEST_DATE}的{TEST_SLOT}")
        # 配置: 可以加至多3个鸡腿（每个3元），最多2人
        addon_config = {"1": 3}  # 假设鸡腿的addon_id是1，最多3个
        meal_data = admin_b.publish_meal(
            date=TEST_DATE,
            slot=TEST_SLOT,
            description="测试",
            base_price_yuan=20.0,
            addon_config=addon_config,
            max_orders=2
        )
        meal_id = meal_data['meal_id']
        print(f"✅ 晚餐发布成功: meal_id={meal_id}")
        
        # 步骤5: 检查管理员A的calendar页面状态
        print(f"\n📋 步骤5: 检查管理员A的calendar页面{TEST_DATE}{TEST_SLOT}状态")
        meals_a2 = admin_a.get_calendar_meals(TEST_DATE, TEST_DATE)
        dinner_meal_a2 = find_meal_by_date_slot(meals_a2, TEST_DATE, TEST_SLOT)
        
        if not dinner_meal_a2 or dinner_meal_a2['status'] != 'published':
            raise Exception(f"预期错误: 晚餐状态应该是已发布，实际为 {dinner_meal_a2['status'] if dinner_meal_a2 else '不存在'}")
        print("✅ 预期正确: 晚餐状态为已发布")
        
        # 步骤6: 检查管理员B的calendar页面状态
        print(f"\n📋 步骤6: 检查管理员B的calendar页面{TEST_DATE}{TEST_SLOT}状态")
        meals_b1 = admin_b.get_calendar_meals(TEST_DATE, TEST_DATE)
        dinner_meal_b1 = find_meal_by_date_slot(meals_b1, TEST_DATE, TEST_SLOT)
        
        if not dinner_meal_b1 or dinner_meal_b1['status'] != 'published':
            raise Exception(f"预期错误: 晚餐状态应该是已发布，实际为 {dinner_meal_b1['status'] if dinner_meal_b1 else '不存在'}")
        print("✅ 预期正确: 晚餐状态为已发布")
        
        # 步骤7: 管理员B订餐（选择加2个鸡腿）
        print(f"\n📋 步骤7: 管理员B订{TEST_DATE}的{TEST_SLOT}（选择加2个鸡腿）")
        order_result_b1 = admin_b.create_order(meal_id, {"1": 2})  # 2个鸡腿
        if not order_result_b1.get('success'):
            raise Exception(f"订餐失败: {order_result_b1.get('error')}")
        
        # 验证总价: 20元基础 + 2×3元鸡腿 = 26元
        order_amount = order_result_b1['data']['amount_yuan']
        if abs(order_amount - 26.0) > 0.01:
            raise Exception(f"预期错误: 总价应该是26元，实际为 {order_amount}元")
        print(f"✅ 订餐成功: 总价 {order_amount}元（20元基础 + 6元附加项）")
        
        # 步骤8: 管理员B再次订餐（应该失败）
        print(f"\n📋 步骤8: 管理员B再次订{TEST_DATE}的{TEST_SLOT}（应该失败）")
        order_result_b2 = admin_b.create_order(meal_id, {"1": 2})
        if order_result_b2.get('success'):
            raise Exception("预期错误: 重复订餐应该失败")
        print(f"✅ 预期正确: 重复订餐失败 - {order_result_b2.get('error')}")
        
        # 步骤9: 检查管理员A的calendar页面进度
        print(f"\n📋 步骤9: 检查管理员A的calendar页面{TEST_DATE}{TEST_SLOT}进度")
        meals_a3 = admin_a.get_calendar_meals(TEST_DATE, TEST_DATE)
        dinner_meal_a3 = find_meal_by_date_slot(meals_a3, TEST_DATE, TEST_SLOT)
        
        if not dinner_meal_a3:
            raise Exception("晚餐不存在")
        
        current_orders = dinner_meal_a3['current_orders']
        max_orders = dinner_meal_a3['max_orders']
        if current_orders != 1 or max_orders != 2:
            raise Exception(f"预期错误: 进度应该是1/2，实际为 {current_orders}/{max_orders}")
        print(f"✅ 预期正确: 晚餐状态为已发布，进度为 {current_orders}/{max_orders}")
        
        # 步骤10: 管理员A订餐（不选附加项）
        print(f"\n📋 步骤10: 管理员A订{TEST_DATE}的{TEST_SLOT}（不选附加项）")
        order_result_a1 = admin_a.create_order(meal_id, {})
        if not order_result_a1.get('success'):
            raise Exception(f"订餐失败: {order_result_a1.get('error')}")
        
        # 验证总价: 20元基础
        order_amount_a = order_result_a1['data']['amount_yuan']
        if abs(order_amount_a - 20.0) > 0.01:
            raise Exception(f"预期错误: 总价应该是20元，实际为 {order_amount_a}元")
        print(f"✅ 订餐成功: 总价 {order_amount_a}元（仅基础价格）")
        
        # 步骤9: 检查管理员B的余额（应为负数）
        print(f"\n📋 步骤9: 检查管理员B的余额")
        profile_b = admin_b.get_profile()
        balance_b = profile_b['balance_yuan']
        expected_balance_b = -26.0  # 0 - 26 = -26 (信用系统)
        if abs(balance_b - expected_balance_b) > 0.01:
            raise Exception(f"预期错误: 管理员B余额应该是{expected_balance_b}元，实际为 {balance_b}元")
        print(f"✅ 预期正确: 管理员B余额为 {balance_b}元")
        
        # 步骤10: 检查管理员A的余额（应为负数）
        print(f"\n📋 步骤10: 检查管理员A的余额")
        profile_a = admin_a.get_profile()
        balance_a = profile_a['balance_yuan']
        expected_balance_a = -20.0  # 0 - 20 = -20 (信用系统)
        if abs(balance_a - expected_balance_a) > 0.01:
            raise Exception(f"预期错误: 管理员A余额应该是{expected_balance_a}元，实际为 {balance_a}元")
        print(f"✅ 预期正确: 管理员A余额为 {balance_a}元")
        
        # 步骤11: 管理员B取消晚餐
        print(f"\n📋 步骤11: 管理员B取消{TEST_DATE}的{TEST_SLOT}")
        cancel_result = admin_b.cancel_meal(meal_id, "测试取消")
        print(f"✅ 晚餐取消成功: meal_id={meal_id}")
        
        # 步骤12: 检查管理员A的余额（退款后应为0元）
        print(f"\n📋 步骤12: 检查管理员A的余额（退款后）")
        profile_a_after = admin_a.get_profile()
        balance_a_after = profile_a_after['balance_yuan']
        if abs(balance_a_after - 0.0) > 0.01:  # 应该恢复为0元
            raise Exception(f"预期错误: 管理员A余额应该是0元，实际为 {balance_a_after}元")
        print(f"✅ 预期正确: 管理员A余额恢复为 {balance_a_after}元")
        
        # 步骤13: 检查管理员B的余额（退款后应为0元）
        print(f"\n📋 步骤13: 检查管理员B的余额（退款后）")
        profile_b_after = admin_b.get_profile()
        balance_b_after = profile_b_after['balance_yuan']
        if abs(balance_b_after - 0.0) > 0.01:  # 应该恢复为0元
            raise Exception(f"预期错误: 管理员B余额应该是0元，实际为 {balance_b_after}元")
        print(f"✅ 预期正确: 管理员B余额恢复为 {balance_b_after}元")
        
        # 步骤14: 检查管理员A的calendar页面状态（应该是未发布）
        print(f"\n📋 步骤14: 检查管理员A的calendar页面{TEST_DATE}{TEST_SLOT}状态（取消后）")
        meals_a4 = admin_a.get_calendar_meals(TEST_DATE, TEST_DATE)
        dinner_meal_a4 = find_meal_by_date_slot(meals_a4, TEST_DATE, TEST_SLOT)
        
        if dinner_meal_a4 and dinner_meal_a4['status'] != 'unpublished':
            raise Exception(f"预期错误: 晚餐状态应该是未发布，实际为 {dinner_meal_a4['status']}")
        print("✅ 预期正确: 晚餐状态为未发布")
        
        # 步骤15: 检查管理员B的calendar页面状态（应该是未发布）
        print(f"\n📋 步骤15: 检查管理员B的calendar页面{TEST_DATE}{TEST_SLOT}状态（取消后）")
        meals_b2 = admin_b.get_calendar_meals(TEST_DATE, TEST_DATE)
        dinner_meal_b2 = find_meal_by_date_slot(meals_b2, TEST_DATE, TEST_SLOT)
        
        if dinner_meal_b2 and dinner_meal_b2['status'] != 'unpublished':
            raise Exception(f"预期错误: 晚餐状态应该是未发布，实际为 {dinner_meal_b2['status']}")
        print("✅ 预期正确: 晚餐状态为未发布")
        
        # 步骤16: 管理员A发布新晚餐
        print(f"\n📋 步骤16: 管理员A发布{TEST_DATE}的{TEST_SLOT}（第二次）")
        addon_config2 = {"1": 1}  # 最多1个鸡腿
        meal_data2 = admin_a.publish_meal(
            date=TEST_DATE,
            slot=TEST_SLOT,
            description="测试2",
            base_price_yuan=25.0,
            addon_config=addon_config2,
            max_orders=2
        )
        meal_id2 = meal_data2['meal_id']
        print(f"✅ 晚餐发布成功: meal_id={meal_id2}")
        
        # 步骤17: 检查管理员B的calendar页面状态
        print(f"\n📋 步骤17: 检查管理员B的calendar页面{TEST_DATE}{TEST_SLOT}状态（重新发布后）")
        meals_b3 = admin_b.get_calendar_meals(TEST_DATE, TEST_DATE)
        dinner_meal_b3 = find_meal_by_date_slot(meals_b3, TEST_DATE, TEST_SLOT)
        
        if not dinner_meal_b3 or dinner_meal_b3['status'] != 'published':
            raise Exception(f"预期错误: 晚餐状态应该是已发布，实际为 {dinner_meal_b3['status'] if dinner_meal_b3 else '不存在'}")
        print("✅ 预期正确: 晚餐状态为已发布")
        
        print(f"\n🎉 Scene2测试完全成功！")
        print("✅ 所有17个步骤都符合预期")
        print("✅ 餐次发布、订单创建、余额扣减、退款机制、状态同步 - 全部正常")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Scene2测试失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())