from aiohttp import web
import aiohttp
import logging
import json, os
import asyncio
from datetime import datetime
from rag_service import process_rag
from web_search import process_web_search
from image_processor import extract_images_from_message, get_model_capabilities, describe_images, load_model_capabilities
from proxyrequest.request_handlers import handle_chat_request, handle_regular_request
from proxyrequest.response_formatter import create_ollama_response

logger = logging.getLogger(__name__)
TARGET_PORT = int(os.getenv('TARGET_PORT', 11434))
TARGET_URL = f"http://localhost:{TARGET_PORT}"

# 增加最大请求体大小限制，设置为100MB (默认只有1MB)
MAX_REQUEST_SIZE = int(os.getenv('MAX_REQUEST_SIZE', 104857600))  # 100MB in bytes

async def forward_request(request):
    request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    logger.info(f"=" * 80)
    logger.info(f"请求ID: {request_id}")
    logger.info(f"收到新请求:")
    logger.info(f"时间: {datetime.now()}")
    logger.info(f"客户端IP: {request.remote}")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求路径: {request.path}")
    logger.info(f"Content-Length: {request.headers.get('Content-Length', 'unknown')}")
    logger.info(f"请求头:")
    for header, value in request.headers.items():
        logger.info(f"  {header}: {value}")

    target_url = TARGET_URL
    
    # 检查请求路径并记录日志
    if request.path == "/api/chat" :
        actual_target = f"{target_url}/api/chat"
        logger.info(f"[{request_id}] 检测到聊天/生成请求，转发到: {actual_target}")
        
        try:
            # 读取请求体
            try:
                body = await request.read()
                content_length = len(body)
                logger.info(f"[{request_id}] 请求体大小: {content_length/1024/1024:.2f} MB")
            except web.HTTPRequestEntityTooLarge as e:
                logger.error(f"[{request_id}] 请求体过大: {str(e)}")
                return web.Response(
                    text=json.dumps({
                        "error": "请求体过大，超过服务器限制",
                        "details": f"请求体大小超过 {MAX_REQUEST_SIZE/1024/1024} MB 的限制，请尝试压缩图片或减少发送的数据量"
                    }),
                    status=413,
                    content_type='application/json'
                )
            
            # 处理聊天请求
            return await handle_chat_request(request_id, request, body, target_url)
            
        except Exception as e:
            logger.error(f"[{request_id}] 处理请求时出错: {str(e)}")
            logger.exception(e)  # 打印完整的异常堆栈
            return web.Response(
                text=json.dumps(create_ollama_response(error_message=str(e))),
                status=500,
                content_type='application/json'
            )
    else:
        # 对于其他所有请求，直接忠实转发
        return await handle_regular_request(request_id, request, target_url)

async def handle_options(request):
    """
    处理OPTIONS预检请求
    """
    return web.Response(
        headers={
            'Access-Control-Allow-Origin': 'http://localhost:3000',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Credentials': 'true',
        }
    )

async def create_app(port, target_url):
    """
    创建并配置应用服务器
    """
    # 启动时加载模型能力信息
    logger.info("正在加载模型能力信息...")
    await load_model_capabilities()
    logger.info("模型能力信息加载完成")
    
    app = web.Application(client_max_size=MAX_REQUEST_SIZE)
    app.router.add_route('OPTIONS', '/{path:.*}', handle_options)
    app.router.add_route('*', '/{path:.*}', forward_request)
    # 所有匹配的请求都会被转发给这个处理函数
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    return site
