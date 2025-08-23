# 参考文档: doc/db/core_operations.md
# 核心业务操作测试

import pytest
from datetime import datetime


class TestAdminOperations:
    """管理员操作测试"""
    
    def test_admin_create_addon(self, core_ops, sample_admin_user):
        """测试管理员创建附加项"""
        result = core_ops.admin_create_addon(
            admin_user_id=sample_admin_user,
            name="加鸡蛋",
            price_cents=200,
            display_order=2
        )
        
        assert result['addon_id'] is not None
        assert "加鸡蛋" in result['message']
        assert result.get('success', True)
    
    def test_admin_create_addon_duplicate_name(self, core_ops, sample_admin_user, sample_addon):
        """测试创建重复名称的附加项"""
        # 先获取已存在附加项的名称
        addon_info = core_ops.db.execute_single(
            "SELECT name FROM addons WHERE addon_id = ?", [sample_addon]
        ).fetchone()
        
        with pytest.raises(Exception):
            core_ops.admin_create_addon(
                admin_user_id=sample_admin_user,
                name=addon_info[0],  # 使用重复名称
                price_cents=300,
                display_order=1
            )
    
    def test_admin_deactivate_addon(self, core_ops, sample_admin_user, sample_addon):
        """测试管理员停用附加项"""
        result = core_ops.admin_deactivate_addon(
            admin_user_id=sample_admin_user,
            addon_id=sample_addon
        )
        
        assert result['addon_id'] == sample_addon
        assert "已停用" in result['message']
        assert result.get('success', True)
    
    def test_admin_publish_meal(self, core_ops, sample_admin_user, sample_addon):
        """测试管理员发布餐次"""
        result = core_ops.admin_publish_meal(
            admin_user_id=sample_admin_user,
            date="2024-12-26",
            slot="dinner",
            description="圣诞晚餐",
            base_price_cents=2000,
            addon_config={sample_addon: 3},
            max_orders=20
        )
        
        assert result['meal_id'] is not None
        assert result['date'] == "2024-12-26"
        assert result['slot'] == "dinner"
        assert "发布成功" in result['message']
    
    def test_admin_lock_meal(self, core_ops, sample_admin_user, sample_meal):
        """测试管理员锁定餐次"""
        result = core_ops.admin_lock_meal(
            admin_user_id=sample_admin_user,
            meal_id=sample_meal
        )
        
        assert result['meal_id'] == sample_meal
        assert "已锁定" in result['message']
    
    def test_admin_complete_meal(self, core_ops, sample_admin_user, sample_meal):
        """测试管理员完成餐次"""
        result = core_ops.admin_complete_meal(
            admin_user_id=sample_admin_user,
            meal_id=sample_meal
        )
        
        assert result['meal_id'] == sample_meal
        assert "已完成" in result['message']
    
    def test_admin_cancel_meal(self, core_ops, sample_admin_user):
        """测试管理员取消餐次"""
        # 先创建一个新餐次用于取消测试
        meal_result = core_ops.admin_publish_meal(
            admin_user_id=sample_admin_user,
            date="2024-12-27",
            slot="lunch",
            description="待取消餐次",
            base_price_cents=1000,
            addon_config={},
            max_orders=10
        )
        meal_id = meal_result['meal_id']
        
        result = core_ops.admin_cancel_meal(
            admin_user_id=sample_admin_user,
            meal_id=meal_id,
            cancel_reason="测试取消"
        )
        
        assert result['meal_id'] == meal_id
        assert result['cancel_reason'] == "测试取消"
        assert "取消成功" in result['message']
    
    def test_admin_adjust_balance(self, core_ops, sample_admin_user, sample_user):
        """测试管理员调整用户余额"""
        # 测试充值
        result = core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=5000,
            reason="测试充值"
        )
        
        assert result['target_user_id'] == sample_user
        assert result['adjustment_amount'] == 5000
        assert result['balance_after'] == 5000
        assert "充值" in result['operation_type']
        
        # 测试扣款
        deduct_result = core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=-1000,
            reason="测试扣款"
        )
        
        assert deduct_result['adjustment_amount'] == -1000
        assert deduct_result['balance_after'] == 4000
        assert "扣除" in deduct_result['operation_type']


