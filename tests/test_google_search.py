import os
import unittest
import requests
from dotenv import load_dotenv
import json
from pprint import pprint

load_dotenv()

class TestGoogleSearch(unittest.TestCase):
    def setUp(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        self.base_url = 'https://www.googleapis.com/customsearch/v1'

    def test_basic_search(self):
        query = 'Deepseek'
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': 10,  # 每页结果数（最大10）
            'start': 1,  # 起始位置
            # 'dateRestrict': 'd[number]' # 限制日期范围，例如 'd1' 表示最近1天
            # 'gl': 'cn',  # 地理位置
            # 'lr': 'lang_zh-CN',  # 语言限制
        }

        response = requests.get(self.base_url, params=params)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 保存完整响应到文件
        with open('search_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 打印搜索结果的主要字段说明
        print("\n=== 搜索响应数据结构说明 ===")
        print("1. searchInformation:")
        print("   - totalResults: 总结果数")
        print("   - searchTime: 搜索耗时")
        
        print("\n2. items 数组中每个结果包含:")
        print("   - title: 标题")
        print("   - link: 链接URL")
        print("   - snippet: 文本摘要")
        print("   - pagemap: 页面元数据（如有）")
        print("   - displayLink: 显示的链接")
        print("   - htmlTitle: HTML格式的标题")
        print("   - htmlSnippet: HTML格式的摘要")

        # 打印实际数据示例
        print("\n=== 实际搜索数据 ===")
        pprint(data)

if __name__ == '__main__':
    unittest.main()
