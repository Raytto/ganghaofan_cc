# 参考文档: doc/db/db_manager.md
# 数据库连接和事务管理的核心组件

import duckdb
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from contextlib import contextmanager

class DatabaseManager:
    """
    数据库管理器
    
    负责DuckDB数据库连接管理、事务处理和基础操作
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
    
    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        建立数据库连接
        
        Returns:
            DuckDB连接对象
        
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
            
            self.conn = duckdb.connect(self.db_path)
            self._is_connected = True
            self.logger.info(f"成功连接到数据库: {self.db_path}")
            
            # 设置DuckDB优化参数
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
        配置DuckDB优化参数
        """
        try:
            # 设置内存限制和并发参数
            optimizations = [
                "PRAGMA memory_limit='1GB'",
                "PRAGMA threads=4"
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
            self.conn.begin()
            
            for i, operation in enumerate(operations):
                self.logger.debug(f"执行事务 {transaction_id} 中的操作 {i+1}/{len(operations)}")
                result = operation()
                results.append(result)
            
            self.conn.commit()
            self.logger.info(f"事务 {transaction_id} 提交成功")
            
            return results
            
        except Exception as e:
            self.logger.error(f"事务 {transaction_id} 执行失败: {str(e)}")
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
                return self.conn.execute(query, params)
            else:
                return self.conn.execute(query)
                
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
            self.conn.begin()
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
    
    def backup(self, backup_path: str):
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径
        """
        self.ensure_connected()
        
        try:
            self.logger.info(f"开始备份数据库到: {backup_path}")
            self.conn.execute(f"EXPORT DATABASE '{backup_path}'")
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