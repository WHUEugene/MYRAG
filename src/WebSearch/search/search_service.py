import time
import logging
from typing import List, Union
from .models import SearchResult,SearchResponse
from .content_processor import ContentProcessor

from .models import SearchResult, SearchResponse
from .content_processor import ContentProcessor
from browser_search import BrowserSearch
# 创建日志记录器
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class SearchService:
    def __init__(self, engines: Union[str, List[str]] = None):
        """
        初始化搜索服务
        Args:
            engines: 可以是字符串('google'或'bing')或字符串列表['google', 'bing']
                    默认为 ['bing']
        """
        if engines is None:
            engines = ['google_api']
        elif isinstance(engines, str):
            engines = [engines]
            
        self.browser_search = BrowserSearch(engines)
        self.content_processor = ContentProcessor()
        self.active_engines = engines
    
    def search(self, query: str, min_results: int = 10, max_pages: int = 3) -> SearchResponse:
        logger.info(f"使用搜索引擎: {', '.join(self.active_engines)}")
        start_time = time.time()
        
        # 获取原始搜索结果
        raw_results = self.browser_search.search(query, min_results=min_results, max_pages=max_pages)
        
        # 转换为SearchResult对象
        results = [
            SearchResult(
                title=item['title'],
                link=item['link'],
                snippet=item['snippet']
            )
            for item in raw_results['items']
        ]
        logger.info(f"初级搜索结果: {len(results)} 条")
        
        # 处理结果
        processed_results = self.content_processor.process_results(
            query, 
            results,
            max_results=min(5, len(results))  # 限制最终结果数量
        )
        logger.info(f"网页段落查询后的结果: {len(processed_results)} 条")
        
        search_time = time.time() - start_time
        
        return SearchResponse(
            query=query,
            results=processed_results,
            total_results=len(processed_results),
            search_time=search_time
        )
