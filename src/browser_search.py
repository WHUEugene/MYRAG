import logging
from typing import Dict, List, Union
from WebSearch.search_engines.google_engine import GoogleSearchEngine
from WebSearch.search_engines.bing_engine import BingSearchEngine
import json

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class BrowserSearch:
    def __init__(self, engines: Union[str, List[str]] = None):
        """
        初始化浏览器搜索服务
        
        Args:
            engines: 要使用的搜索引擎，可以是字符串或字符串列表
        """
        if engines is None:
            engines = ['bing']
        elif isinstance(engines, str):
            engines = [engines]
            
        self.engines = []
        for engine_name in engines:
            if engine_name.lower() == 'google':
                self.engines.append(('google', GoogleSearchEngine()))
            elif engine_name.lower() == 'bing':
                self.engines.append(('bing', BingSearchEngine()))
            else:
                logger.warning(f"不支持的搜索引擎: {engine_name}")
                
        if not self.engines:
            logger.warning("没有指定有效的搜索引擎，将使用Bing作为默认引擎")
            self.engines.append(('bing', BingSearchEngine()))
    
    def search(self, query: str, min_results: int = 10, max_pages: int = 3) -> Dict:
        """
        执行多引擎搜索
        
        Args:
            query: 搜索查询
            min_results: 每个引擎需要的最小结果数
            max_pages: 每个引擎最多搜索的页数
            
        Returns:
            包含搜索结果的字典
        """
        all_results = []
        
        try:
            for engine_name, engine in self.engines:
                logger.info(f"使用 {engine_name} 搜索: {query}")
                try:
                    # 计算每个引擎需要的结果数
                    engine_min_results = min_results // len(self.engines) + (1 if min_results % len(self.engines) > 0 else 0)
                    
                    # 执行搜索
                    results = engine.search(query, engine_min_results, max_pages)
                    
                    if 'items' in results:
                        logger.info(f"{engine_name} 返回了 {len(results['items'])} 条结果")
                        all_results.extend(results['items'])
                    else:
                        logger.warning(f"{engine_name} 没有返回有效结果")
                        
                except Exception as e:
                    logger.error(f"{engine_name} 搜索出错: {str(e)}")
        except Exception as e:
            logger.error(f"多引擎搜索过程中发生错误: {str(e)}")
            
        return {'items': all_results}

def analyze_page_structure():
    """分析保存的页面源码,帮助确定正确的选择器"""
    with open('google_search_page.html', 'r', encoding='utf-8') as f:
        html = f.read()
    print("\n页面结构分析:")
    print("1. 搜索结果容器数量:", html.count('class="g"'))
    print("2. 标题元素数量:", html.count('<h3'))
    print("3. 摘要元素数量:", html.count('class="VwiC3b'))
    return html

def main():
    searcher = BrowserSearch()
    results = searcher.search("Deepseek")
    
    # 分析页面结构
    print("\n开始分析页面结构...")
    analyze_page_structure()
    
    # 保存结果到文件
    with open('browser_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n搜索完成！结果已保存到 browser_results.json")
    print(f"找到 {len(results['items'])} 个结果")

if __name__ == "__main__":
    main()
