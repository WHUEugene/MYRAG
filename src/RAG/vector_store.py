import json
import os

class VectorStore:
    def __init__(self):
        self.base_path = "vector_store"
        os.makedirs(self.base_path, exist_ok=True)

    def store_vectors(self, kb_id, dataset_id, texts, vectors):
        """
        存储文本及其对应的向量
        
        Args:
            kb_id (str): 知识库ID
            dataset_id (str): 数据集ID
            texts (list): 文本列表
            vectors (list): 向量列表
        """
        kb_path = os.path.join(self.base_path, kb_id)
        os.makedirs(kb_path, exist_ok=True)
        
        # 保存向量和文本映射
        data = {
            'texts': texts,
            'vectors': [v.tolist() for v in vectors]
        }
        
        with open(os.path.join(kb_path, f"{dataset_id}.json"), 'w') as f:
            json.dump(data, f)

# 创建全局实例
vector_store = VectorStore()

def store_vectors(kb_id, dataset_id, texts, vectors):
    """全局函数，用于存储向量"""
    return vector_store.store_vectors(kb_id, dataset_id, texts, vectors)
