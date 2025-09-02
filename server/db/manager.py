# 参考文档: doc/db/db_manager.md
# 数据库连接和事务管理的核心组件

import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from contextlib import contextmanager

class DatabaseManager:
    """
    数据库管理器
    
    负责SQLite数据库连接管理、事务处理和基础操作
    参考文档: doc/db/db_manager.md
    """
    
    def __init__(self, db_path: str, auto_connect: bool = False):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
            auto_connect: 是否自动连接数据库
        """
        self.db_path = db_path
        self.conn = None
        self._is_connected = False
        
        # 配置日志
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if auto_connect:
            self.connect()
    
    def connect(self) -> sqlite3.Connection:
        """
        建立数据库连接
        
        Returns:
            SQLite连接对象
        
        Raises:
            ConnectionError: 连接失败时抛出异常
        """
        try:
            if self.conn is not None:
                self.logger.warning("数据库连接已存在，先关闭现有连接")
                self.close()
            
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info(f"创建数据库目录: {db_dir}")
            
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self._is_connected = True
            self.logger.info(f"成功连接到数据库: {self.db_path}")
            
            # 设置SQLite优化参数
            self._configure_database()
            
            return self.conn
            
        except Exception as e:
            self.logger.error(f"连接数据库失败: {str(e)}")
            raise ConnectionError(f"无法连接到数据库 {self.db_path}: {str(e)}")
    
    def close(self):
        """
        关闭数据库连接
        """
        if self.conn is not None:
            try:
                self.conn.close()
                self.logger.info("数据库连接已关闭")
            except Exception as e:
                self.logger.error(f"关闭数据库连接时发生错误: {str(e)}")
            finally:
                self.conn = None
                self._is_connected = False
    
    def _configure_database(self):
        """
        配置SQLite优化参数
        """
        try:
            # 设置SQLite优化参数
            optimizations = [
                "PRAGMA foreign_keys = ON",        # 启用外键约束
                "PRAGMA journal_mode = WAL",       # 使用WAL模式提高并发性能
                "PRAGMA synchronous = NORMAL",     # 平衡性能和安全性
                "PRAGMA cache_size = -64000",      # 设置缓存大小为64MB
                "PRAGMA temp_store = MEMORY"       # 临时表存储在内存中
            ]
            
            for opt in optimizations:
                self.conn.execute(opt)
                
            self.logger.debug("数据库优化参数配置完成")
            
        except Exception as e:
            self.logger.warning(f"配置数据库参数时出现警告: {str(e)}")
    
    def is_connected(self) -> bool:
        """
        检查数据库连接状态
        
        Returns:
            连接状态布尔值
        """
        return self._is_connected and self.conn is not None
    
    def ensure_connected(self):
        """
        确保数据库连接可用
        
        Raises:
            ConnectionError: 连接不可用时抛出异常
        """
        if not self.is_connected():
            raise ConnectionError("数据库未连接，请先调用connect()方法")
    
    def execute_transaction(self, operations: List[Callable]) -> List[Any]:
        """
        串行执行事务操作
        
        Args:
            operations: 操作函数列表，每个函数返回操作结果
        
        Returns:
            所有操作结果的列表
            
        Raises:
            ConnectionError: 数据库未连接
            Exception: 事务执行失败时抛出原始异常
        """
        self.ensure_connected()
        
        if not operations:
            self.logger.warning("事务操作列表为空")
            return []
        
        results = []
        transaction_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        try:
            self.logger.debug(f"开始事务 {transaction_id}，包含 {len(operations)} 个操作")
            
            for i, operation in enumerate(operations):
                self.logger.debug(f"执行事务 {transaction_id} 中的操作 {i+1}/{len(operations)}")
                result = operation()
                results.append(result)
            
            self.conn.commit()
            self.logger.info(f"事务 {transaction_id} 提交成功")
            
            return results
            
        except Exception as e:
            self.logger.error(f"事务 {transaction_id} 执行失败: {str(e)}")
            self.logger.error(f"[TRANSACTION_DEBUG] Exception type: {type(e).__name__}")
            self.logger.error(f"[TRANSACTION_DEBUG] Exception details: {repr(e)}")
            try:
                self.conn.rollback()
                self.logger.info(f"事务 {transaction_id} 已回滚")
            except Exception as rollback_error:
                self.logger.error(f"事务回滚失败: {str(rollback_error)}")
            
            raise e
    
    def execute_single(self, query: str, params: List = None) -> Any:
        """
        执行单个SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
        
        Returns:
            查询结果
        """
        self.ensure_connected()
        
        try:
            if params:
                result = self.conn.execute(query, params)
            else:
                result = self.conn.execute(query)
            
            # For SQLite, auto-commit DDL and DML statements
            if query.strip().upper().startswith(('CREATE', 'DROP', 'ALTER', 'INSERT', 'UPDATE', 'DELETE')):
                self.conn.commit()
                
            return result
                
        except Exception as e:
            self.logger.error(f"执行SQL查询失败: {query[:100]}..., 错误: {str(e)}")
            raise e
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        Usage:
            with db_manager.transaction():
                # 执行数据库操作
                db_manager.conn.execute("INSERT ...")
                db_manager.conn.execute("UPDATE ...")
        """
        self.ensure_connected()
        
        try:
            self.logger.debug("手动事务开始")
            yield self.conn
            self.conn.commit()
            self.logger.debug("手动事务提交成功")
        except Exception as e:
            self.logger.error(f"手动事务执行失败: {str(e)}")
            try:
                self.conn.rollback()
                self.logger.debug("手动事务已回滚")
            except Exception as rollback_error:
                self.logger.error(f"手动事务回滚失败: {str(rollback_error)}")
            raise e
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取数据表信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        self.ensure_connected()
        
        try:
            # 获取表结构
            columns_result = self.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            
            if not columns_result:
                raise ValueError(f"表 {table_name} 不存在")
            
            columns = []
            for col in columns_result:
                columns.append({
                    'name': col[1],
                    'type': col[2], 
                    'not_null': bool(col[3]),
                    'default_value': col[4],
                    'primary_key': bool(col[5])
                })
            
            # 获取记录数
            count_result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            record_count = count_result[0] if count_result else 0
            
            return {
                'table_name': table_name,
                'columns': columns,
                'record_count': record_count
            }
            
        except Exception as e:
            self.logger.error(f"获取表 {table_name} 信息失败: {str(e)}")
            raise e
    
    def vacuum(self):
        """
        清理和优化数据库
        """
        self.ensure_connected()
        
        try:
            self.logger.info("开始数据库清理优化")
            self.conn.execute("VACUUM")
            self.logger.info("数据库清理优化完成")
        except Exception as e:
            self.logger.error(f"数据库清理优化失败: {str(e)}")
            raise e
    
    def analyze(self):
        """
        分析数据库统计信息，优化查询计划
        """
        self.ensure_connected()
        
        try:
            self.logger.info("开始数据库统计分析")
            self.conn.execute("ANALYZE")
            self.logger.info("数据库统计分析完成")
        except Exception as e:
            self.logger.error(f"数据库统计分析失败: {str(e)}")
            raise e
    
    def perform_maintenance(self):
        """
        执行完整的数据库维护操作
        """
        self.ensure_connected()
        
        try:
            self.logger.info("开始数据库维护操作")
            
            # 1. 清理和压缩
            self.vacuum()
            
            # 2. 更新统计信息
            self.analyze()
            
            # 3. 检查数据库完整性
            self.check_integrity()
            
            self.logger.info("数据库维护操作全部完成")
            
        except Exception as e:
            self.logger.error(f"数据库维护操作失败: {str(e)}")
            raise e
    
    def check_integrity(self):
        """
        检查数据库完整性
        """
        self.ensure_connected()
        
        try:
            self.logger.info("开始数据库完整性检查")
            
            # 检查核心表是否存在
            core_tables = ['users', 'meals', 'addons', 'orders', 'ledger']
            
            for table in core_tables:
                result = self.conn.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table,)).fetchone()
                
                if not result or result[0] == 0:
                    raise RuntimeError(f"核心表 {table} 不存在")
            
            # 检查主键约束
            integrity_issues = []
            
            # 检查 meals 表主键唯一性
            duplicate_meals = self.conn.execute("""
                SELECT meal_id, COUNT(*) as count 
                FROM meals 
                GROUP BY meal_id 
                HAVING COUNT(*) > 1
            """).fetchall()
            
            if duplicate_meals:
                integrity_issues.extend([f"meals表存在重复的meal_id: {row[0]} (出现{row[1]}次)" for row in duplicate_meals])
            
            # 检查 orders 表主键唯一性
            duplicate_orders = self.conn.execute("""
                SELECT order_id, COUNT(*) as count 
                FROM orders 
                GROUP BY order_id 
                HAVING COUNT(*) > 1
            """).fetchall()
            
            if duplicate_orders:
                integrity_issues.extend([f"orders表存在重复的order_id: {row[0]} (出现{row[1]}次)" for row in duplicate_orders])
            
            # 检查 ledger 表主键唯一性
            duplicate_ledger = self.conn.execute("""
                SELECT ledger_id, COUNT(*) as count 
                FROM ledger 
                GROUP BY ledger_id 
                HAVING COUNT(*) > 1
            """).fetchall()
            
            if duplicate_ledger:
                integrity_issues.extend([f"ledger表存在重复的ledger_id: {row[0]} (出现{row[1]}次)" for row in duplicate_ledger])
            
            if integrity_issues:
                error_msg = "数据库完整性检查发现问题:\n" + "\n".join(integrity_issues)
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            self.logger.info("数据库完整性检查通过")
            
        except Exception as e:
            self.logger.error(f"数据库完整性检查失败: {str(e)}")
            raise e
    
    def check_table_constraints(self, table_name: str = None):
        """
        检查表约束定义
        
        Args:
            table_name: 指定表名，None则检查所有核心表
        """
        self.ensure_connected()
        
        try:
            core_tables = [table_name] if table_name else ['users', 'meals', 'addons', 'orders', 'ledger']
            
            for table in core_tables:
                self.logger.info(f"=== 检查表 {table} 的约束 ===")
                
                # 1. 检查表结构
                try:
                    columns_info = self.conn.execute(f"PRAGMA table_info('{table}')").fetchall()
                    self.logger.info(f"表 {table} 列信息:")
                    for col in columns_info:
                        pk_status = "PRIMARY KEY" if col[5] else ""
                        not_null = "NOT NULL" if col[3] else ""
                        self.logger.info(f"  - {col[1]}: {col[2]} {not_null} {pk_status}")
                except Exception as e:
                    self.logger.error(f"无法获取表 {table} 的列信息: {e}")
                
                # 2. 检查索引
                try:
                    # SQLite 查询索引信息
                    indexes_info = self.conn.execute("""
                        SELECT name, sql FROM sqlite_master 
                        WHERE type='index' AND tbl_name=?
                    """, (table,)).fetchall()
                    
                    self.logger.info(f"表 {table} 索引信息 ({len(indexes_info)} 个索引):")
                    for idx in indexes_info:
                        self.logger.info(f"  - 索引: {idx[0]} -> {idx[1]}")
                        
                except Exception as e:
                    self.logger.warning(f"无法获取表 {table} 的索引信息: {e}")
                
                # 3. 检查约束（SQLite约束信息较难获取，主要通过表结构检查）
                try:
                    # 获取外键约束信息
                    foreign_keys = self.conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
                    
                    self.logger.info(f"表 {table} 外键约束信息 ({len(foreign_keys)} 个外键):")
                    for fk in foreign_keys:
                        self.logger.info(f"  - 外键: {fk}")
                        
                except Exception as e:
                    self.logger.warning(f"无法获取表 {table} 的约束信息: {e}")
                
                self.logger.info(f"=== 表 {table} 检查完成 ===\n")
                
        except Exception as e:
            self.logger.error(f"检查表约束失败: {str(e)}")
            raise e
    
    def repair_table_constraints(self):
        """
        修复表约束问题
        """
        self.ensure_connected()
        
        try:
            self.logger.info("开始修复数据库表约束...")
            
            # 检查并修复 meals 表主键约束
            self.logger.info("检查 meals 表主键约束...")
            
            # 检查当前主键约束状态（通过表结构信息）
            table_info = self.conn.execute("PRAGMA table_info(meals)").fetchall()
            has_primary_key = any(col[5] for col in table_info)  # col[5] 是 pk 字段
            
            if not has_primary_key:
                self.logger.warning("meals 表缺少主键约束，尝试修复...")
                
                # 检查是否有重复的 meal_id
                duplicates = self.conn.execute("""
                    SELECT meal_id, COUNT(*) 
                    FROM meals 
                    GROUP BY meal_id 
                    HAVING COUNT(*) > 1
                """).fetchall()
                
                if duplicates:
                    self.logger.error(f"发现重复的 meal_id: {duplicates}")
                    # 这里可以添加重复数据清理逻辑
                    raise RuntimeError("存在重复数据，无法创建主键约束")
                
                # SQLite 不支持在已有表上添加主键约束，需要重建表
                self.logger.info("尝试重建 meals 表以确保主键约束...")
                self._rebuild_meals_table_with_constraints()
                
            else:
                self.logger.info("meals 表主键约束正常")
            
            # 检查其他核心表
            for table in ['users', 'addons', 'orders', 'ledger']:
                self._check_and_repair_table_pk(table)
            
            self.logger.info("表约束修复完成")
            
        except Exception as e:
            self.logger.error(f"修复表约束失败: {str(e)}")
            raise e
    
    def _rebuild_meals_table_with_constraints(self):
        """
        重建 meals 表以确保约束正确
        """
        self.logger.info("开始重建 meals 表...")
        
        try:
            # 1. 备份现有数据
            existing_data = self.conn.execute("SELECT * FROM meals").fetchall()
            self.logger.info(f"备份了 {len(existing_data)} 条 meals 记录")
            
            # 2. 创建临时表
            self.conn.execute("""
                CREATE TABLE meals_backup AS SELECT * FROM meals
            """)
            
            # 3. 删除原表
            self.conn.execute("DROP TABLE meals")
            
            # 4. 重新创建表（确保主键约束）
            self.conn.execute("""
                CREATE TABLE meals (
                    meal_id INTEGER PRIMARY KEY,
                    date DATE NOT NULL,
                    slot VARCHAR(20) NOT NULL,
                    description TEXT,
                    base_price_cents INTEGER NOT NULL,
                    addon_config JSON,
                    max_orders INTEGER DEFAULT 50,
                    current_orders INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'published',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    locked_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    canceled_at TIMESTAMP,
                    canceled_by INTEGER,
                    canceled_reason TEXT,
                    UNIQUE(date, slot)
                )
            """)
            
            # 5. 恢复数据
            for row in existing_data:
                self.conn.execute("""
                    INSERT INTO meals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            
            # 6. 删除备份表
            self.conn.execute("DROP TABLE meals_backup")
            
            self.logger.info("meals 表重建完成")
            
        except Exception as e:
            self.logger.error(f"重建 meals 表失败: {e}")
            # 尝试恢复
            try:
                self.conn.execute("DROP TABLE IF EXISTS meals")
                self.conn.execute("ALTER TABLE meals_backup RENAME TO meals")
                self.logger.info("已恢复原始 meals 表")
            except:
                pass
            raise e
    
    def _check_and_repair_table_pk(self, table_name: str):
        """
        检查并修复指定表的主键约束
        """
        try:
            # 通过PRAGMA table_info检查主键约束
            table_info = self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            has_primary_key = any(col[5] for col in table_info)  # col[5] 是 pk 字段
            
            if has_primary_key:
                self.logger.info(f"表 {table_name} 主键约束正常")
            else:
                self.logger.warning(f"表 {table_name} 缺少主键约束")
                
        except Exception as e:
            self.logger.warning(f"检查表 {table_name} 约束失败: {e}")

    def backup(self, backup_path: str):
        """
        备份数据库（SQLite文件复制方式）
        
        Args:
            backup_path: 备份文件路径
        """
        self.ensure_connected()
        
        try:
            import shutil
            self.logger.info(f"开始备份数据库到: {backup_path}")
            
            # 确保备份目录存在
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            
            # SQLite通过文件复制进行备份
            shutil.copy2(self.db_path, backup_path)
            self.logger.info("数据库备份完成")
        except Exception as e:
            self.logger.error(f"数据库备份失败: {str(e)}")
            raise e
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        if not self.is_connected():
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.close()
    
    def __del__(self):
        """
        析构函数，确保连接被正确关闭
        """
        if self.is_connected():
            self.close()