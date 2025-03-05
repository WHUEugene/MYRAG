import os
import sys
import json
from datetime import datetime

# 添加父目录到路径，以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_fc import QwenClient, tools, handle_function_calls
from utils.debug_helpers import log_api_interaction, analyze_function_calls


def debug_function_call(query: str, previous_messages=None):
    """
    用于调试单个function call的函数
    
    参数:
    query - 用户查询
    previous_messages - 之前的对话历史，可选
    
    返回:
    处理后的结果和完整的API响应
    """
    # 从环境变量获取API密钥
    api_key = os.environ.get("SILICONFLOW_KEY")
    if not api_key:
        print("请设置SILICONFLOW_KEY环境变量")
        return None, None
    
    client = QwenClient(api_key)
    
    # 设置消息
    messages = previous_messages or []
    if not messages:
        messages.append({"role": "system", "content": "你是一个旅游助手，可以提供城市间距离计算、天气查询和周边设施查询等服务。"})
    
    messages.append({"role": "user", "content": query})
    
    # 创建日志文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"debug_call_{timestamp}.log")
    
    print(f"发送请求到API，查询: '{query}'")
    print(f"详细日志将保存到: {log_file}")
    
    # 调用API
    response = client.chat_completion(messages, tools=tools)
    
    # 记录交互
    log_api_interaction(
        {"model": "Qwen/Qwen2.5-72B-Instruct", "messages": messages, "tools": tools},
        response, 
        log_file
    )
    
    # 分析函数调用
    analysis = analyze_function_calls(response)
    
    # 打印分析结果
    if analysis["has_function_calls"]:
        print(f"\n检测到 {len(analysis['function_calls'])} 个函数调用:")
        for i, fc in enumerate(analysis["function_calls"]):
            print(f"  {i+1}. 函数: {fc['function_name']}")
            print(f"     参数有效: {'是' if fc['arguments_valid'] else '否'}")
            
            # 如果参数是字典，以漂亮的格式打印
            if isinstance(fc["arguments"], dict):
                arg_str = json.dumps(fc["arguments"], ensure_ascii=False, indent=2)
                print(f"     参数: {arg_str}")
            else:
                print(f"     参数: {fc['arguments']}")
    else:
        print("\n未检测到函数调用")
    
    if analysis["errors"]:
        print("\n错误:")
        for error in analysis["errors"]:
            print(f"  - {error}")
    
    # 处理结果
    result = handle_function_calls(response)
    print(f"\n处理结果: {result}")
    
    return result, response


def debug_specific_scenarios():
    """调试特定的问题场景"""
    
    # 测试场景1: 测试天气查询
    print("\n===== 测试场景1: 天气查询 =====")
    query1 = "北京今天天气怎么样？"
    result1, response1 = debug_function_call(query1)
    
    # 测试场景2: 测试地点搜索
    print("\n===== 测试场景2: 地点搜索 =====")
    query2 = "请查找故宫(纬度39.9163, 经度116.3972)附近2公里内的酒店"
    result2, response2 = debug_function_call(query2)
    
    # 测试场景3: 组合查询
    print("\n===== 测试场景3: 组合查询 =====")
    query3 = "北京到上海的距离是多少？上海今天的天气怎么样？"
    result3, response3 = debug_function_call(query3)


if __name__ == "__main__":
    debug_specific_scenarios()
    
    # 允许用户输入自定义查询进行调试
    while True:
        user_input = input("\n输入测试查询 (输入'exit'退出): ")
        if user_input.lower() in ("exit", "quit", "q"):
            break
        
        debug_function_call(user_input)
