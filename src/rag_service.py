import os
import json
import aiohttp
import logging
from dotenv import load_dotenv
from typing import List, Dict

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 配置常量
DOC_SERVER_URL = f"http://localhost:{os.getenv('DOC_SERVER_PORT', 5001)}"

# 获取默认知识库ID
async def get_default_kb_id():
    """获取默认知识库ID，如果没有则返回None"""
    try:
        # 实现一个API，或者从配置文件直接读取第一个知识库
        url = f"{DOC_SERVER_URL}/api/knowledge-base/list"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    kb_list = data.get('kb_list', {})
                    
                    if not kb_list:
                        logger.warning("没有找到任何知识库")
                        return None
                    
                    # 返回第一个知识库的ID
                    first_kb_id = next(iter(kb_list.keys()), None)
                    logger.info(f"找到默认知识库 ID: {first_kb_id}")
                    return first_kb_id
                else:
                    logger.error(f"获取知识库列表失败: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"获取默认知识库异常: {str(e)}")
        return None

async def search_kb(kb_id, query, top_k=3):
    """从知识库中搜索信息"""
    logger.debug(f"开始搜索知识库 {kb_id}, 查询: '{query}'")
    
    try:
        url = f"{DOC_SERVER_URL}/api/knowledge-base/{kb_id}/search"
        payload = {"query": query, "top_k": top_k}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    results = await response.json()
                    logger.debug(f"知识库搜索成功, 找到 {len(results.get('results', []))} 条结果")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"知识库搜索失败: {response.status}, {error_text}")
                    return {"error": f"搜索失败: {response.status}", "results": []}
    except Exception as e:
        logger.error(f"知识库搜索异常: {str(e)}")
        return {"error": str(e), "results": []}

async def process_rag(request_body):
    """处理RAG请求"""
    try:
        # 提取原始请求信息
        model = request_body.get("model", "")
        prompt = request_body.get("prompt", "")
        messages = request_body.get("messages", [])
        user_query = ""
        
        # 从不同格式中提取用户查询
        if messages and len(messages) > 0:
            # 从最后一条用户消息中获取查询
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_query = msg.get("content", "")
                    break
        elif prompt:
            # 使用prompt作为查询
            user_query = prompt
        
        if not user_query:
            logger.warning("未能提取到用户查询")
            return {"prompt": request_body.get("prompt", ""), "rag_results": ""}
            
        logger.info(f"处理RAG请求，用户查询: '{user_query}'")
        
        # 获取上下文信息
        all_contexts = []
        
        # 获取默认知识库ID
        default_kb_id = await get_default_kb_id()
        if not default_kb_id:
            logger.warning("未找到有效的知识库，跳过知识库搜索")
        else:
            # 从知识库搜索
            kb_results = await search_kb(default_kb_id, user_query, top_k=3)
            if "results" in kb_results and kb_results["results"]:
                all_contexts.extend(kb_results["results"])
                logger.debug(f"从知识库获取了 {len(kb_results['results'])} 条结果")
        
        # 如果没有获取到任何上下文
        if not all_contexts:
            logger.warning("未能获取到任何上下文信息")
            return {"prompt": request_body.get("prompt", ""), "rag_results": ""}
            
        # 修复此处的问题，确保能够安全地获取内容
        context_texts = []
        for hit in all_contexts:
            if isinstance(hit, dict):
                # 首先尝试获取text字段，这是标准化后的字段名
                text = hit.get("text", "")
                # 如果没有text，尝试content字段(兼容旧格式)
                if not text and "content" in hit:
                    text = hit["content"]
                # 如果还没有，尝试snippet(web搜索结果可能用这个字段)
                if not text and "snippet" in hit:
                    text = hit["snippet"]
                
                if text:
                    context_texts.append(text)
                else:
                    logger.warning(f"在上下文中找到没有有效内容的条目: {hit}")
        
        # 合并所有有效的上下文文本
        context_text = "\n\n".join(context_texts)
        
        # 创建增强的提示
        rag_prompt = f"""请根据以下参考信息回答用户的问题。如果参考信息不足以回答问题，请基于您自己的知识提供答案，但请优先使用参考信息。

参考信息:
{context_text}

用户问题: {user_query}"""

        # 更新请求体
        modified_request = request_body.copy()
        if messages:
            # 创建系统消息
            system_message = {"role": "system", "content": rag_prompt}
            
            # 查找是否已有系统消息
            has_system = False
            for i, msg in enumerate(messages):
                if msg.get("role") == "system":
                    messages[i]["content"] = rag_prompt
                    has_system = True
                    break
                    
            if not has_system:
                # 在消息列表开头添加系统消息
                messages.insert(0, system_message)
                
            # 更新请求体
            modified_request["messages"] = messages
        else:
            # 使用增强的提示替换原始提示
            modified_request["prompt"] = rag_prompt
            
        logger.info("已成功增强提示")
        return {"prompt": modified_request.get("prompt", ""), "rag_results": context_text}
        
    except Exception as e:
        logger.error(f"RAG处理失败: {str(e)}", exc_info=True)
        return {"prompt": request_body.get("prompt", ""), "rag_results": ""}  # 出现错误时返回原始请求
