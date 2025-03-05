import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search.search_service import SearchService

def test_different_engines():
    # 只使用Google搜索
    google_service = SearchService(engines='google')
    google_response = google_service.search("Python教程", min_results=5)
    print("\nGoogle搜索结果:")
    print(google_response.to_json())
    
    # 只使用Bing搜索
    bing_service = SearchService(engines='bing')
    bing_response = bing_service.search("Python教程", min_results=5)
    print("\nBing搜索结果:")
    print(bing_response.to_json())
    
    # 同时使用Google和Bing
    combined_service = SearchService(engines=['google', 'bing'])
    combined_response = combined_service.search("Python教程", min_results=10)
    print("\n组合搜索结果:")
    print(combined_response.to_json())

if __name__ == "__main__":
    test_different_engines()
