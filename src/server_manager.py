import sys
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
sys.path.append(current_dir)  # 添加 src 目录到路径

import asyncio
import multiprocessing
import logging
import subprocess
# 确保导入正确
from document_server import app as doc_app
from proxy_server import create_app

# 在每个进程中单独配置日志
def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler()  # 使用默认的流处理器
        ]
    )
    return logging.getLogger(__name__)

# 服务器配置
PROXY_PORT = int(os.getenv('PROXY_PORT', 11435))
TARGET_PORT = int(os.getenv('TARGET_PORT', 11434))
TARGET_URL = f"http://localhost:{TARGET_PORT}"
DOC_SERVER_PORT = int(os.getenv('DOC_SERVER_PORT', 5001))

def run_doc_server():
    """运行文档服务器"""
    logger = configure_logging()
    logger.info(f"启动文档服务器在端口 {DOC_SERVER_PORT}")
    # 设置环境变量传递端口
    os.environ['DOC_SERVER_PORT'] = str(DOC_SERVER_PORT)
    doc_app.run(port=DOC_SERVER_PORT, debug=True, host='0.0.0.0', use_reloader=False)

def run_celery_worker():
    """运行 Celery Worker"""
    logger = configure_logging()
    logger.info("启动 Celery Worker")
    # 获取 celery_worker.py 的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    worker_path = os.path.join(current_dir, 'celery_worker.py')
    logger.info(f"Celery worker 路径: {worker_path}")
    
    # 在当前目录下执行 celery worker
    subprocess.run(['python', worker_path], cwd=current_dir)

async def run_proxy_server():
    """运行代理服务器"""
    logger = configure_logging()
    MAX_REQUEST_SIZE=os.getenv('MAX_REQUEST_SIZE', 1024*1024*100) # 10MB
    # app = await create_app(PROXY_PORT, TARGET_URL,client_max_size=MAX_REQUEST_SIZE)
    app = await create_app(PROXY_PORT, TARGET_URL)
    logger.info(f"启动代理服务器在端口 {PROXY_PORT}")
    await app.start()
    await asyncio.Event().wait()

async def main():
    """主函数：启动所有服务"""
    logger = configure_logging()
    logger.info("=" * 50)
    logger.info("启动RAG服务系统")
    logger.info("=" * 50)
    
    # 使用多进程启动文档服务器
    doc_server_process = multiprocessing.Process(target=run_doc_server)
    doc_server_process.start()
    
    # 启动 Celery Worker
    celery_process = multiprocessing.Process(target=run_celery_worker)
    celery_process.start()
    
    # 启动代理服务器
    await run_proxy_server()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        configure_logging().info("正在关闭服务...")
    except Exception as e:
        configure_logging().error(f"服务发生错误: {e}")
    finally:
        configure_logging().info("服务已停止")
