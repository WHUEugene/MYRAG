import json
from typing import Dict, Any, List, Optional


def format_json(data: Any, indent: int = 2) -> str:
    """
    将数据格式化为易读的JSON字符串
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


def log_api_interaction(request_data: Dict[str, Any], response_data: Dict[str, Any], 
                        log_file: Optional[str] = None) -> None:
    """
    记录API请求和响应
    
    参数:
    request_data - API请求数据
    response_data - API响应数据
    log_file - 日志文件路径，如果提供则写入文件
    """
    log = []
    
    # 请求信息
    log.append("===== API请求 =====")
    if "model" in request_data:
        log.append(f"模型: {request_data['model']}")
    
    if "messages" in request_data:
        log.append("消息:")
        for msg in request_data["messages"]:
            log.append(f"- [{msg['role']}]: {msg['content'][:200]}...")
    
    if "tools" in request_data:
        log.append(f"工具定义: {len(request_data['tools'])} 个工具")
    
    # 响应信息
    log.append("\n===== API响应 =====")
    if "choices" in response_data and len(response_data["choices"]) > 0:
        choice = response_data["choices"][0]
        
        if "message" in choice:
            message = choice["message"]
            
            if "content" in message and message["content"]:
                log.append(f"内容: {message['content']}")
            
            if "tool_calls" in message:
                log.append("工具调用:")
                for tool_call in message["tool_calls"]:
                    if tool_call["type"] == "function":
                        function = tool_call["function"]
                        log.append(f"- 函数: {function['name']}")
                        log.append(f"  参数: {function['arguments']}")
    
    log_content = "\n".join(log)
    
    # 写入文件或打印到控制台
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_content)
            f.write("\n\n" + "-"*50 + "\n\n")
    else:
        print(log_content)


def analyze_function_calls(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析API响应中的function calls，提取有用信息
    
    返回:
    包含函数调用分析的字典
    """
    result = {
        "has_function_calls": False,
        "function_calls": [],
        "errors": []
    }
    
    if "choices" not in response_data:
        result["errors"].append("响应中没有choices字段")
        return result
    
    choice = response_data["choices"][0]
    
    if "message" not in choice:
        result["errors"].append("响应中没有message字段")
        return result
    
    message = choice["message"]
    
    if "tool_calls" not in message:
        return result  # 没有函数调用，返回默认结果
    
    result["has_function_calls"] = True
    
    for tool_call in message["tool_calls"]:
        if tool_call["type"] != "function":
            continue
        
        function = tool_call["function"]
        
        try:
            args = json.loads(function["arguments"]) if isinstance(function["arguments"], str) else function["arguments"]
            valid_args = True
        except json.JSONDecodeError:
            args = function["arguments"]
            valid_args = False
            result["errors"].append(f"函数 {function['name']} 的参数解析失败")
        
        function_call = {
            "function_name": function["name"],
            "arguments": args,
            "arguments_valid": valid_args
        }
        
        result["function_calls"].append(function_call)
    
    return result
