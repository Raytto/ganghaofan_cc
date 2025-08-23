# 业务情景测试
# 测试完整的业务流程：创建附加项 -> 创建餐次 -> 下单 -> 取消订单 -> 再下单 -> 取消餐次 -> 再创建餐次 -> 下单 -> 锁定餐次 -> 尝试下单

import sys
import os
from pathlib import Path
import traceback

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.manager import DatabaseManager
from db.core_operations import CoreOperations
from db.supporting_operations import SupportingOperations


class ScenarioTester:
    def __init__(self):
        self.db = DatabaseManager("data/gang_hao_fan.db", auto_connect=True)
        self.core_ops = CoreOperations(self.db)
        self.support_ops = SupportingOperations(self.db)
        
        self.test_results = []
        self.admin_user_id = None
        self.normal_user_id = None
        self.addon_id = None
        self.meal_id = None
        self.order_id = None
    
    def log(self, message, is_step=False):
        """记录测试日志"""
        if is_step:
            print(f"\n=== {message} ===")
        else:
            print(f"  {message}")
        self.test_results.append(message)
    
    def verify_balance(self, user_id, expected_cents, step_name):
        """验证用户余额"""
        user_info = self.support_ops.get_user_by_id(user_id)
        actual_cents = user_info['balance_cents']
        expected_yuan = expected_cents / 100
        actual_yuan = actual_cents / 100
        
        if actual_cents == expected_cents:
            self.log(f"✅ {step_name}: 余额验证通过 ({actual_yuan}元)")
            return True
        else:
            self.log(f"❌ {step_name}: 余额验证失败，期望{expected_yuan}元，实际{actual_yuan}元")
            return False
    
    def setup_test_data(self):
        """设置测试数据"""
        self.log("设置测试数据", is_step=True)
        
        # 1. 创建管理员用户
        admin_result = self.support_ops.register_user(
            open_id="scenario_admin",
            wechat_name="情景测试管理员",
            avatar_url="http://test.com/admin.jpg"
        )
        self.admin_user_id = admin_result['user_id']
        
        # 设置管理员权限
        self.support_ops.db.execute_single(
            "UPDATE users SET is_admin = TRUE WHERE user_id = ?",
            [self.admin_user_id]
        )
        self.log(f"创建管理员用户: ID={self.admin_user_id}")
        
        # 2. 创建普通用户
        user_result = self.support_ops.register_user(
            open_id="scenario_user",
            wechat_name="情景测试用户",
            avatar_url="http://test.com/user.jpg"
        )
        self.normal_user_id = user_result['user_id']
        self.log(f"创建普通用户: ID={self.normal_user_id}")
        
        # 3. 给用户充值
        balance_result = self.core_ops.admin_adjust_balance(
            admin_user_id=self.admin_user_id,
            target_user_id=self.normal_user_id,
            amount_cents=10000,  # 100元
            reason="情景测试初始充值"
        )
        self.log(f"用户充值: {balance_result['adjustment_amount']/100}元")
        self.verify_balance(self.normal_user_id, 10000, "初始充值")
    
    def test_create_addon(self):
        """测试创建附加项"""
        self.log("创建附加项", is_step=True)
        
        result = self.core_ops.admin_create_addon(
            admin_user_id=self.admin_user_id,
            name="情景测试附加项",
            price_cents=300,  # 3元
            display_order=1
        )
        
        self.addon_id = result['addon_id']
        self.log(f"✅ 创建附加项成功: ID={self.addon_id}, 价格=3元")
        return True
    
    def test_create_meal_with_addon(self):
        """测试创建带附加项的餐次"""
        self.log("创建带附加项的餐次", is_step=True)
        
        result = self.core_ops.admin_publish_meal(
            admin_user_id=self.admin_user_id,
            date="2024-12-25",
            slot="lunch",
            description="情景测试餐次",
            base_price_cents=1500,  # 15元
            addon_config={self.addon_id: 2},  # 最多选择2个附加项
            max_orders=10
        )
        
        self.meal_id = result['meal_id']
        self.log(f"✅ 创建餐次成功: ID={self.meal_id}, 基础价格=15元, 附加项最多2个")
        return True
    
    def test_create_order(self):
        """测试创建订单"""
        self.log("创建订单（选择1个附加项）", is_step=True)
        
        result = self.core_ops.create_order(
            user_id=self.normal_user_id,
            meal_id=self.meal_id,
            addon_selections={self.addon_id: 1}  # 选择1个附加项
        )
        
        self.order_id = result['order_id']
        expected_amount = 1500 + 300  # 15元基础 + 3元附加项 = 18元
        actual_amount = result['amount_cents']
        
        if actual_amount == expected_amount:
            self.log(f"✅ 创建订单成功: ID={self.order_id}, 金额={actual_amount/100}元")
            # 余额应该从100元减少到82元
            self.verify_balance(self.normal_user_id, 8200, "下单后余额")
            return True
        else:
            self.log(f"❌ 订单金额错误: 期望{expected_amount/100}元，实际{actual_amount/100}元")
            return False
    
    def test_cancel_order(self):
        """测试取消订单"""
        self.log("取消订单", is_step=True)
        
        result = self.core_ops.cancel_order(
            user_id=self.normal_user_id,
            order_id=self.order_id,
            cancel_reason="情景测试取消"
        )
        
        refund_amount = result['refund_amount']
        if refund_amount == 1800:  # 18元
            self.log(f"✅ 取消订单成功: 退款={refund_amount/100}元")
            # 余额应该恢复到100元
            self.verify_balance(self.normal_user_id, 10000, "取消订单后余额")
            return True
        else:
            self.log(f"❌ 退款金额错误: 期望18元，实际{refund_amount/100}元")
            return False
    
    def test_create_order_again(self):
        """测试再次创建订单"""
        self.log("再次创建订单（选择2个附加项）", is_step=True)
        
        result = self.core_ops.create_order(
            user_id=self.normal_user_id,
            meal_id=self.meal_id,
            addon_selections={self.addon_id: 2}  # 选择2个附加项
        )
        
        self.order_id = result['order_id']
        expected_amount = 1500 + 600  # 15元基础 + 6元附加项 = 21元
        actual_amount = result['amount_cents']
        
        if actual_amount == expected_amount:
            self.log(f"✅ 再次创建订单成功: ID={self.order_id}, 金额={actual_amount/100}元")
            # 余额应该从100元减少到79元
            self.verify_balance(self.normal_user_id, 7900, "再次下单后余额")
            return True
        else:
            self.log(f"❌ 订单金额错误: 期望{expected_amount/100}元，实际{actual_amount/100}元")
            return False
    
    def test_cancel_meal(self):
        """测试取消餐次"""
        self.log("取消餐次", is_step=True)
        
        result = self.core_ops.admin_cancel_meal(
            admin_user_id=self.admin_user_id,
            meal_id=self.meal_id,
            cancel_reason="情景测试取消餐次"
        )
        
        canceled_orders = result['canceled_orders_count']
        if canceled_orders == 1:
            self.log(f"✅ 取消餐次成功: 取消了{canceled_orders}个订单")
            # 余额应该恢复到100元
            self.verify_balance(self.normal_user_id, 10000, "取消餐次后余额")
            return True
        else:
            self.log(f"❌ 取消餐次失败: 应取消1个订单，实际取消{canceled_orders}个")
            return False
    
    def test_create_meal_again(self):
        """测试再次创建餐次"""
        self.log("再次创建餐次", is_step=True)
        
        result = self.core_ops.admin_publish_meal(
            admin_user_id=self.admin_user_id,
            date="2024-12-26",
            slot="dinner",
            description="情景测试餐次2",
            base_price_cents=2000,  # 20元
            addon_config={self.addon_id: 1},  # 最多选择1个附加项
            max_orders=5
        )
        
        self.meal_id = result['meal_id']
        self.log(f"✅ 再次创建餐次成功: ID={self.meal_id}, 基础价格=20元")
        return True
    
    def test_create_order_new_meal(self):
        """测试在新餐次下单"""
        self.log("在新餐次下单", is_step=True)
        
        result = self.core_ops.create_order(
            user_id=self.normal_user_id,
            meal_id=self.meal_id,
            addon_selections={self.addon_id: 1}  # 选择1个附加项
        )
        
        self.order_id = result['order_id']
        expected_amount = 2000 + 300  # 20元基础 + 3元附加项 = 23元
        actual_amount = result['amount_cents']
        
        if actual_amount == expected_amount:
            self.log(f"✅ 在新餐次下单成功: ID={self.order_id}, 金额={actual_amount/100}元")
            # 余额应该从100元减少到77元
            self.verify_balance(self.normal_user_id, 7700, "新餐次下单后余额")
            return True
        else:
            self.log(f"❌ 订单金额错误: 期望{expected_amount/100}元，实际{actual_amount/100}元")
            return False
    
    def test_lock_meal(self):
        """测试锁定餐次"""
        self.log("锁定餐次", is_step=True)
        
        result = self.core_ops.admin_lock_meal(
            admin_user_id=self.admin_user_id,
            meal_id=self.meal_id
        )
        
        self.log(f"✅ 锁定餐次成功: 当前订单数={result['current_orders']}")
        return True
    
    def test_create_order_locked_meal(self):
        """测试在锁定餐次下单（应该失败）"""
        self.log("尝试在锁定餐次下单（应该失败）", is_step=True)
        
        # 先创建另一个用户
        user2_result = self.support_ops.register_user(
            open_id="scenario_user2",
            wechat_name="情景测试用户2",
            avatar_url="http://test.com/user2.jpg"
        )
        user2_id = user2_result['user_id']
        
        # 给新用户充值
        self.core_ops.admin_adjust_balance(
            admin_user_id=self.admin_user_id,
            target_user_id=user2_id,
            amount_cents=5000,
            reason="测试充值"
        )
        
        try:
            result = self.core_ops.create_order(
                user_id=user2_id,
                meal_id=self.meal_id,
                addon_selections={}
            )
            self.log("❌ 在锁定餐次下单应该失败，但成功了")
            return False
        except Exception as e:
            if "锁定" in str(e) or "published" in str(e):
                self.log("✅ 在锁定餐次下单正确失败")
                return True
            else:
                self.log(f"❌ 失败原因不正确: {str(e)}")
                return False
    
    def run_all_tests(self):
        """运行所有测试"""
        self.log("开始业务情景测试", is_step=True)
        
        test_steps = [
            ("设置测试数据", self.setup_test_data),
            ("创建附加项", self.test_create_addon),
            ("创建带附加项的餐次", self.test_create_meal_with_addon),
            ("创建订单", self.test_create_order),
            ("取消订单", self.test_cancel_order),
            ("再次创建订单", self.test_create_order_again),
            ("取消餐次", self.test_cancel_meal),
            ("再次创建餐次", self.test_create_meal_again),
            ("在新餐次下单", self.test_create_order_new_meal),
            ("锁定餐次", self.test_lock_meal),
            ("尝试在锁定餐次下单", self.test_create_order_locked_meal)
        ]
        
        passed = 0
        failed = 0
        
        for step_name, test_func in test_steps:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"❌ {step_name} 执行异常: {str(e)}")
                self.log(f"异常详情: {traceback.format_exc()}")
                failed += 1
        
        self.log("情景测试完成", is_step=True)
        self.log(f"通过: {passed}/{len(test_steps)}")
        self.log(f"失败: {failed}/{len(test_steps)}")
        
        if failed == 0:
            self.log("🎉 所有情景测试通过！")
            return True
        else:
            self.log("💥 部分情景测试失败")
            return False
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == "__main__":
    tester = ScenarioTester()
    try:
        success = tester.run_all_tests()
        exit_code = 0 if success else 1
    except Exception as e:
        print(f"情景测试执行异常: {e}")
        print(traceback.format_exc())
        exit_code = 1
    finally:
        tester.close()
    
    sys.exit(exit_code)