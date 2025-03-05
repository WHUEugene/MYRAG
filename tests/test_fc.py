import os
import json
import requests
import math
import random
from datetime import datetime
from typing import Dict, List, Any, Optional

# 计算两点之间距离的函数
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用Haversine公式计算两个坐标点之间的距离（单位：公里）
    
    参数:
    lat1, lon1 - 第一个点的纬度和经度
    lat2, lon2 - 第二个点的纬度和经度
    
    返回:
    两点之间的距离，单位为公里
    """
    # 地球半径（公里）
    R = 6371.0
    
    # 将经纬度转换为弧度
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine公式
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return distance

# 新增功能：获取城市天气信息
def get_weather(city: str) -> Dict[str, Any]:
    """
    获取指定城市的天气信息
    
    参数:
    city - 城市名称
    
    返回:
    包含温度、天气状况等信息的字典
    """
    # 模拟天气数据
    weather_conditions = ["晴朗", "多云", "小雨", "大雨", "雷阵雨", "阴天", "雾霾"]
    temp_range = {"北京": (15, 30), "上海": (18, 32), "广州": (22, 35), "深圳": (23, 36), "杭州": (17, 31)}
    
    # 修复：处理嵌套的JSON对象
    if isinstance(city, dict) and "city" in city:
        city = city["city"]
    
    if city not in temp_range:
        return {"error": f"不支持的城市: {city}"}
    
    min_temp, max_temp = temp_range[city]
    temp = round(random.uniform(min_temp, max_temp), 1)
    condition = random.choice(weather_conditions)
    humidity = random.randint(30, 90)
    
    return {
        "city": city,
        "temperature": temp,
        "condition": condition,
        "humidity": humidity,
        "date": datetime.now().strftime("%Y-%m-%d")
    }

# 新增功能：搜索附近地点
def search_nearby_places(lat: float, lon: float, query: str, radius: float = 5.0) -> List[Dict[str, Any]]:
    """
    搜索指定坐标附近的地点
    
    参数:
    lat - 纬度
    lon - 经度
    query - 搜索关键词
    radius - 搜索半径(公里)
    
    返回:
    符合条件的地点列表
    """
    # 模拟POI数据
    poi_data = {
        "餐厅": [
            {"name": "北京烤鸭店", "lat": 39.9142, "lon": 116.4074, "rating": 4.8},
            {"name": "海底捞火锅", "lat": 39.9102, "lon": 116.4114, "rating": 4.7},
            {"name": "星巴克咖啡", "lat": 39.9052, "lon": 116.4094, "rating": 4.5},
        ],
        "酒店": [
            {"name": "希尔顿酒店", "lat": 39.9062, "lon": 116.4084, "rating": 4.9},
            {"name": "如家快捷酒店", "lat": 39.9022, "lon": 116.4054, "rating": 4.2},
        ],
        "景点": [
            {"name": "故宫博物院", "lat": 39.9163, "lon": 116.3972, "rating": 5.0},
            {"name": "天安门广场", "lat": 39.9054, "lon": 116.3976, "rating": 4.9},
            {"name": "颐和园", "lat": 40.0000, "lon": 116.2755, "rating": 4.8},
        ]
    }
    
    results = []
    query_terms = ["餐厅", "酒店", "景点"]
    search_term = next((term for term in query_terms if term in query), "餐厅")
    
    for place in poi_data.get(search_term, []):
        place_lat = place["lat"]
        place_lon = place["lon"]
        
        # 计算距离
        distance = calculate_distance(lat, lon, place_lat, place_lon)
        
        if distance <= radius:
            place_with_distance = place.copy()
            place_with_distance["distance"] = round(distance, 2)
            results.append(place_with_distance)
    
    # 按距离排序
    return sorted(results, key=lambda x: x["distance"])

# 扩展Function Call定义
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_distance",
            "description": "计算两个地理坐标点之间的距离",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat1": {
                        "type": "number",
                        "description": "第一个点的纬度"
                    },
                    "lon1": {
                        "type": "number",
                        "description": "第一个点的经度"
                    },
                    "lat2": {
                        "type": "number",
                        "description": "第二个点的纬度"
                    },
                    "lon2": {
                        "type": "number",
                        "description": "第二个点的经度"
                    }
                },
                "required": ["lat1", "lon1", "lat2", "lon2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_nearby_places",
            "description": "搜索指定坐标附近的地点",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "中心点纬度"
                    },
                    "lon": {
                        "type": "number",
                        "description": "中心点经度"
                    },
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如'餐厅'、'酒店'、'景点'"
                    },
                    "radius": {
                        "type": "number",
                        "description": "搜索半径(公里)"
                    }
                },
                "required": ["lat", "lon", "query"]
            }
        }
    }
]

def handle_function_calls(response_data: Dict[str, Any]) -> Any:
    """处理API返回的function call结果"""
    if "choices" not in response_data:
        return "无法解析API响应"
    
    choice = response_data["choices"][0]
    
    if "message" in choice and "tool_calls" in choice["message"]:
        tool_calls = choice["message"]["tool_calls"]
        results = []
        
        for tool_call in tool_calls:
            if tool_call["type"] != "function":
                continue
                
            function_name = tool_call["function"]["name"]
            try:
                # 修复：确保字符串参数正确解析为JSON
                args_str = tool_call["function"]["arguments"]
                
                # 打印原始参数以便调试
                print(f"DEBUG - 函数 {function_name} 的原始参数: {args_str}")
                
                # 尝试解析JSON，处理可能的异常
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    print(f"警告: 无法解析参数JSON: {args_str}")
                    args = {}
                
                if function_name == "calculate_distance":
                    distance = calculate_distance(
                        float(args["lat1"]), float(args["lon1"]), 
                        float(args["lat2"]), float(args["lon2"])
                    )
                    results.append(f"两点之间的距离为: {distance:.2f} 公里")
                
                elif function_name == "get_weather":
                    # 修复：处理不同格式的city参数
                    if isinstance(args, dict) and "city" in args:
                        city = args["city"]
                    elif isinstance(args, str):
                        # 尝试将纯字符串解析为JSON
                        try:
                            parsed = json.loads(args)
                            city = parsed.get("city", args)
                        except json.JSONDecodeError:
                            city = args
                    else:
                        city = str(args)
                        
                    weather_data = get_weather(city)
                    if "error" in weather_data:
                        results.append(f"获取天气信息失败: {weather_data['error']}")
                    else:
                        results.append(
                            f"{weather_data['city']}今日天气: {weather_data['condition']}, "
                            f"温度{weather_data['temperature']}°C, 湿度{weather_data['humidity']}%"
                        )
                
                elif function_name == "search_nearby_places":
                    # 修复：处理JSON字符串参数问题
                    if isinstance(args_str, str) and not args:
                        # 如果JSON解析失败，尝试替代方法提取参数
                        import re
                        # 使用正则表达式提取数值
                        lat_match = re.search(r'"lat":\s*([\d\.]+)', args_str)
                        lon_match = re.search(r'"lon":\s*([\d\.]+)', args_str)
                        query_match = re.search(r'"query":\s*"([^"]+)"', args_str)
                        radius_match = re.search(r'"radius":\s*([\d\.]+)', args_str)
                        
                        lat = float(lat_match.group(1)) if lat_match else 0
                        lon = float(lon_match.group(1)) if lon_match else 0
                        query = query_match.group(1) if query_match else "餐厅"
                        radius = float(radius_match.group(1)) if radius_match else 5.0
                    else:
                        # 正常情况下提取参数
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        lat = float(args.get("lat", 0)) if isinstance(args, dict) else 0
                        lon = float(args.get("lon", 0)) if isinstance(args, dict) else 0
                        query = args.get("query", "餐厅") if isinstance(args, dict) else "餐厅"
                        radius = float(args.get("radius", 5.0)) if isinstance(args, dict) else 5.0
                    
                    places = search_nearby_places(lat, lon, query, radius)
                    
                    if not places:
                        results.append(f"在{radius}公里范围内没有找到匹配'{query}'的地点")
                    else:
                        place_info = [f"{p['name']} (距离{p['distance']}公里，评分{p['rating']})" for p in places[:3]]
                        results.append(f"在附近找到的{query}:\n" + "\n".join(place_info))
                
                else:
                    results.append(f"未知函数: {function_name}")
                    
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                results.append(f"处理函数{function_name}时出错: {str(e)}")
                print(f"详细错误信息:\n{error_detail}")
        
        return "\n\n".join(results) if results else "模型调用的函数未返回结果"
    
    # 如果没有工具调用，返回模型的文本回复
    if "message" in choice and "content" in choice["message"] and choice["message"]["content"]:
        return choice["message"]["content"]
    
    return "模型没有调用函数或给出回复"

def print_request_response(request_data: Dict, response_data: Dict, title: str = "API交互"):
    """详细打印请求和响应信息"""
    print(f"\n===== {title} =====")
    print("请求内容:")
    
    # 打印请求消息
    if "messages" in request_data:
        for msg in request_data["messages"]:
            role = msg["role"]
            content = msg["content"]
            print(f"- [{role}]: {content[:100]}..." if len(content) > 100 else f"- [{role}]: {content}")
    
    # 打印工具定义（简化版本）
    if "tools" in request_data:
        print(f"- 工具数量: {len(request_data['tools'])}")
        for tool in request_data["tools"]:
            if tool["type"] == "function" and "function" in tool:
                print(f"  - 函数: {tool['function']['name']}")
    
    print("\n响应内容:")
    
    # 打印选择结果
    if "choices" in response_data and len(response_data["choices"]) > 0:
        choice = response_data["choices"][0]
        
        # 打印内容
        if "message" in choice:
            msg = choice["message"]
            if "content" in msg and msg["content"]:
                print(f"- 内容: {msg['content'][:100]}..." if len(msg['content'] or "") > 100 else f"- 内容: {msg['content']}")
            
            # 打印工具调用
            if "tool_calls" in msg:
                print("- 工具调用:")
                for tc in msg["tool_calls"]:
                    if tc["type"] == "function":
                        fn = tc["function"]
                        print(f"  - 函数: {fn['name']}")
                        print(f"  - 参数: {fn['arguments']}")
    
    print(f"===== {title} 结束 =====\n")

class QwenClient:
    def __init__(self, api_key: str = None):
        """初始化Qwen API客户端"""
        self.api_key = api_key or os.environ.get("QWEN_API_KEY")
        if not self.api_key:
            raise ValueError("API密钥未提供。请设置QWEN_API_KEY环境变量或者在初始化时提供。")
        
        self.endpoint = "https://api.siliconflow.cn/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                       model: str = "Qwen/Qwen2.5-72B-Instruct",
                       tools: Optional[List[Dict[str, Any]]] = None,
                       title: str = "API调用") -> Dict[str, Any]:
        """
        发送聊天请求到Qwen API
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.7
        }
        
        if tools:
            payload["tools"] = tools
        
        # 记录请求信息
        print(f"\n准备{title}请求...")
            
        response = requests.post(self.endpoint, headers=self.headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} {response.text}")
        
        response_data = response.json()
        
        # 打印详细的请求和响应信息
        print_request_response(payload, response_data, title)
            
        return response_data

    def execute_function_call_and_continue(self, messages: List[Dict], 
                                          tools: List[Dict], 
                                          title: str = "函数调用和继续对话") -> Dict:
        """
        执行Function Call并将结果返回给模型继续对话
        
        步骤：
        1. 发送初始请求，检查是否有函数调用
        2. 如果有函数调用，执行函数并获取结果
        3. 将函数结果作为新消息发送给模型继续对话
        4. 返回最终回复
        """
        # 初始请求
        initial_response = self.chat_completion(messages, tools=tools, title=f"{title} - 初始请求")
        
        # 检查是否有函数调用
        if "choices" not in initial_response or len(initial_response["choices"]) == 0:
            print("初始响应中没有有效选择")
            return initial_response
        
        choice = initial_response["choices"][0]
        if "message" not in choice or "tool_calls" not in choice["message"]:
            print("没有函数调用，直接返回初始响应")
            return initial_response
        
        # 有函数调用，处理它们
        print("\n检测到函数调用，执行函数...")
        assistant_message = choice["message"]
        tool_calls = assistant_message["tool_calls"]
        
        # 创建助手消息（包含函数调用的消息）
        messages.append({
            "role": "assistant",
            "content": assistant_message.get("content", ""),
            "tool_calls": tool_calls
        })
        
        # 为每个函数调用执行函数并添加结果
        for tool_call in tool_calls:
            if tool_call["type"] != "function":
                continue
                
            function_name = tool_call["function"]["name"]
            function_id = tool_call["id"]
            args_str = tool_call["function"]["arguments"]
            
            print(f"执行函数: {function_name}")
            
            try:
                # 解析参数并执行函数
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
                
                # 根据函数名调用相应的函数
                result = None
                if function_name == "calculate_distance":
                    result = calculate_distance(
                        float(args["lat1"]), float(args["lon1"]), 
                        float(args["lat2"]), float(args["lon2"])
                    )
                    result = f"两点之间的距离为{result:.2f}公里"
                    
                elif function_name == "get_weather":
                    # 处理不同格式的city参数
                    if isinstance(args, dict) and "city" in args:
                        city = args["city"]
                    else:
                        city = str(args)
                        
                    weather_data = get_weather(city)
                    if "error" in weather_data:
                        result = f"获取天气信息失败: {weather_data['error']}"
                    else:
                        result = json.dumps(weather_data, ensure_ascii=False)
                    
                elif function_name == "search_nearby_places":
                    # 确保参数正确
                    lat = float(args["lat"]) if "lat" in args else 0
                    lon = float(args["lon"]) if "lon" in args else 0
                    query = args["query"] if "query" in args else "餐厅"
                    radius = float(args.get("radius", 5.0))
                    
                    places = search_nearby_places(lat, lon, query, radius)
                    result = json.dumps(places, ensure_ascii=False)
                
                else:
                    result = f"未知函数: {function_name}"
                    
                # 将函数执行结果添加到消息列表
                messages.append({
                    "role": "tool",
                    "tool_call_id": function_id,
                    "name": function_name,
                    "content": str(result)
                })
                
                print(f"函数 {function_name} 执行结果: {result[:100]}..." if len(str(result)) > 100 else f"函数 {function_name} 执行结果: {result}")
                
            except Exception as e:
                error_message = f"函数执行错误: {str(e)}"
                print(error_message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": function_id,
                    "name": function_name,
                    "content": error_message
                })
        
        # 发送新请求，包含函数执行结果
        print("\n发送函数执行结果给模型继续对话...")
        final_response = self.chat_completion(messages, tools=tools, title=f"{title} - 继续对话")
        
        return final_response

