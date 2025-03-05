import logging
from typing import List, Dict
import json
import requests
import sys
import io
import asyncio
from WebSearch.search.search_service import SearchService

# 配置日志以正确处理中文
logger = logging.getLogger(__name__)

# 检查是否已经添加了处理器，避免重复添加
if not logger.handlers:
    handler = logging.StreamHandler()  # 使用默认流而不是自定义的io.TextIOWrapper
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def format_search_results(results: List[Dict]) -> str:
    """格式化搜索结果为字符串"""
    formatted_results = []
    for idx, result in enumerate(results, 1):
        # 确保所有文本字段正确编码
        title = result['title'].encode('utf-8').decode('utf-8', errors='ignore') if result['title'] else ""
        link = result['link']
        snippet = result['snippet'].encode('utf-8').decode('utf-8', errors='ignore') if result['snippet'] else ""
        
        formatted_result = f"""
来源 {idx}:
标题: {title}
链接: {link}
摘要: {snippet}
"""
        if result.get('paragraphs'):
            formatted_result += "相关段落:\n"
            for p in result['paragraphs']:
                # 确保段落文本正确编码
                p_text = p['text'].encode('utf-8').decode('utf-8', errors='ignore') if p['text'] else ""
                formatted_result += f"- {p_text[:500]}...\n"
        
        formatted_results.append(formatted_result)
    
    return "\n".join(formatted_results)

def extract_search_queries(prompt: str) -> List[str]:
    """
    使用 Qwen 模型从用户prompt中提取搜索关键词
    返回一个搜索关键词列表
    """
    system_prompt = """你是一个搜索关键词提取助手。
请分析用户的对话内容，提取或者思考、扩展出4-5个需要搜索的关键短语。请你一步一步的多想一想。

要求:
1. 关键短语应该完整表达一个搜索意图
2. 每个短语3-10个字
3. 返回JSON数组格式
4. 只返回JSON数据，不要其他任何内容

示例:
用户问:"请介绍一下量子计算的原理和应用场景"
返回:["量子计算原理","量子计算商业应用","量子计算机发展现状"]"""

    extract_prompt = f"""{system_prompt}

用户问题/对话内容:
{prompt}
"""
    try:
        # 使用同步请求
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5",
                "prompt": extract_prompt,
                "stream": False
            }
        )
        result = response.json()
        response_text = result.get('response', '')
        
        # 尝试解析JSON内容
        try:
            json_str = response_text.strip()
            if not json_str.startswith('['):
                import re
                json_match = re.search(r'\[(.*?)\]', json_str)
                if json_match:
                    json_str = f"[{json_match.group(1)}]"
            
            search_queries = json.loads(json_str)
            logger.info(f"提取的搜索关键词: {search_queries}")
            return search_queries
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}, 原始返回: {response_text}")
            return [prompt]
            
    except Exception as e:
        logger.error(f"提取搜索关键词失败: {str(e)}")
        return [prompt]

async def _search_single_query(service, query: str, search_options: dict, 
                             total_queries: int, query_idx: int, 
                             send_progress=None) -> List[dict]:
    """处理单个搜索查询的异步函数"""
    try:
        if send_progress:
            await send_progress(f"正在搜索({query_idx}/{total_queries}): {query}")
            
        response = service.search(
            query=query,
            min_results=max(15, search_options.get("min_results", 15) // total_queries),
            max_pages=search_options.get("max_pages", 16)
        )
        
        results = json.loads(response.to_json())
        
        if send_progress:
            await send_progress(f"完成关键词 '{query}' 的搜索，找到 {len(results['results'])} 条结果")
            
        return results['results']
        
    except Exception as search_error:
        logger.error(f"搜索关键词 '{query}' 时出错: {str(search_error)}")
        if send_progress:
            await send_progress(f"搜索关键词 '{query}' 时出错: {str(search_error)}")
        return []

async def process_web_search(request_data, send_progress=None):
    """处理网页搜索功能,返回搜索结果和元数据"""
    logger.info("正在处理Web搜索请求...")
    
    # 提取用户查询 - 增强提取逻辑以适应不同格式
    original_prompt = ""
    
    # 尝试从不同格式中提取用户查询
    if isinstance(request_data.get("prompt"), str):
        original_prompt = request_data["prompt"]
    elif isinstance(request_data.get("prompt"), list):
        for item in request_data["prompt"]:
            if item.get("type") == "text":
                original_prompt = item.get("text", "")
                break
    elif "messages" in request_data and isinstance(request_data["messages"], list):
        for msg in reversed(request_data["messages"]):
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                original_prompt = msg["content"]
                break
    
    # 记录提取到的查询以便调试
    logger.info(f"提取到的用户查询: {original_prompt}")
    
    search_options = request_data.get("search_options", {})
   
    
    try:
        search_queries = extract_search_queries(original_prompt)
        if send_progress:
            await send_progress(f"已确定搜索关键词: {', '.join(search_queries)}")
            
        service = SearchService(
            engines=search_options.get("engines", ["google_api"])
        )
        
        # 并行执行所有搜索查询
        search_tasks = [
            _search_single_query(
                service, 
                query, 
                search_options, 
                len(search_queries),
                i+1, 
                send_progress
            )
            for i, query in enumerate(search_queries)
        ]
        
        # 等待所有搜索完成
        results_list = await asyncio.gather(*search_tasks)
        
        # 合并所有结果
        all_results = []
        for results in results_list:
            all_results.extend(results)
            
        formatted_results = format_search_results(all_results)
        
        return {
            "search_results": formatted_results,
            "metadata": {
                "search_queries": search_queries,
                "total_results": len(all_results),
                "sources": list(set(r["link"] for r in all_results))
            }
        }
        
    except Exception as e:
        logger.error(f"搜索过程出错: {str(e)}")
        if send_progress:
            await send_progress(f"搜索过程发生错误: {str(e)}")
        return {
            "search_results": "",
            "metadata": {}
        }

# 使用示例:
"""
request_data = {
    "prompt": "什么是向量数据库？",
    "search_options": {
        "engines": ["bing", "google"],
        "min_results": 5,
        "max_pages": 2
    }
}

result = await process_web_search(request_data)
print(result["prompt"])  # 增强后的提示词
print(result["search_metadata"])  # 搜索元数据
"""
