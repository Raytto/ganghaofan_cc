# 参考文档: doc/db/query_operations.md
# 查询业务操作测试

import pytest
from datetime import datetime, timedelta


class TestMealQueries:
    """餐次查询测试"""
    
    def test_query_meals_by_date_range(self, query_ops, core_ops, sample_admin_user, sample_addon):
        """测试按日期范围查询餐次"""
        # 创建测试餐次
        core_ops.admin_publish_meal(
            admin_user_id=sample_admin_user,
            date="2024-12-25",
            slot="lunch",
            description="圣诞午餐",
            base_price_cents=1500,
            addon_config={sample_addon: 2},
            max_orders=20
        )
        
        core_ops.admin_publish_meal(
            admin_user_id=sample_admin_user,
            date="2024-12-25",
            slot="dinner",
            description="圣诞晚餐",
            base_price_cents=2000,
            addon_config={sample_addon: 3},
            max_orders=30
        )
        
        # 查询餐次
        result = query_ops.query_meals_by_date_range(
            start_date="2024-12-24",
            end_date="2024-12-26"
        )
        
        assert result['success'] is True
        assert len(result['data']['meals']) == 2
        assert result['data']['pagination']['total_count'] == 2
        
        # 验证餐次数据
        meals = result['data']['meals']
        lunch_meal = next(m for m in meals if m['slot'] == 'lunch')
        dinner_meal = next(m for m in meals if m['slot'] == 'dinner')
        
        assert lunch_meal['description'] == "圣诞午餐"
        assert lunch_meal['base_price_cents'] == 1500
        assert lunch_meal['max_orders'] == 20
        
        assert dinner_meal['description'] == "圣诞晚餐"
        assert dinner_meal['base_price_cents'] == 2000
        assert dinner_meal['max_orders'] == 30
    
    def test_query_meal_detail(self, query_ops, core_ops, sample_admin_user, sample_meal, sample_user, sample_addon):
        """测试查询餐次详情"""
        # 先给用户充值并下单
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=3000,
            reason="测试充值"
        )
        
        core_ops.create_order(
            user_id=sample_user,
            meal_id=sample_meal,
            addon_selections={sample_addon: 1}
        )
        
        # 查询餐次详情
        result = query_ops.query_meal_detail(sample_meal)
        
        assert result['success'] is True
        meal_data = result['data']
        
        # 验证餐次基本信息
        assert meal_data['meal_id'] == sample_meal
        assert meal_data['description'] == "测试餐次"
        assert meal_data['base_price_cents'] == 1500
        assert meal_data['current_orders'] == 1
        
        # 验证附加项信息
        assert len(meal_data['available_addons']) > 0
        addon_info = meal_data['available_addons'][0]
        assert addon_info['addon_id'] == sample_addon
        assert addon_info['status'] == 'active'
        
        # 验证订餐用户信息
        assert len(meal_data['ordered_users']) == 1
        ordered_user = meal_data['ordered_users'][0]
        assert ordered_user['user_id'] == sample_user
        assert ordered_user['amount_cents'] == 1800  # 1500 + 300


