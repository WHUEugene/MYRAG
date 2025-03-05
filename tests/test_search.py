import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_search import BrowserSearch
from search.search_service import SearchService
from search_engines.google_engine import GoogleSearchEngine
from search_engines.bing_engine import BingSearchEngine

def setup_chrome_driver():
    """设置Chrome驱动路径"""
    # 根据实际ChromeDriver存放路径修改
    chrome_driver_path = "/usr/local/bin/chromedriver"  # 示例路径
    if os.path.exists(chrome_driver_path):
        os.environ["webdriver.chrome.driver"] = chrome_driver_path

def test_single_engine(engine='google'):
    """测试单一搜索引擎"""
    print(f"\n测试 {engine} 搜索引擎...")
    browser = BrowserSearch([engine])
    try:
        results = browser.search("人工智能", min_results=5, max_pages=2)
        print(f"结果数量: {len(results['items'])}")
        for item in results['items'][:3]:  # 只显示前3个结果
            print(f"\n标题: {item['title'][:50]}...")
            print(f"链接: {item['link']}")
    except Exception as e:
        print(f"搜索出错: {str(e)}")

def test_search_service():
    """测试搜索服务"""
    print("\n测试搜索服务...")
    service = SearchService()
    try:
        response = service.search(
            query="深度学习框架比较",
            min_results=10,    # 初始搜索结果数量
            max_pages=2        # 最多搜索页数
        )
        
        print(f"查询: {response.query}")
        print(f"找到结果数: {response.total_results}")
        print(f"搜索用时: {response.search_time:.2f}秒")
        
        if response.results:
            print("\n第一个结果:")
            result = response.results[0]
            print(f"标题: {result.title[:50]}...")
            print(f"相关度: {result.relevance_score:.4f}")
            if result.paragraphs:
                print(f"最相关段落: {result.paragraphs[0].text[:100]}...")
    except Exception as e:
        print(f"搜索服务出错: {str(e)}")

def test_google():
    print("\n测试 Google 搜索...")
    engine = GoogleSearchEngine()
    results = engine.search("python programming", min_results=5, max_pages=1)
    print(f"Google 搜索结果数量: {len(results['items'])}")
    for item in results['items']:
        print(f"\n标题: {item['title'][:50]}...")
        print(f"链接: {item['link']}")

def test_bing():
    print("\n测试 Bing 搜索...")
    engine = BingSearchEngine()
    results = engine.search("python programming", min_results=5, max_pages=1)
    print(f"Bing 搜索结果数量: {len(results['items'])}")
    for item in results['items']:
        print(f"\n标题: {item['title'][:50]}...")
        print(f"链接: {item['link']}")

def main():
    print("开始搜索测试...\n")
    setup_chrome_driver()
    
    try:
        # 测试Bing搜索
        test_single_engine('bing')
        
        # 测试搜索服务
        test_search_service()
        
        # 测试Google搜索
        test_google()
        
        # 测试Bing搜索
        test_bing()
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {str(e)}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()
