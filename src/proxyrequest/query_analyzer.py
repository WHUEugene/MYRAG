import re
import logging
from typing import Dict, List, Any, Tuple

# 配置日志
logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """
    查询分析器，用于分析用户查询并提供功能推荐
    """
    
    def __init__(self, min_confidence=0.6):
        """
        初始化查询分析器
        
        参数:
            min_confidence: 最小置信度阈值，低于此值的功能不会被推荐
        """
        self.min_confidence = min_confidence
        
        # 关键词和模式词典
        self.patterns = {
            "rag_enabled": {
                "keywords": [
                    "知识库", "文档", "资料", "数据库", "文章", "论文", "书籍", 
                    "报告", "内部资料", "参考", "资料库", "信息库"
                ],
                "patterns": [
                    r"(?:查找|查询|搜索|检索|寻找).*(?:知识库|文档|资料)",
                    r".*(?:知识库|文档|资料).*(?:相关内容|相关信息)",
                    r"(?:根据|基于).*(?:知识库|文档|资料)",
                    r".*内部(?:资料|文档|知识).*",
                ],
                "negative_patterns": [
                    r"不要.*(?:知识库|文档)"
                ]
            },
            "web_search_enabled": {
                "keywords": [
                    "搜索", "查一下", "查询", "网上", "互联网", "最新", "新闻", 
                    "最近", "最新消息", "网络", "在线", "实时", "谷歌", "百度"
                ],
                "patterns": [
                    r"(?:搜索|查询|查找|检索).*(?:网络|互联网|在线)",
                    r".*(?:最新|最近|近期|当前).*(?:情况|消息|新闻|进展)",
                    r".*(?:互联网|网络|在线|外部).*(?:查询|搜索)",
                    r".*现在.*(?:是什么|怎样|如何)",
                ],
                "negative_patterns": [
                    r"不要.*(?:搜索|上网)"
                ]
            }
        }
        
        # 权重配置
        self.weights = {
            "keyword": 0.5,  # 关键词匹配的基础权重
            "pattern": 0.7,  # 模式匹配的权重
            "negative": -1.0  # 否定模式的权重
        }
    
    def analyze(self, query: str) -> Dict[str, bool]:
        """
        分析查询并返回应该启用的功能
        
        参数:
            query: 用户查询文本
            
        返回:
            Dict[str, bool]: 功能启用推荐，如{"rag_enabled": True, "web_search_enabled": False}
        """
        if not query or not isinstance(query, str):
            logger.warning("无效的查询文本")
            return {}
        
        logger.info(f"开始分析查询: {query[:100]}..." if len(query) > 100 else query)
        
        # 清理查询文本
        query = query.lower().strip()
        
        # 存储每个功能的置信度分数
        confidence_scores = {}
        
        # 分析每个功能
        for feature, patterns in self.patterns.items():
            score, matches = self._calculate_feature_score(query, patterns)
            confidence = self._normalize_score(score)
            
            confidence_scores[feature] = {
                "confidence": confidence,
                "matches": matches,
                "enabled": confidence >= self.min_confidence
            }
            
            logger.info(f"功能 {feature} 的置信度: {confidence:.2f} - 启用: {confidence >= self.min_confidence}")
        
        # 返回最终决策
        decisions = {
            feature: data["enabled"] 
            for feature, data in confidence_scores.items()
        }
        
        return decisions
    
    def _calculate_feature_score(self, query: str, patterns: Dict[str, List[str]]) -> Tuple[float, List[str]]:
        """
        计算特定功能的置信度分数
        
        参数:
            query: 用户查询
            patterns: 功能的模式词典
            
        返回:
            Tuple[float, List[str]]: 分数和匹配项列表
        """
        score = 0.0
        matches = []
        
        # 关键词匹配
        for keyword in patterns.get("keywords", []):
            if keyword in query:
                score += self.weights["keyword"]
                matches.append(f"关键词: {keyword}")
        
        # 模式匹配
        for pattern in patterns.get("patterns", []):
            if re.search(pattern, query):
                score += self.weights["pattern"]
                matches.append(f"模式: {pattern}")
        
        # 否定模式匹配
        for neg_pattern in patterns.get("negative_patterns", []):
            if re.search(neg_pattern, query):
                score += self.weights["negative"]  # 减去分数
                matches.append(f"否定模式: {neg_pattern}")
        
        return score, matches
    
    def _normalize_score(self, score: float) -> float:
        """
        归一化分数到0-1范围
        
        参数:
            score: 原始分数
            
        返回:
            float: 归一化后的分数
        """
        # 简单的Sigmoid函数归一化
        import math
        normalized = 1 / (1 + math.exp(-score))
        return normalized

    def extract_options_from_message(self, body_json: Dict[str, Any]) -> Dict[str, bool]:
        """
        从消息中提取查询并分析需要启用的选项
        
        参数:
            body_json: 请求体
            
        返回:
            Dict[str, bool]: 推荐的选项
        """
        query = self._extract_latest_query(body_json)
        
        if not query:
            logger.info("未能从消息中提取有效查询")
            return {}
             
        return self.analyze(query)
    
    def _extract_latest_query(self, body_json: Dict[str, Any]) -> str:
        """
        从请求体中提取最新的用户查询
        
        参数:
            body_json: 请求体
            
        返回:
            str: 用户查询，如果无法提取则返回空字符串
        """
        # 从messages中提取
        if "messages" in body_json:
            for msg in reversed(body_json["messages"]):
                # 代码使用了 reversed() 函数来逆序遍历消息数组：
                if msg.get("role") == "user" and "content" in msg:
                    # # 找到第一个用户消息即返回
                    content = msg["content"]
                    if isinstance(content, str):
                        return content
                    elif isinstance(content, list):
                        # 处理多模态消息
                        text_parts = []
                        for part in content:
                            if part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                        return " ".join(text_parts)
        
        # 从prompt中提取
        if "prompt" in body_json:
            if isinstance(body_json["prompt"], str):
                return body_json["prompt"]
            elif isinstance(body_json["prompt"], list):
                # 处理多模态prompt
                text_parts = []
                for item in body_json["prompt"]:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                return " ".join(text_parts)
        
        return ""
