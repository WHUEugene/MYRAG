import os
import json
import sys
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入测试模块
from test_fc import QwenClient, tools, calculate_distance, get_weather, search_nearby_places

def test_single_query_with_function_calling():
    """测试单个查询中的函数调用和返回结果"""
    # 从环境变量获取API密钥
    api_key = os.environ.get("SILICONFLOW_KEY")
    if not api_key:
        print("请设置SILICONFLOW_KEY环境变量")
        return
    
    client = QwenClient(api_key)
    
    # 准备查询
    messages = [
        {"role": "system", "content": "你是一个旅游助手，可以提供城市间距离计算、天气查询和周边设施查询等服务。"},
        {"role": "user", "content": "北京到上海的距离是多少公里？顺便告诉我北京今天的天气如何？"}
    ]
    
    print("\n===== 测试单个查询中的函数调用和返回结果 =====")
    print(f"用户: {messages[-1]['content']}")
    
    # 执行函数调用和对话
    response = client.execute_function_call_and_continue(messages.copy(), tools, "单查询测试")
    
    # 输出最终回复
    if "choices" in response and len(response["choices"]) > 0:
        final_reply = response["choices"][0]["message"].get("content", "")
        print("\n助手最终回复:")
        print(final_reply)
    
    print("\n===== 单查询测试结束 =====")


def test_conversational_assistant():
    """测试多轮对话中的函数调用和返回结果"""
    # 从环境变量获取API密钥
    api_key = os.environ.get("SILICONFLOW_KEY")
    if not api_key:
        print("请设置SILICONFLOW_KEY环境变量")
        return
    
    client = QwenClient(api_key)
    
    # 初始化对话历史
    messages = [
        {"role": "system", "content": "你是一个旅游助手，可以提供城市间距离计算、天气查询和周边设施查询等服务。"}
    ]
    
    print("\n===== 测试多轮对话中的函数调用和结果处理 =====")
    
    # 第一轮对话
    user_message = "我要从北京去上海旅游，这两个城市相距多远？"
    messages.append({"role": "user", "content": user_message})
    print(f"\n用户: {user_message}")
    
    response = client.execute_function_call_and_continue(messages.copy(), tools, "对话测试-轮次1")
    
    if "choices" in response and len(response["choices"]) > 0:
        assistant_reply = response["choices"][0]["message"].get("content", "")
        print(f"\n助手: {assistant_reply}")
        messages.append({"role": "assistant", "content": assistant_reply})
    
    # 第二轮对话
    user_message = "北京现在天气怎么样？在故宫附近有哪些好酒店推荐？"
    messages.append({"role": "user", "content": user_message})
    print(f"\n用户: {user_message}")
    
    response = client.execute_function_call_and_continue(messages.copy(), tools, "对话测试-轮次2")
    
    if "choices" in response and len(response["choices"]) > 0:
        assistant_reply = response["choices"][0]["message"].get("content", "")
        print(f"\n助手: {assistant_reply}")
        messages.append({"role": "assistant", "content": assistant_reply})
    
    # 第三轮对话
    user_message = "我到上海后想参观东方明珠，周边有哪些景点可以一起游览？"
    messages.append({"role": "user", "content": user_message})
    print(f"\n用户: {user_message}")
    
    response = client.execute_function_call_and_continue(messages.copy(), tools, "对话测试-轮次3")
    
    if "choices" in response and len(response["choices"]) > 0:
        assistant_reply = response["choices"][0]["message"].get("content", "")
        print(f"\n助手: {assistant_reply}")
    
    print("\n===== 多轮对话测试结束 =====")


def interactive_assistant():
    """交互式助手模式，允许用户进行多轮对话"""
    # 从环境变量获取API密钥
    api_key = os.environ.get("SILICONFLOW_KEY")
    if not api_key:
        print("请设置SILICONFLOW_KEY环境变量")
        return
    
    client = QwenClient(api_key)
    
    # 初始化对话历史
    messages = [
        {"role": "system", "content": "你是一个旅游助手，可以提供城市间距离计算、天气查询和周边设施查询等服务。"}
    ]
    
    print("\n===== 交互式旅游助手 =====")
    print("您可以询问城市间距离、天气状况、周边景点等信息。")
    print("输入'exit'或'quit'退出对话。")
    
    while True:
        # 获取用户输入
        user_input = input("\n您: ")
        
        # 检查是否退出
        if user_input.lower() in ("exit", "quit", "q"):
            print("谢谢使用！再见！")
            break
        
        # 添加到对话历史
        messages.append({"role": "user", "content": user_input})
        
        # 执行函数调用和对话
        print("AI思考中...")
        response = client.execute_function_call_and_continue(messages.copy(), tools, "交互式对话")
        
        # 输出回复
        if "choices" in response and len(response["choices"]) > 0:
            assistant_reply = response["choices"][0]["message"].get("content", "")
            print(f"\n助手: {assistant_reply}")
            
            # 更新对话历史
            messages.append({"role": "assistant", "content": assistant_reply})


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试大模型函数调用和助手模式")
    parser.add_argument("--mode", type=str, choices=["single", "conversation", "interactive"], 
                        default="interactive", help="测试模式：单查询/多轮对话/交互式")
    
    args = parser.parse_args()
    
    if args.mode == "single":
        test_single_query_with_function_calling()
    elif args.mode == "conversation":
        test_conversational_assistant()
    else:
        interactive_assistant()