class TestUserQueries:
    """用户查询测试"""
    
    def test_query_user_meal_order(self, query_ops, core_ops, sample_admin_user, sample_user, sample_meal, sample_addon):
        """测试查询用户餐次订单"""
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
        
        # 查询用户餐次订单
        result = query_ops.query_user_meal_order(sample_user, sample_meal)
        
        assert result['success'] is True
        order_data = result['data']
        
        assert order_data['has_order'] is True
        assert order_data['order_id'] == order_result['order_id']
        assert order_data['order_status'] == 'active'
        assert order_data['amount_cents'] == 1800
    
    def test_query_user_meal_order_no_order(self, query_ops, sample_user, sample_meal):
        """测试查询用户无订单的餐次"""
        result = query_ops.query_user_meal_order(sample_user, sample_meal)
        
        assert result['success'] is True
        assert result['data']['has_order'] is False
    
    def test_query_user_ledger_history(self, query_ops, core_ops, sample_admin_user, sample_user):
        """测试查询用户账单历史"""
        # 创建一些交易记录
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=5000,
            reason="第一次充值"
        )
        
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=2000,
            reason="第二次充值"
        )
        
        # 查询账单历史
        result = query_ops.query_user_ledger_history(sample_user)
        
        assert result['success'] is True
        ledger_data = result['data']
        
        assert ledger_data['user_info']['user_id'] == sample_user
        assert ledger_data['user_info']['current_balance_yuan'] == 70.0  # 7000分
        
        # 验证账单记录
        records = ledger_data['ledger_records']
        assert len(records) == 2
        
        # 记录按时间倒序排列，最新的在前
        latest_record = records[0]
        assert latest_record['type'] == 'recharge'
        assert latest_record['direction'] == 'in'
        assert latest_record['amount_yuan'] == 20.0
    
    def test_query_user_order_statistics(self, query_ops, core_ops, sample_admin_user, sample_user, sample_meal, sample_addon):
        """测试查询用户订单统计"""
        # 给用户充值
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=5000,
            reason="测试充值"
        )
        
        # 创建订单
        order_result = core_ops.create_order(
            user_id=sample_user,
            meal_id=sample_meal,
            addon_selections={sample_addon: 1}
        )
        
        # 查询订单统计
        stats = query_ops.query_user_order_statistics(sample_user)
        
        assert stats['total_orders'] == 1
        assert stats['active_orders'] == 1
        assert stats['completed_orders'] == 0
        assert stats['canceled_orders'] == 0
        assert stats['total_spent_yuan'] == 18.0  # 1800分
    
    def test_query_user_transaction_statistics(self, query_ops, core_ops, sample_admin_user, sample_user):
        """测试查询用户交易统计"""
        # 创建充值记录
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=3000,
            reason="第一次充值"
        )
        
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=2000,
            reason="第二次充值"
        )
        
        # 查询交易统计
        stats = query_ops.query_user_transaction_statistics(sample_user)
        
        assert stats['total_transactions'] == 2
        assert stats['recharge_count'] == 2
        assert stats['total_recharged_yuan'] == 50.0  # 5000分
    
    def test_query_user_orders(self, query_ops, core_ops, sample_admin_user, sample_user, sample_meal, sample_addon):
        """测试查询用户订单列表"""
        # 给用户充值并下单
        core_ops.admin_adjust_balance(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            amount_cents=5000,
            reason="测试充值"
        )
        
        order_result = core_ops.create_order(
            user_id=sample_user,
            meal_id=sample_meal,
            addon_selections={sample_addon: 1}
        )
        
        # 查询订单列表
        result = query_ops.query_user_orders(sample_user)
        
        assert result['success'] is True
        orders_data = result['data']
        
        assert orders_data['user_info']['user_id'] == sample_user
        
        orders = orders_data['orders']
        assert len(orders) == 1
        
        order = orders[0]
        assert order['order_id'] == order_result['order_id']
        assert order['status'] == 'active'
        assert order['amount_yuan'] == 18.0
        assert order['meal_info']['meal_id'] == sample_meal


class TestPagination:
    """分页测试"""
    
    def test_meals_pagination(self, query_ops, core_ops, sample_admin_user, sample_addon):
        """测试餐次分页查询"""
        # 创建多个测试餐次
        dates = ["2024-12-20", "2024-12-21", "2024-12-22", "2024-12-23", "2024-12-24"]
        for i, date in enumerate(dates):
            core_ops.admin_publish_meal(
                admin_user_id=sample_admin_user,
                date=date,
                slot="lunch",
                description=f"测试餐次{i+1}",
                base_price_cents=1500,
                addon_config={sample_addon: 2},
                max_orders=20
            )
        
        # 测试第一页（前3个）
        result = query_ops.query_meals_by_date_range(
            start_date="2024-12-19",
            end_date="2024-12-25",
            offset=0,
            limit=3
        )
        
        assert result['success'] is True
        meals = result['data']['meals']
        pagination = result['data']['pagination']
        
        assert len(meals) == 3
        assert pagination['total_count'] == 5
        assert pagination['total_pages'] == 2
        assert pagination['current_page'] == 1
        assert pagination['has_next'] is True
        assert pagination['has_prev'] is False
        
        # 测试第二页（剩余2个）
        result2 = query_ops.query_meals_by_date_range(
            start_date="2024-12-19",
            end_date="2024-12-25",
            offset=3,
            limit=3
        )
        
        meals2 = result2['data']['meals']
        pagination2 = result2['data']['pagination']
        
        assert len(meals2) == 2
        assert pagination2['current_page'] == 2
        assert pagination2['has_next'] is False
        assert pagination2['has_prev'] is True


class TestErrorHandling:
    """错误处理测试"""
    
    def test_query_nonexistent_meal(self, query_ops):
        """测试查询不存在的餐次"""
        result = query_ops.query_meal_detail(99999)
        
        assert result['success'] is False
        assert "不存在" in result.get('error', '') or "不存在" in result.get('message', '')
    
    def test_query_nonexistent_user_orders(self, query_ops):
        """测试查询不存在用户的订单"""
        result = query_ops.query_user_orders(99999)
        
        assert result['success'] is False
        assert "不存在" in result.get('error', '') or "不存在" in result.get('message', '')
    
    def test_invalid_date_range(self, query_ops):
        """测试无效的日期范围"""
        with pytest.raises(Exception) as exc_info:
            query_ops.query_meals_by_date_range(
                start_date="2024-12-25",
                end_date="2024-12-20"  # 结束日期早于开始日期
            )
        
        assert "日期" in str(exc_info.value)