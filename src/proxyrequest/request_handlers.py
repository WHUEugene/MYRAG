from aiohttp import web
import aiohttp
import json
import logging
import asyncio
from datetime import datetime
from rag_service import process_rag
from web_search import process_web_search
from image_processor import extract_images_from_message, get_model_capabilities, describe_images
from proxyrequest.response_formatter import create_ollama_response
from proxyrequest.context_enhancer import enhance_prompt_with_context
from proxyrequest.TaskManager import TaskManager

logger = logging.getLogger(__name__)

async def handle_chat_request(request_id, request, body, target_url):
    """处理聊天/生成请求"""
    try:
        body_json = json.loads(body)
        logger.info(f"[{request_id}] 原始请求体类型: {type(body_json)}")
        if isinstance(body_json, dict):
            logger.info(f"[{request_id}] 请求包含的字段: {list(body_json.keys())}")
        else:
            logger.info(f"[{request_id}] 请求体不是字典格式")
    except json.JSONDecodeError as e:
        logger.error(f"[{request_id}] JSON解析失败: {e}")
        logger.error(f"[{request_id}] 原始请求体(截断): {body[:200].decode('utf-8', errors='ignore')}...")
        return web.Response(text="无效的JSON格式", status=400)

    # 创建标准响应
    response = web.StreamResponse(
        status=200,
        headers={
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': 'http://localhost:3000',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Credentials': 'true',
        }
    )
    await response.prepare(request)

    # 修改进度消息发送函数，使用 Ollama 标准格式
    async def send_progress(msg):
        progress_data = create_ollama_response(
            model=body_json.get("model", "unknown"),
            response=f"<info> {msg}</info>\n",
            done=False
        )
        await response.write(json.dumps(progress_data).encode() + b'\n')
        await response.drain()

    # 确保options字段存在
    if "options" not in body_json:
        body_json["options"] = {}
        
    # 默认启用自动检测（除非明确禁用）
    body_json["options"]["auto_detect"] = body_json.get("options", {}).get("auto_detect", True)
    
    # 创建任务管理器
    task_manager = TaskManager(request_id, body_json, send_progress)
    
    # 执行增强处理
    enhanced_body = await task_manager.process_tasks()
    
    # 检查是否应该终止处理
    if task_manager.should_terminate:
        return response
    
    # 发送到 Ollama
    await send_progress("增强处理完成，正在生成回答...")
    logger.info(f"[{request_id}] 准备发送到Ollama的请求体:")
    
    # 在发送前移除所有消息中的images字段
    if 'messages' in enhanced_body:
        for msg in enhanced_body['messages']:
            if 'images' in msg:
                del msg['images']
    
    # 在日志中记录清理后的请求体
    logger.info(json.dumps(enhanced_body, indent=2, ensure_ascii=False))
    
    # 调用Ollama API - 使用chat接口
    return await call_ollama_api(request_id, response, f"{target_url}/api/chat", enhanced_body, send_progress)

async def handle_regular_request(request_id, request, target_url):
    """处理常规请求（非聊天/生成请求）"""
    actual_target = f"{target_url}{request.path}"
    logger.info(f"[{request_id}] 直接转发普通请求到: {actual_target}")
    
    try:
        # 直接转发请求到目标服务器
        async with aiohttp.ClientSession() as session:
            # 复制原始请求头
            headers = dict(request.headers)
            
            # 构建请求参数
            kwargs = {
                'headers': headers,
                'params': request.query,
                'allow_redirects': True,
            }
            
            # 如果有请求体，添加到请求参数中
            if request.content_length and request.content_length > 0:
                body = await request.read()
                if body:
                    kwargs['data'] = body
            
            # 根据原始请求方法发送请求
            target_response = await getattr(session, request.method.lower())(actual_target, **kwargs)
            
            # 构建响应
            response_headers = dict(target_response.headers)
            response = web.StreamResponse(status=target_response.status, headers=response_headers)
            await response.prepare(request)
            
            # 流式传输响应体
            async for chunk in target_response.content.iter_chunked(4096):
                await response.write(chunk)
            
            logger.info(f"[{request_id}] 完成普通请求转发")
            return response
            
    except Exception as e:
        logger.error(f"[{request_id}] 转发普通请求时出错: {str(e)}")
        logger.exception(e)
        return web.Response(
            text=str(e),
            status=500
        )

