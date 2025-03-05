import os
import json
import requests
from typing import Dict
from dotenv import load_dotenv
from .base_engine import BaseSearchEngine

class GoogleAPISearchEngine(BaseSearchEngine):
    def __init__(self):
        super().__init__()
        load_dotenv()
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not self.api_key or not self.search_engine_id:
            raise ValueError("未找到 Google API 配置，请检查环境变量 GOOGLE_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID")
            
    def search(self, query: str, min_results: int = 10, max_pages: int = 3) -> Dict:
        """
        使用 Google Custom Search API 执行搜索
        """
        results = []
        start_index = 1
        
        try:
            while len(results) < min_results and start_index <= (max_pages * 10):
                # 构建 API 请求URL
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.api_key,
                    'cx': self.search_engine_id,
                    'q': query,
                    'start': start_index,
                    # 'gl': 'cn',  # 设置地理位置为中国
                    # 'hl': 'zh-CN'  # 设置语言为中文
                }
                
                self.logger.info(f"正在请求第 {(start_index-1)//10 + 1} 页搜索结果...")
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'items' in data:
                        for item in data['items']:
                            results.append({
                                'title': item.get('title', ''),
                                'link': item.get('link', ''),
                                'snippet': item.get('snippet', '')
                            })
                            
                        if len(data['items']) < 10:  # 如果返回结果少于10条，说明没有更多结果了
                            break
                    else:
                        self.logger.warning("API响应中没有搜索结果")
                        break
                else:
                    self.logger.error(f"API请求失败: {response.status_code}")
                    break
                
                start_index += 10
                
        except Exception as e:
            self.logger.error(f"Google API搜索出错: {str(e)}")
            
        self.logger.info(f"搜索完成，共找到 {len(results)} 个结果")
        return {'items': results[:min_results]}