def complex_conversation_with_function_results(client):
    """执行复杂的对话测试，包含多轮对话和函数调用及其结果"""
    print("\n===== 开始复杂对话测试(带函数结果反馈) =====")
    
    # 初始化聊天历史
    messages = [
        {"role": "system", "content": "你是一个旅游助手，可以提供城市间距离计算、天气查询和周边设施查询等服务。"}
    ]
    
    # 第一轮对话：询问城市间距离和天气
    user_query = "我计划从北京去上海旅游，这两个城市之间相距多远？北京今天天气怎么样？"
    print(f"\n用户: {user_query}")
    
    messages.append({"role": "user", "content": user_query})
    response = client.execute_function_call_and_continue(messages.copy(), tools, title="第一轮对话")
    
    # 获取模型最终回复
    if "choices" in response and len(response["choices"]) > 0:
        final_reply = response["choices"][0]["message"].get("content", "")
        print(f"助手最终回复: {final_reply}")
        
        # 更新对话历史
        messages.append({"role": "assistant", "content": final_reply})
    
    # 第二轮对话：询问附近的酒店和餐厅
    user_query = "我到达北京后想住在故宫附近，请帮我查找故宫周围2公里内的酒店，以及有什么好吃的餐厅推荐？"
    print(f"\n用户: {user_query}")
    
    messages.append({"role": "user", "content": user_query})
    response = client.execute_function_call_and_continue(messages.copy(), tools, title="第二轮对话")
    
    # 获取模型最终回复
    if "choices" in response and len(response["choices"]) > 0:
        final_reply = response["choices"][0]["message"].get("content", "")
        print(f"助手最终回复: {final_reply}")
        
        # 更新对话历史
        messages.append({"role": "assistant", "content": final_reply})
    
    # 第三轮对话：询问上海天气和景点
    user_query = "上海最近天气如何？我想知道上海有哪些著名景点可以游览。"
    print(f"\n用户: {user_query}")
    
    messages.append({"role": "user", "content": user_query})
    response = client.execute_function_call_and_continue(messages.copy(), tools, title="第三轮对话")
    
    # 获取模型最终回复
    if "choices" in response and len(response["choices"]) > 0:
        final_reply = response["choices"][0]["message"].get("content", "")
        print(f"助手最终回复: {final_reply}")
    
    print("\n===== 复杂对话测试(带函数结果反馈)结束 =====")

def main():
    # 从环境变量获取API密钥
    api_key = os.environ.get("SILICONFLOW_KEY")
    if not api_key:
        print("请设置SILICONFLOW_KEY环境变量")
        return
    
    client = QwenClient(api_key)
    
    # 测试天气和地点搜索功能
    print("\n===== 功能单元测试 =====")
    print("测试天气功能:")
    print(get_weather("上海"))
    
    print("\n测试地点搜索功能:")
    places = search_nearby_places(31.2304, 121.4737, "景点", 10)
    for place in places[:3]:
        print(f"- {place['name']} (距离{place['distance']}公里)")
    
    # 执行带有函数结果反馈的复杂对话测试
    complex_conversation_with_function_results(client)

if __name__ == "__main__":
    main()
