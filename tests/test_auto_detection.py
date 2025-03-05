import sys
import os
import json
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from proxyrequest.TaskManager import TaskManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MockSendProgress:
    """模拟发送进度消息的回调函数"""
    def __init__(self):
        self.messages = []
    
    async def __call__(self, msg):
        self.messages.append(msg)
        print(f"进度消息: {msg}")

async def test_auto_detection():
    # 测试案例
    test_cases = [
        # 网络搜索案例
        {
            "name": "网络搜索查询",
            "request": {
                "model": "llama3",
                "messages": [
                    {"role": "user", "content": "最近的世界杯是在哪里举办的？"}
                ],
                "options": {"auto_detect": True}
            },
            "expected_features": ["web_search_enabled"]
        },
        # 知识库案例
        {
            "name": "知识库查询",
            "request": {
                "model": "llama3",
                "messages": [
                    {"role": "user", "content": "在知识库中查找关于太阳能电池的资料"}
                ],
                "options": {"auto_detect": True}
            },
            "expected_features": ["rag_enabled"]
        },
        # 混合案例
        {
            "name": "混合查询",
            "request": {
                "model": "llama3",
                "messages": [
                    {"role": "user", "content": "请在知识库中查找关于太阳能的最新研究进展"}
                ],
                "options": {"auto_detect": True}
            },
            "expected_features": ["rag_enabled", "web_search_enabled"]
        },
        # 用户覆盖案例
        {
            "name": "用户覆盖",
            "request": {
                "model": "llama3",
                "messages": [
                    {"role": "user", "content": "最近的世界杯是在哪里举办的？"}
                ],
                "options": {"auto_detect": True, "web_search_enabled": False}
            },
            "expected_features": []
        },
        # 自动检测禁用案例
        {
            "name": "禁用自动检测",
            "request": {
                "model": "llama3",
                "messages": [
                    {"role": "user", "content": "最近的世界杯是在哪里举办的？"}
                ],
                "options": {"auto_detect": False}
            },
            "expected_features": []
        }
    ]
    
    # 执行测试
    for i, case in enumerate(test_cases):
        print(f"\n==== 测试案例 {i+1}: {case['name']} ====")
        request = case["request"]
        expected_features = case["expected_features"]
        
        mock_progress = MockSendProgress()
        task_manager = TaskManager("test-request", request, mock_progress)
        
        # 运行任务处理（这里我们只测试检测逻辑，不实际运行任务）
        # 通过检查任务管理器内部状态来验证自动检测结果
        # 修改TaskManager以输出检测结果
        
        # 获取自动检测结果
        if task_manager.auto_detect_enabled:
            auto_options = task_manager.query_analyzer.extract_options_from_message(request)
            print(f"自动检测结果: {auto_options}")
            
            # 检查是否符合预期
            actual_features = [feature for feature, enabled in auto_options.items() if enabled]
            missed_features = [f for f in expected_features if f not in actual_features]
            unexpected_features = [f for f in actual_features if f not in expected_features]
            
            if not missed_features and not unexpected_features:
                print("✅ 检测结果符合预期")
            else:
                print("❌ 检测结果不符合预期")
                if missed_features:
                    print(f"缺少功能: {missed_features}")
                if unexpected_features:
                    print(f"意外启用功能: {unexpected_features}")
        else:
            print("⚠️ 自动检测已禁用")

if __name__ == "__main__":
    asyncio.run(test_auto_detection())
