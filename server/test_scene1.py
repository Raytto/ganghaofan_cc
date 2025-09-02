#!/usr/bin/env python3
"""
情景测试1: 完整的餐次发布-取消流程
模拟客户端API调用进行完整测试
"""

import requests
import json
import time
from datetime import datetime

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_DATE = "2025-09-24"
TEST_SLOT = "lunch"

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.user_info = None
    
    def login_admin(self, admin_name):
        """模拟管理员登录"""
        print(f"\n=== 模拟管理员{admin_name}登录 ===")
        
        # 1. 微信登录（模拟）
        login_data = {
            "code": f"mock_code_for_admin_{admin_name.lower()}"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/wechat/login", json=login_data)
        if response.status_code != 200:
            raise Exception(f"登录失败: {response.text}")
        
        login_result = response.json()
        if not login_result.get('success'):
            raise Exception(f"登录失败: {login_result.get('error')}")
        
        self.token = login_result['data']['access_token']
        print(f"✅ 获取token成功")
        
        # 2. 注册用户（如果需要）
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
            
            print(f"✅ 用户注册成功")
        
        # 3. 获取用户信息
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/auth/me", headers=headers)
        if response.status_code != 200:
            raise Exception(f"获取用户信息失败: {response.text}")
        
        me_result = response.json()
        if not me_result.get('success'):
            raise Exception(f"获取用户信息失败: {me_result.get('error')}")
        
        self.user_info = me_result['data']
        print(f"✅ 用户信息: {self.user_info['wechat_name']}, is_admin: {self.user_info['is_admin']}")
        
        if not self.user_info['is_admin']:
            raise Exception(f"用户{admin_name}不是管理员")
        
        return self.token
    
    def get_calendar_meals(self, start_date, end_date):
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
        
        return result['data']['meals']
    
    def publish_meal(self, date, slot, description, base_price_cents, addon_config, max_orders):
        """发布餐次"""
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {
            "date": date,
            "slot": slot,
            "description": description,
            "base_price_cents": base_price_cents,
            "addon_config": addon_config,
            "max_orders": max_orders
        }
        
        response = requests.post(f"{self.base_url}/api/admin/meals", json=data, headers=headers)
        if response.status_code not in [200, 201]:
            raise Exception(f"发布餐次失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"发布餐次失败: {result.get('error')}")
        
        return result['data']
    
    def cancel_meal(self, meal_id):
        """取消餐次"""
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {
            "cancel_reason": "情景测试取消"
        }
        
        response = requests.delete(f"{self.base_url}/api/admin/meals/{meal_id}", json=data, headers=headers)
        if response.status_code != 200:
            raise Exception(f"取消餐次失败: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"取消餐次失败: {result.get('error')}")
        
        return result['data']

def find_meal_by_date_slot(meals, date, slot):
    """在餐次列表中查找指定日期和时段的餐次"""
    for meal in meals:
        if meal['date'] == date and meal['slot'] == slot:
            return meal
    return None

def main():
    """主测试流程"""
    print("🚀 开始情景测试1: 完整的餐次发布-取消流程")
    print(f"测试目标: {TEST_DATE} {TEST_SLOT}")
    
    try:
        # 创建两个管理员客户端
        admin_a = APIClient(BASE_URL)
        admin_b = APIClient(BASE_URL)
        
        # 步骤1: 管理员A登录
        print("\n📋 步骤1: 管理员A登录")
        admin_a.login_admin("A")
        
        # 步骤2: 检查管理员A的calendar页面2025年9月24日的午餐，预期状态是未发布
        print(f"\n📋 步骤2: 检查管理员A的calendar页面{TEST_DATE}的午餐状态")
        meals_a = admin_a.get_calendar_meals(TEST_DATE, TEST_DATE)
        lunch_meal_a = find_meal_by_date_slot(meals_a, TEST_DATE, TEST_SLOT)
        
        if lunch_meal_a:
            if lunch_meal_a['status'] == 'unpublished':
                print(f"✅ 预期正确: 午餐状态为未发布")
            else:
                print(f"❌ 预期错误: 午餐状态为 {lunch_meal_a['status']}，应该是未发布")
                return False
        else:
            print(f"✅ 预期正确: 午餐不存在（未发布状态）")
        
        # 步骤3: 管理员A发布午餐
        print(f"\n📋 步骤3: 管理员A发布{TEST_DATE}的午餐")
        
        # 先获取可用附加项
        headers = {"Authorization": f"Bearer {admin_a.token}"}
        response = requests.get(f"{BASE_URL}/api/admin/addons?status=active", headers=headers)
        if response.status_code != 200:
            raise Exception(f"获取附加项失败: {response.text}")
        
        addons_result = response.json()
        if not addons_result.get('success'):
            raise Exception(f"获取附加项失败: {addons_result.get('error')}")
        
        addons = addons_result['data']['addons']
        chicken_leg_addon = None
        for addon in addons:
            if "鸡腿" in addon['name']:
                chicken_leg_addon = addon
                break
        
        if not chicken_leg_addon:
            raise Exception("未找到鸡腿附加项")
        
        # 发布餐次：描述"测试"，附加可以加至多2个鸡腿，订餐限制最多2人
        addon_config = {
            chicken_leg_addon['addon_id']: 2  # 最多2个鸡腿，使用整数键
        }
        
        meal_data = admin_a.publish_meal(
            date=TEST_DATE,
            slot=TEST_SLOT,
            description="测试",
            base_price_cents=1500,  # 15元 = 1500分
            addon_config=addon_config,
            max_orders=2
        )
        
        meal_id = meal_data['meal_id']
        print(f"✅ 餐次发布成功: meal_id={meal_id}")
        
        # 步骤4: 管理员B登录
        print(f"\n📋 步骤4: 管理员B登录")
        admin_b.login_admin("B")
        
        # 步骤5: 检查管理员B的calendar页面，预期状态是已发布，且进度是 0/2
        print(f"\n📋 步骤5: 检查管理员B的calendar页面{TEST_DATE}午餐状态")
        meals_b = admin_b.get_calendar_meals(TEST_DATE, TEST_DATE)
        lunch_meal_b = find_meal_by_date_slot(meals_b, TEST_DATE, TEST_SLOT)
        
        if not lunch_meal_b:
            print(f"❌ 错误: 管理员B看不到午餐")
            return False
        
        if lunch_meal_b['status'] != 'published':
            print(f"❌ 错误: 午餐状态为 {lunch_meal_b['status']}，应该是已发布")
            return False
        
        if lunch_meal_b['current_orders'] != 0 or lunch_meal_b['max_orders'] != 2:
            print(f"❌ 错误: 订单进度为 {lunch_meal_b['current_orders']}/{lunch_meal_b['max_orders']}，应该是 0/2")
            return False
        
        print(f"✅ 预期正确: 午餐状态为已发布，进度为 {lunch_meal_b['current_orders']}/{lunch_meal_b['max_orders']}")
        
        # 步骤6: 再次检查管理员A的calendar页面，预期状态是已发布，且进度是 0/2
        print(f"\n📋 步骤6: 再次检查管理员A的calendar页面{TEST_DATE}午餐状态")
        meals_a2 = admin_a.get_calendar_meals(TEST_DATE, TEST_DATE)
        lunch_meal_a2 = find_meal_by_date_slot(meals_a2, TEST_DATE, TEST_SLOT)
        
        if not lunch_meal_a2:
            print(f"❌ 错误: 管理员A看不到午餐")
            return False
        
        if lunch_meal_a2['status'] != 'published':
            print(f"❌ 错误: 午餐状态为 {lunch_meal_a2['status']}，应该是已发布")
            return False
        
        if lunch_meal_a2['current_orders'] != 0 or lunch_meal_a2['max_orders'] != 2:
            print(f"❌ 错误: 订单进度为 {lunch_meal_a2['current_orders']}/{lunch_meal_a2['max_orders']}，应该是 0/2")
            return False
        
        print(f"✅ 预期正确: 午餐状态为已发布，进度为 {lunch_meal_a2['current_orders']}/{lunch_meal_a2['max_orders']}")
        
        # 步骤7: 管理员A取消午餐
        print(f"\n📋 步骤7: 管理员A取消{TEST_DATE}的午餐")
        cancel_result = admin_a.cancel_meal(meal_id)
        print(f"✅ 餐次取消成功: meal_id={cancel_result.get('meal_id', meal_id)}")
        
        # 步骤8: 检查管理员A的calendar页面，预期状态是未发布
        print(f"\n📋 步骤8: 检查管理员A的calendar页面{TEST_DATE}午餐状态")
        meals_a3 = admin_a.get_calendar_meals(TEST_DATE, TEST_DATE)
        lunch_meal_a3 = find_meal_by_date_slot(meals_a3, TEST_DATE, TEST_SLOT)
        
        if not lunch_meal_a3:
            print(f"✅ 预期正确: 午餐不存在（未发布状态）")
        elif lunch_meal_a3['status'] == 'unpublished':
            print(f"✅ 预期正确: 午餐状态为未发布")
        else:
            print(f"❌ 错误: 午餐状态为 {lunch_meal_a3['status']}，应该是未发布")
            return False
        
        # 步骤9: 检查管理员B的calendar页面，预期状态是未发布
        print(f"\n📋 步骤9: 检查管理员B的calendar页面{TEST_DATE}午餐状态")
        meals_b2 = admin_b.get_calendar_meals(TEST_DATE, TEST_DATE)
        lunch_meal_b2 = find_meal_by_date_slot(meals_b2, TEST_DATE, TEST_SLOT)
        
        if not lunch_meal_b2:
            print(f"✅ 预期正确: 午餐不存在（未发布状态）")
        elif lunch_meal_b2['status'] == 'unpublished':
            print(f"✅ 预期正确: 午餐状态为未发布")
        else:
            print(f"❌ 错误: 午餐状态为 {lunch_meal_b2['status']}，应该是未发布")
            return False
        
        print(f"\n🎉 情景测试1完全成功！")
        print("✅ 所有步骤都符合预期")
        return True
        
    except Exception as e:
        print(f"\n❌ 情景测试1失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)