import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Optional
from .models import SearchResult, ContentParagraph
from .ranking import RelevanceRanker
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class ContentProcessor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Charset': 'UTF-8'
        }
        # 初始化使用Ollama的nomic-embed-text模型
        self.ranker = RelevanceRanker(model_name="nomic-embed-text")
        self.cache = {}  # 简单的内存缓存
        self.min_paragraph_length = 500
        self.max_paragraphs_per_page = 5  # 每个页面保留的最相关段落数
        self.max_workers = 15  # 并发线程数
    
    def fetch_content(self, url: str) -> Optional[str]:
        # 检查缓存
        if url in self.cache:
            return self.cache[url]
            
        try:
            logger.info(f"正在获取网页内容: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            # 检测并设置正确的编码
            if response.encoding.lower() != 'utf-8':
                # 尝试从内容或HTTP头中获取编码
                if 'charset=' in response.headers.get('Content-Type', '').lower():
                    charset = response.headers.get('Content-Type').split('charset=')[1]
                    response.encoding = charset
                else:
                    # 默认使用UTF-8
                    response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除script、style等标签
            for tag in soup(['script', 'style', 'meta', 'link']):
                tag.decompose()
                
            # 提取正文
            content = ' '.join(p.text.strip() for p in soup.find_all('p') if p.text.strip())
            
            # 确保内容是正确编码的UTF-8
            content = content.encode('utf-8').decode('utf-8', errors='ignore')
            
            # 缓存结果
            self.cache[url] = content
            time.sleep(1)  # 简单的请求延迟
            logger.info(f"成功获取网页内容，长度: {len(content)} 字符")
            return content
            
        except Exception as e:
            logger.error(f"获取网页内容失败 {url}: {str(e)}")
            return None
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """智能文本分段，控制段落长度在500-1000字符左右"""
        # 首先按换行符分割
        raw_paragraphs = text.split('\n')
        paragraphs = []
        current = []
        current_length = 0
        target_min_length = 500
        target_max_length = 1000
        
        for p in raw_paragraphs:
            p = p.strip()
            if not p:
                continue
                
            # 如果当前段落加上新内容会超过最大长度，先保存当前段落
            if current_length + len(p) > target_max_length and current_length >= target_min_length:
                if current:
                    paragraphs.append(' '.join(current))
                    current = []
                    current_length = 0
            
            current.append(p)
            current_length += len(p)
            
            # 如果已经达到目标最小长度，并且在一个自然段落结束（句号等），可以考虑切分
            if current_length >= target_min_length and p.endswith(('.', '。', '!', '！', '?', '？')):
                paragraphs.append(' '.join(current))
                current = []
                current_length = 0
        
        # 处理剩余内容
        if current:
            paragraphs.append(' '.join(current))
        
        # 确保所有段落至少达到最小长度要求
        result = []
        temp = []
        temp_length = 0
        
        for p in paragraphs:
            if temp_length + len(p) <= target_max_length or not temp:
                temp.append(p)
                temp_length += len(p)
            else:
                result.append(' '.join(temp))
                temp = [p]
                temp_length = len(p)
        
        if temp:
            result.append(' '.join(temp))
        
        # 过滤太短的段落
        result = [p for p in result if len(p) >= self.min_paragraph_length]
            
        return result
    
    def _process_single_result(self, result: SearchResult, query_emb) -> SearchResult:
        """处理单个搜索结果"""
        content = self.fetch_content(result.link)
        if content:
            # 智能分段
            paragraphs = self.split_into_paragraphs(content)
            logger.info(f"从 '{result.title[:30]}...' 中提取了 {len(paragraphs)} 个段落")
            
            scored_paragraphs = []
            
            # 计算每个段落的相似度
            for para in paragraphs:
                if len(para.strip()) >= self.min_paragraph_length:
                    para_emb = self.ranker.get_embedding(para)
                    score = self.ranker.compute_similarity(query_emb, para_emb)
                    scored_paragraphs.append(ContentParagraph(para, score))
            
            # 按相似度排序，保留最相关的几个段落
            scored_paragraphs.sort(key=lambda x: x.score, reverse=True)
            result.paragraphs = scored_paragraphs[:self.max_paragraphs_per_page]
            
            # 使用最相关的段落作为主要内容
            if result.paragraphs:
                result.content = result.paragraphs[0].text
                logger.debug(f"最相关段落得分: {result.paragraphs[0].score:.4f}")
        
        return result

    def process_results(self, query: str, results: List[SearchResult], 
                       max_results: int = 20) -> List[SearchResult]:
        logger.info(f"处理 {len(results)} 条搜索结果")
        
        # 先进行第一层过滤
        filtered_results = self.ranker.rank_results(query, results)
        query_emb = self.ranker.get_embedding(query)
        
        # 使用线程池并发处理结果
        processed_results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_result = {
                executor.submit(self._process_single_result, result, query_emb): result 
                for result in filtered_results
            }
            
            # 收集处理完成的结果
            for future in as_completed(future_to_result):
                try:
                    processed_result = future.result()
                    if processed_result:
                        processed_results.append(processed_result)
                except Exception as e:
                    logger.error(f"处理结果时出错: {str(e)}")
        
        # 根据整体相关度和段落得分重新排序
        processed_results.sort(key=lambda x: (
            x.relevance_score,
            max(p.score for p in (x.paragraphs or [ContentParagraph('', 0)]))
        ), reverse=True)
        
        logger.info(f"处理完成，返回 {min(max_results, len(processed_results))} 条结果")
        return processed_results[:max_results]
