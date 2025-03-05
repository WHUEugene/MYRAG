import logging
import numpy as np
import requests
import json
from typing import List, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
from .models import SearchResult
import os
TARGET_PORT = os.getenv("TARGET_URL", "11434")
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class RelevanceRanker:
    """用于对搜索结果进行相关度排序的类"""
    
    def __init__(self, model_name="nomic-embed-text"):
        """
        初始化排序器
        
        Args:
            model_name: 使用的Ollama嵌入模型名称，默认为nomic-embed-text
        """
        self.model_name = model_name
        self.ollama_url = f"http://localhost:{TARGET_PORT}/api/embeddings"
        
        # 验证模型是否可用
        try:
            self._test_model_availability()
            logger.info(f"已连接到Ollama服务并使用嵌入模型: {model_name}")
        except Exception as e:
            logger.error(f"Ollama嵌入模型连接失败: {str(e)}")
            logger.warning("如果Ollama服务未启动，请运行: ollama serve")
            logger.warning(f"如果模型未下载，请运行: ollama pull {model_name}")
            raise
        
        # 缓存嵌入向量，避免重复计算
        self.embedding_cache = {}
        
    def _test_model_availability(self):
        """测试Ollama服务和模型是否可用"""
        test_req = {"model": self.model_name, "prompt": "test"}
        response = requests.post(self.ollama_url, json=test_req, timeout=5)
        if response.status_code != 200:
            raise ConnectionError(f"Ollama服务响应错误: {response.status_code}, {response.text}")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        使用Ollama服务获取文本的嵌入向量
        
        Args:
            text: 需要计算嵌入向量的文本
            
        Returns:
            numpy数组形式的嵌入向量
        """
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        try:
            # 准备请求
            request_data = {
                "model": self.model_name,
                "prompt": text
            }
            
            # 发送请求
            response = requests.post(self.ollama_url, json=request_data)
            response.raise_for_status()  # 检查响应状态
            
            # 解析结果
            result = response.json()
            if "embedding" not in result:
                raise ValueError(f"Ollama返回的结果中没有embedding字段: {result}")
                
            # 转换为numpy数组
            embedding = np.array(result["embedding"])
            
            # 缓存结果
            self.embedding_cache[text] = embedding
            return embedding
            
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {str(e)}")
            # 返回一个空向量作为备选
            return np.zeros(1024)  # nomic-embed-text 通常是 1024 维
        
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算两个嵌入向量的相似度"""
        try:
            return cosine_similarity(
                embedding1.reshape(1, -1),
                embedding2.reshape(1, -1)
            )[0][0]
        except Exception as e:
            logger.error(f"计算相似度时出错: {str(e)}")
            return 0.0
        
    def rank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """根据与查询的相关性对结果进行排序"""
        if not results:
            return []
            
        try:
            # 获取查询的嵌入
            query_embedding = self.get_embedding(query)
            logger.info(f"已获取查询文本的嵌入向量，维度: {query_embedding.shape}")
            
            # 计算每个结果的相关性分数
            for result in results:
                # 结合标题和摘要
                text = f"{result.title}. {result.snippet}"
                result_embedding = self.get_embedding(text)
                
                # 计算余弦相似度
                similarity = self.compute_similarity(query_embedding, result_embedding)
                result.relevance_score = float(similarity)
                logger.debug(f"结果 '{result.title[:30]}...' 的相关性得分: {similarity:.4f}")
                
            # 按相关性排序
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"排序结果时出错: {str(e)}")
            return results  # 出错时返回原始顺序