class TestUserOperations:
    """用户操作测试"""
    
    def test_create_order_success(self, core_ops, sample_admin_user, sample_user, sample_meal, sample_addon):
        """测试用户成功下单"""
        # 先给用户充值
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=3000,
            reason="测试充值"
        )
        
        result = core_ops.create_order(
            user_id=sample_user,
            meal_id=sample_meal,
            addon_selections={sample_addon: 1}
        )
        
        assert result['order_id'] is not None
        assert result['meal_id'] == sample_meal
        assert result['amount_cents'] == 1800  # 1500 + 300
        assert "创建成功" in result['message']
    
    def test_create_order_insufficient_balance(self, core_ops, sample_user, sample_meal):
        """测试余额不足下单失败"""
        with pytest.raises(Exception) as exc_info:
            core_ops.create_order(
                user_id=sample_user,
                meal_id=sample_meal,
                addon_selections={}
            )
        
        assert "余额不足" in str(exc_info.value)
    
    def test_cancel_order(self, core_ops, sample_admin_user, sample_user, sample_meal, sample_addon):
        """测试用户取消订单"""
        # 先给用户充值并下单
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=3000,
            reason="测试充值"
        )
        
        order_result = core_ops.create_order(
            user_id=sample_user,
            meal_id=sample_meal,
            addon_selections={sample_addon: 1}
        )
        order_id = order_result['order_id']
        
        # 取消订单
        cancel_result = core_ops.cancel_order(
            user_id=sample_user,
            order_id=order_id,
            cancel_reason="测试取消"
        )
        
        assert cancel_result['order_id'] == order_id
        assert cancel_result['refund_amount'] == 1800
        assert "已取消" in cancel_result['message']


class TestValidations:
    """验证逻辑测试"""
    
    def test_non_admin_operations_fail(self, core_ops, sample_user):
        """测试非管理员操作失败"""
        with pytest.raises(Exception) as exc_info:
            core_ops.admin_create_addon(
                admin_user_id=sample_user,  # 普通用户
                name="非法附加项",
                price_cents=100,
                display_order=1
            )
        
        assert "不是管理员" in str(exc_info.value) or "权限" in str(exc_info.value)
    
    def test_meal_capacity_limit(self, core_ops, sample_admin_user, sample_user):
        """测试餐次容量限制"""
        # 创建只能1人订餐的餐次
        meal_result = core_ops.admin_publish_meal(
            admin_user_id=sample_admin_user,
            date="2024-12-28",
            slot="lunch",
            description="限量餐次",
            base_price_cents=1000,
            addon_config={},
            max_orders=1
        )
        meal_id = meal_result['meal_id']
        
        # 给用户充值
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=3000,
            reason="测试充值"
        )
        
        # 第一个用户下单成功
        core_ops.create_order(
            user_id=sample_user,
            meal_id=meal_id,
            addon_selections={}
        )
        
        # 创建第二个用户
        user2_result = core_ops.db.execute_single("""
            INSERT INTO users (user_id, open_id, wechat_name, balance_cents, status)
            VALUES ((SELECT COALESCE(MAX(user_id), 0) + 1 FROM users), 'test_user2', '测试用户2', 2000, 'active')
            RETURNING user_id
        """).fetchone()
        user2_id = user2_result[0]
        
        # 第二个用户下单应该失败
        with pytest.raises(Exception) as exc_info:
            core_ops.create_order(
                user_id=user2_id,
                meal_id=meal_id,
                addon_selections={}
            )
        
        assert "已满" in str(exc_info.value) or "无法下单" in str(exc_info.value)
    
    def test_duplicate_order_prevention(self, core_ops, sample_admin_user, sample_user, sample_meal):
        """测试防重复下单"""
        # 给用户充值
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=5000,
            reason="测试充值"
        )
        
        # 第一次下单
        core_ops.create_order(
            user_id=sample_user,
            meal_id=sample_meal,
            addon_selections={}
        )
        
        # 第二次下单应该失败
        with pytest.raises(Exception) as exc_info:
            core_ops.create_order(
                user_id=sample_user,
                meal_id=sample_meal,
                addon_selections={}
            )
        
        assert "已有" in str(exc_info.value) or "重复" in str(exc_info.value)