import sys
import os
import asyncio
import json
import uuid
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from proxyrequest.request_handlers import handle_chat_request
from aiohttp import web
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MockRequest:
    """模拟Web请求"""
    def __init__(self, body):
        self.body_bytes = json.dumps(body).encode('utf-8')
    
    async def read(self):
        return self.body_bytes

class MockResponse:
    """模拟响应对象，捕获输出"""
    def __init__(self):
        self.status = 200
        self.headers = {}
        self.body = []
        self.prepared = False
    
    async def prepare(self, request):
        self.prepared = True
        return None
    
    async def write(self, data):
        self.body.append(data)
        try:
            decoded = data.decode('utf-8')
            if len(decoded.strip()) > 0:
                print(f"响应片段: {decoded.strip()}")
        except:
            pass
    
    async def drain(self):
        pass

async def test_queries():
    """测试不同类型的查询以验证功能检测和响应"""
    
    test_cases = [
        {
            "name": "普通问题",
            "body": {
                "model": "llama3",
                "messages": [{"role": "user", "content": "介绍一下自己"}]
            }
        },
        {
            "name": "需要网络搜索的问题",
            "body": {
                "model": "llama3",
                "messages": [{"role": "user", "content": "2023年的奥斯卡最佳电影是什么？"}]
            }
        },
        {
            "name": "需要知识库的问题",
            "body": {
                "model": "llama3",
                "messages": [{"role": "user", "content": "在我们的知识库中查找关于产品规格的文档"}]
            }
        }
    ]
    
    for case in test_cases:
        print(f"\n==== 测试: {case['name']} ====")
        request_id = str(uuid.uuid4())
        request = MockRequest(case["body"])
        target_url = "http://localhost:11434"  # 模拟Ollama服务器地址
        
        # 这里不会实际调用外部API，你可以通过日志或输出看到自动检测的结果
        # 如果需要真实的端到端测试，你需要模拟或使用实际的Ollama API
        response = MockResponse()
        
        try:
            # 因为不会实际调用Ollama，这里会引发错误，但我们只关注自动检测逻辑
            await handle_chat_request(request_id, request, request.body_bytes, target_url)
            print("✅ 请求处理成功")
        except Exception as e:
            print(f"❌ 请求处理出错 (这在没有实际Ollama服务的情况下是预期的): {str(e)}")
        
        # 分析日志输出来确认自动检测是否按预期工作

if __name__ == "__main__":
    asyncio.run(test_queries())
