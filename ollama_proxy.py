import asyncio
from aiohttp import web
import aiohttp
import logging
import json
from datetime import datetime

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 服务器配置
SOURCE_PORT = 11435  # 源端口：接收前端发来的请求
TARGET_PORT = 11434  # 目标端口：转发给实际的Ollama服务器
TARGET_URL = f"http://localhost:{TARGET_PORT}"

async def forward_request(request):
    """
    请求转发处理函数 - 支持流式响应
    """
    """
    async def 是 Python 的异步函数定义语法，用于定义协程(coroutine)。
    它允许函数在等待 I/O 操作时释放控制权，提高程序的并发性能。
    """
    start_time = datetime.now()
    client_ip = request.remote
    
    # 打印请求详情
    logger.info("=" * 50)
    logger.info(f"收到新请求:")
    logger.info(f"时间: {start_time}")
    logger.info(f"客户端IP: {client_ip}")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求路径: {request.path}")
    
    try:
        body = await request.read()
        headers = {k: v for k, v in request.headers.items()}
        
        # 输出请求头和请求体
        logger.info("请求头:")
        for header, value in headers.items():
            logger.info(f"  {header}: {value}")
            
        if body:
            try:
                body_json = json.loads(body)
                logger.info("请求体:")
                logger.info(json.dumps(body_json, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                logger.info(f"请求体: {body.decode('utf-8', errors='ignore')}")
        
        logger.info(f"转发请求到: {TARGET_URL}{request.path}")
        # ------------------打印请求的详细信息------------------------------------------------------------------------
        # 创建流式响应
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'application/json',  # 修改为application/json
                'Access-Control-Allow-Origin': 'http://localhost:3000',  # 允许前端域
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Credentials': 'true',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )
        await response.prepare(request)
        # 创建了一个 StreamResponse 对象，这是 aiohttp 框架提供的流式响应机制
        # 设置响应状态码为 200
        # 配置必要的 HTTP 头，包括 CORS 策略和缓存控制
        # prepare() 方法初始化了流式响应，建立持久连接
        
        # 转发请求并处理流式响应
        # 1. 创建HTTP客户端会话
        async with aiohttp.ClientSession() as session:
            # 2. 发送请求到Ollama服务器
            async with session.request(
                method=request.method,
                url=f"{TARGET_URL}{request.path}",
                headers=headers,
                data=body
            ) as ollama_response:
                # 检查响应状态
                # 3. 错误处理
                if ollama_response.status != 200:
                    error_body = await ollama_response.read()
                    logger.error(f"Ollama error: {error_body}")
                    return web.Response(
                        body=error_body,
                        status=ollama_response.status
                    )
                # 4. 处理流式响应
                # 逐行转发流式响应
                async for chunk in ollama_response.content:
                    if chunk:
                        try:# 如果数据块不为空
                            # 5. 解码并记录数据
                            # 记录接收到的数据
                            chunk_str = chunk.decode('utf-8')
                            logger.info(f"转发数据: {chunk_str.strip()}")
                            # 6. 转发数据到客户端
                            # 发送数据到客户端 (移除drain调用)
                            await response.write(chunk + b'\n')  # 添加换行符确保正确分割
                            
                        except Exception as e:
                            logger.error(f"处理数据块时出错: {e}")
                # 7. 记录处理时间
                end_time = datetime.now()
                process_time = (end_time - start_time).total_seconds()
                logger.info("-" * 50)
                logger.info(f"完成流式传输，总处理时间: {process_time:.3f}秒")
                logger.info("=" * 50)
                # 8. 返回响应对象
                return response
                
    except aiohttp.ClientError as e:
        logger.error(f"网络错误: {e}")
        return web.Response(text=f"代理错误: {e}", status=502)
    except Exception as e:
        logger.error(f"未知错误: {e}")
        return web.Response(text=f"内部错误: {e}", status=500)

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

async def main():
    """
    主函数：启动代理服务器
    """
    app = web.Application()
    # 添加OPTIONS请求处理
    app.router.add_route('OPTIONS', '/{path:.*}', handle_options)
    app.router.add_route('*', '/{path:.*}', forward_request)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', SOURCE_PORT)
    
    logger.info("*" * 50)
    logger.info(f"Ollama代理服务器启动")
    logger.info(f"监听端口: {SOURCE_PORT}")
    logger.info(f"转发地址: {TARGET_URL}")
    logger.info("*" * 50)
    
    await site.start()
    await asyncio.Event().wait()  # 保持服务器运行

if __name__ == "__main__":
    asyncio.run(main())