async def call_ollama_api(request_id, response, target_url, body_json, send_progress):
    """调用Ollama API并处理响应"""
    # 确保请求体是chat格式
    body_json = convert_to_chat_format(body_json)
    
    async with aiohttp.ClientSession() as session:
        try:
            start_time = datetime.now()
            logger.info(f"[{request_id}] 开始请求Ollama Chat API: {start_time}")
            
            ollama_response = await session.post(
                target_url,
                json=body_json,
                headers={'Content-Type': 'application/json'}
            )
            
            logger.info(f"[{request_id}] Ollama响应状态码: {ollama_response.status}")
            logger.info(f"[{request_id}] Ollama响应头:")
            for header, value in ollama_response.headers.items():
                logger.info(f"  {header}: {value}")
            
            if ollama_response.status != 200:
                error_text = await ollama_response.text()
                logger.error(f"[{request_id}] Ollama错误响应:")
                logger.error(f"状态码: {ollama_response.status}")
                logger.error(f"错误内容: {error_text}")
                # 使用 Ollama 格式发送错误
                error_data = create_ollama_response(
                    model=body_json.get("model", "unknown"),
                    response=f"[错误] {error_text}",
                    done=True
                )
                await response.write(json.dumps(error_data).encode() + b'\n')
                return response
            
            chunk_count = 0
            async for chunk in ollama_response.content:
                if chunk:
                    # 直接将 Ollama 的响应发送给客户端
                    await response.write(chunk + b'\n')
                    await response.drain()
                    chunk_count += 1
            
            end_time = datetime.now()
            process_time = (end_time - start_time).total_seconds()
            logger.info(f"[{request_id}] 完成Ollama请求, 处理时间: {process_time:.2f}秒")
            logger.info(f"[{request_id}] 总共处理 {chunk_count} 个数据块")
            
            # 在请求结束后输出转发的请求信息
            logger.info(f"[{request_id}] 转发请求信息摘要:")
            logger.info(f"[{request_id}] 目标URL: {target_url}")
            logger.info(f"[{request_id}] 请求模型: {body_json.get('model', '未指定')}")
            
            # 记录请求体的关键部分（避免日志过大）
            if 'messages' in body_json:
                message_count = len(body_json['messages'])
                logger.info(f"[{request_id}] 请求包含 {message_count} 条消息")
                if message_count > 0:
                    last_msg = body_json['messages'][-1]
                    content = last_msg.get('content', '')
                    if isinstance(content, str):
                        content_summary = content[:100] + '...' if len(content) > 100 else content
                        logger.info(f"[{request_id}] 最后一条消息内容: {content_summary}")
            
            # 记录其他重要参数
            for key in ['temperature', 'top_k', 'top_p', 'stream']:
                if key in body_json:
                    logger.info(f"[{request_id}] 参数 {key}: {body_json[key]}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"[{request_id}] 请求Ollama API时出错: {e}")
            error_data = create_ollama_response(
                model=body_json.get("model", "unknown"),
                response=f"[错误] {str(e)}",
                done=True
            )
            await response.write(json.dumps(error_data).encode() + b'\n')
            return response
        
    # 最后一条消息也使用 Ollama 格式
    final_data = create_ollama_response(
        model=body_json.get("model", "unknown"),
        response="[系统] 处理完成",
        done=True
    )
    await response.write(json.dumps(final_data).encode() + b'\n')
    await response.drain()
    
    logger.info(f"[{request_id}] 请求处理完成")
    logger.info("=" * 80)
    return response

def convert_to_chat_format(body_json):
    """将任何格式的请求转换为 chat 格式"""
    new_body = body_json.copy()
    
    # 如果已经有 messages 字段且格式正确，则不需要转换
    if "messages" in new_body and isinstance(new_body["messages"], list):
        # 检查是否包含有效消息
        if not new_body["messages"]:
            # 空消息列表，添加默认用户消息
            new_body["messages"] = [{"role": "user", "content": ""}]
        return new_body
        
    # 如果有 prompt 字段，将其转换为 messages 格式
    if "prompt" in new_body:
        prompt = new_body.pop("prompt")
        messages = []
        
        # 根据 prompt 类型处理
        if isinstance(prompt, str):
            # 文本类型，创建用户消息
            messages.append({
                "role": "user",
                "content": prompt
            })
        elif isinstance(prompt, list):
            # 多模态prompt（包含文本和图像）
            content = ""
            images = []
            
            for item in prompt:
                if item.get("type") == "text":
                    content += item.get("text", "")
                elif item.get("type") == "image":
                    # 收集图像数据
                    images.append(item.get("data", ""))
            
            # 创建用户消息
            user_message = {
                "role": "user",
                "content": content
            }
            
            # 如果有图像，添加到消息中
            if images:
                user_message["images"] = images
                
            messages.append(user_message)
        
        # 更新请求体
        new_body["messages"] = messages
    else:
        # 如果既没有 messages 也没有 prompt，创建一个空的默认消息
        new_body["messages"] = [{"role": "user", "content": ""}]
    
    # 删除不必要的字段
    if "prompt" in new_body:
        del new_body["prompt"]
    
    return new_body



