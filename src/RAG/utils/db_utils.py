import sqlite3
import json
import numpy as np
import os
from datetime import datetime

class DBManager:
    def __init__(self, db_path):
        """初始化数据库管理器
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        # 确保目录存在并有正确的权限
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, mode=0o755, exist_ok=True)
            print(f"[DEBUG] 创建数据库目录: {db_dir}")
        
        # 如果数据库文件不存在，设置正确的权限
        if not os.path.exists(db_path):
            # 创建空文件并设置权限
            with open(db_path, 'w') as f:
                pass
            os.chmod(db_path, 0o644)
            print(f"[DEBUG] 创建数据库文件: {db_path}")
        
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # 创建表（如果不存在）
            c.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id TEXT NOT NULL,
                kb_id TEXT NOT NULL,
                text TEXT NOT NULL,
                vector BLOB NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建索引（如果不存在）
            c.execute('CREATE INDEX IF NOT EXISTS idx_dataset ON chunks(dataset_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_kb ON chunks(kb_id)')
            
            conn.commit()
            print("[DEBUG] 数据库表初始化完成")
            
        except Exception as e:
            print(f"[ERROR] 数据库初始化失败: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    def add_chunks(self, kb_id, dataset_id, texts, vectors):
        """添加文档分块"""
        print(f"[DEBUG] 添加分块: kb_id={kb_id}, dataset_id={dataset_id}, chunks数量={len(texts)}")
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # 使用事务来提高插入性能
            c.execute('BEGIN TRANSACTION')
            
            for text, vector in zip(texts, vectors):
                # 确保向量是列表格式
                if isinstance(vector, np.ndarray):
                    vector = vector.tolist()
                vector_blob = json.dumps(vector)
                
                # 添加更多的日志
                print(f"[DEBUG] 插入chunk: text长度={len(text)}, vector维度={len(vector)}")
                
                c.execute(
                    'INSERT INTO chunks (kb_id, dataset_id, text, vector, enabled) VALUES (?, ?, ?, ?, 1)',
                    (kb_id, dataset_id, text, vector_blob)
                )
            
            conn.commit()
            print(f"[DEBUG] 成功添加 {len(texts)} 个分块")
            
            # 验证插入
            c.execute('SELECT COUNT(*) FROM chunks WHERE dataset_id = ?', (dataset_id,))
            count = c.fetchone()[0]
            print(f"[DEBUG] 验证: 数据库中找到 {count} 条记录")
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[ERROR] 添加分块失败: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    def get_chunks(self, kb_id=None, dataset_id=None):
        """获取文档分块"""
        print(f"[DEBUG] 获取分块: kb_id={kb_id}, dataset_id={dataset_id}")
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            if dataset_id and kb_id:
                c.execute('SELECT id, dataset_id, kb_id, vector, text FROM chunks WHERE kb_id = ? AND dataset_id = ?', (kb_id, dataset_id))
            elif dataset_id:
                c.execute('SELECT id, dataset_id, kb_id, vector, text FROM chunks WHERE dataset_id = ?', (dataset_id,))
            elif kb_id:
                c.execute('SELECT id, dataset_id, kb_id, vector, text FROM chunks WHERE kb_id = ?', (kb_id,))
            else:
                c.execute('SELECT id, dataset_id, kb_id, vector, text FROM chunks')
            
            chunks = c.fetchall()
            print(f"[DEBUG] 获取到 {len(chunks)} 个分块")
            
            # 转换向量数据
            processed_chunks = []
            for chunk in chunks:
                id_, ds_id, kb_id, vector_blob, text = chunk
                vector = np.array(json.loads(vector_blob))
                processed_chunks.append((id_, ds_id, kb_id, vector, text))
            
            return processed_chunks
        except Exception as e:
            print(f"[ERROR] 获取分块失败: {str(e)}")
            raise
        finally:
            conn.close()

    def delete_chunks(self, dataset_id):
        """删除指定数据集的分块"""
        print(f"[DEBUG] 删除分块: dataset_id={dataset_id}")
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('DELETE FROM chunks WHERE dataset_id = ?', (dataset_id,))
            conn.commit()
            print(f"[DEBUG] 已删除 dataset_id={dataset_id} 的所有分块")
        except Exception as e:
            print(f"[ERROR] 删除分块失败: {str(e)}")
            raise
        finally:
            conn.close()

    def toggle_chunks(self, dataset_id, enabled):
        """切换分块的启用状态"""
        print(f"[DEBUG] 切换分块状态: dataset_id={dataset_id}, enabled={enabled}")
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('UPDATE chunks SET enabled = ? WHERE dataset_id = ?', (1 if enabled else 0, dataset_id))
            conn.commit()
            print(f"[DEBUG] 已更新分块状态")
        except Exception as e:
            print(f"[ERROR] 更新分块状态失败: {str(e)}")
            raise
        finally:
            conn.close()
