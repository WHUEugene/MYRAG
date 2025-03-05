import os
import base64
import json
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Callable, Optional
import logging
import io
import ssl
from dotenv import load_dotenv
import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3
# 加载.env文件中的环境变量
load_dotenv()

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("未安装Pillow库，图片压缩功能将不可用")

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 从环境变量获取OpenAI API密钥和URL
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = os.environ.get("OPENAI_API_URL", "https://api.chatfire.cn/v1/chat/completions")
MODEL_CAPABILITIES_FILE = os.environ.get("MODEL_CAPABILITIES_FILE", "/Users/linyong/vscode/MyRag/config/model_capabilities.json")
TARGET_PORT= os.environ.get("TARGET_PORT")
# siliconflow_API_KEY="sk-xb1abg0YFLZOMeJF66544b95C9314b6d90B64276A46a4028"
# 确保环境变量正确加载
logger.info(f"加载的API URL: {OPENAI_API_URL}")
logger.info(f"API KEY是否设置: {'已设置' if OPENAI_API_KEY else '未设置'}")

# 全局模型能力缓存
MODEL_CAPABILITIES_CACHE = {}

# 默认已知的支持图像的模型
DEFAULT_VISION_MODELS = {
    "llava": True,
    "llama-vision": True, 
    "bakllava": True, 
    "moondream": True, 
    "cogvlm": True, 
    "llava-llama": True, 
    "llava-13b": True, 
    "llava-v1.5": True, 
    "llava-v1.6": True
}

async def load_model_capabilities():
    """
    加载模型能力配置文件，并尝试从Ollama获取所有模型信息
    """
    global MODEL_CAPABILITIES_CACHE
    
    # 1. 加载配置文件中的模型能力信息
    try:
        os.makedirs(os.path.dirname(MODEL_CAPABILITIES_FILE), exist_ok=True)
        if os.path.exists(MODEL_CAPABILITIES_FILE):
            with open(MODEL_CAPABILITIES_FILE, 'r') as f:
                MODEL_CAPABILITIES_CACHE = json.load(f)
            logger.info(f"从文件加载了 {len(MODEL_CAPABILITIES_CACHE)} 个模型的能力信息")
        else:
            # 创建默认配置文件
            MODEL_CAPABILITIES_CACHE = {}
            for model_name, has_vision in DEFAULT_VISION_MODELS.items():
                MODEL_CAPABILITIES_CACHE[model_name] = {"vision": has_vision}
            with open(MODEL_CAPABILITIES_FILE, 'w') as f:
                json.dump(MODEL_CAPABILITIES_CACHE, f, indent=2)
            logger.info(f"创建了默认模型能力配置文件: {MODEL_CAPABILITIES_FILE}")
    except Exception as e:
        logger.error(f"加载模型能力配置文件出错: {str(e)}")
        # 如果加载失败，使用默认值
        MODEL_CAPABILITIES_CACHE = {}
        for model_name, has_vision in DEFAULT_VISION_MODELS.items():
            MODEL_CAPABILITIES_CACHE[model_name] = {"vision": has_vision}
    
    # 2. 从Ollama获取所有模型并检查其能力
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{TARGET_PORT}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    
                    if models:
                        logger.info(f"从Ollama获取了 {len(models)} 个模型信息")
                        
                        # 为每个模型检查能力
                        for model in models:
                            model_name = model.get("name", "")
                            if model_name and model_name not in MODEL_CAPABILITIES_CACHE:
                                capabilities = await detect_model_capabilities(model_name)
                                MODEL_CAPABILITIES_CACHE[model_name] = capabilities
                                logger.info(f"检测到模型 {model_name} 的能力: {capabilities}")
                        
                        # 保存更新后的模型能力信息
                        try:
                            with open(MODEL_CAPABILITIES_FILE, 'w') as f:
                                json.dump(MODEL_CAPABILITIES_CACHE, f, indent=2)
                            logger.info(f"已更新模型能力配置文件")
                        except Exception as e:
                            logger.error(f"保存模型能力配置出错: {str(e)}")
    except Exception as e:
        logger.error(f"获取Ollama模型列表出错: {str(e)}")
    
    logger.info(f"最终模型能力缓存中包含 {len(MODEL_CAPABILITIES_CACHE)} 个模型")

async def detect_model_capabilities(model_name: str) -> Dict[str, bool]:
    """
    检测特定模型的能力，特别是是否支持图像处理
    
    参数:
        model_name: 模型名称
        
    返回:
        Dict[str, bool]: 包含模型能力的字典，例如{"vision": True}
    """
    # 检查模型名称是否包含已知视觉模型的关键字
    is_vision_model = any(vision_name in model_name.lower() for vision_name in DEFAULT_VISION_MODELS)
    
    # 尝试从Ollama获取更准确的模型信息
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://localhost:{TARGET_PORT}/api/show", 
                json={"name": model_name}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    model_details = data.get("details", {})
                    
                    # 检查模型信息中的关键字
                    model_info = str(model_details).lower()
                    if any(keyword in model_info for keyword in ["vision", "visual", "multimodal", "image"]):
                        return {"vision": True}
                    
                    # 检查模型描述
                    model_template = data.get("template", "").lower()
                    if any(keyword in model_template for keyword in ["vision", "visual", "multimodal", "image"]):
                        return {"vision": True}
    except Exception as e:
        logger.warning(f"无法从Ollama获取{model_name}的模型详情: {str(e)}")
    
    # 如果没有明确的证据表明支持图像，则基于名称判断
    return {"vision": is_vision_model}

async def get_model_capabilities(model_name: str) -> Dict[str, bool]:
    """
    查询特定模型的能力，优先从缓存获取，未找到则实时检测
    
    参数:
        model_name: 模型名称
        
    返回:
        Dict[str, bool]: 包含模型能力的字典，例如{"vision": True}
    """
    # 检查模型名称规范化 (去除版本号等)
    base_model_name = model_name.split(':')[0].lower()
    
    # 首先查找精确匹配
    if model_name in MODEL_CAPABILITIES_CACHE:
        return MODEL_CAPABILITIES_CACHE[model_name]
    
    # 其次查找基础模型名称匹配
    if base_model_name in MODEL_CAPABILITIES_CACHE:
        return MODEL_CAPABILITIES_CACHE[base_model_name]
    
    # 再查找部分匹配
    for cached_model_name, capabilities in MODEL_CAPABILITIES_CACHE.items():
        if cached_model_name in model_name or model_name in cached_model_name:
            return capabilities
    
    # 如果缓存中没有，实时检测并更新缓存
    capabilities = await detect_model_capabilities(model_name)
    MODEL_CAPABILITIES_CACHE[model_name] = capabilities
    
    # 尝试保存更新后的缓存
    try:
        with open(MODEL_CAPABILITIES_FILE, 'w') as f:
            json.dump(MODEL_CAPABILITIES_CACHE, f, indent=2)
    except Exception as e:
        logger.warning(f"保存更新的模型能力信息失败: {str(e)}")
    
    return capabilities

async def describe_images(
    images: List[Dict[str, str]],
    progress_callback: Optional[Callable] = None
) -> str:
    """
    使用qwen2.5vl72b描述图片内容
    
    参数:
        images: 图片信息列表，每个元素包含base64编码图片
        progress_callback: 可选的回调函数，用于发送处理进度
        
    返回:
        str: 所有图片描述的组合结果
    """
    
    if not images:
        return ""
        
    all_descriptions = []
    
    try:
        for i, img_data in enumerate(images):
            if progress_callback:
                await progress_callback(f"正在分析第{i+1}张图片...")
            
            # 确保mime_type格式正确
            mime_type = img_data.get('mime_type', 'image/jpeg')
            if not mime_type.startswith('image/'):
                mime_type = 'image/' + mime_type.replace('image/', '')
            
            # 确保base64数据不包含换行符或额外空格
            base64_data = img_data['data'].strip()
            
            # 验证base64数据格式
            if not is_valid_base64(base64_data):
                logger.error(f"图片{i+1}的base64数据格式无效")
                all_descriptions.append(f"[图片{i+1}处理失败: base64格式无效]")
                continue
            
            # 构建请求消息
            messages = [
                {
                    "role": "system", 
                    "content": "你是一个图像描述专家。请详细描述这张图片的内容，包括图片中的主要对象、场景、文本、布局等关键信息。描述要清晰全面，重点突出，使人能通过你的描述了解图片的完整信息。使用中文回复。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请描述这张图片："
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_data}"
                            }
                        }
                    ]
                }
            ]
            
            # API请求配置
            payload = {
                "model": "gpt-4o",
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.95,
                "request_id": f"img_desc_{i}",
                "stream": False
            }

            # 发送请求到硅基流动API
            try:
                urllib3.disable_warnings(InsecureRequestWarning)
                
                response = requests.post(
                    f"{OPENAI_API_URL}",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {OPENAI_API_KEY}"
                    },
                    timeout=60,
                    verify=False
                )
                
                logger.info(f"收到响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    description = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    if description:
                        all_descriptions.append(f"[图片{i+1}]\n{description}")
                    else:
                        logger.warning("API返回成功但未找到描述内容")
                        all_descriptions.append(f"[图片{i+1}描述为空]")
                else:
                    error_msg = f"API请求失败: 状态码={response.status_code}, 响应={response.text}"
                    logger.error(error_msg)
                    all_descriptions.append(f"[图片{i+1}处理失败: {error_msg}]")
                    
            except Exception as e:
                error_msg = f"请求处理失败: {str(e)}"
                logger.error(error_msg)
                all_descriptions.append(f"[图片{i+1}处理失败: {error_msg}]")
                
        return "\n\n".join(all_descriptions)
        
    except Exception as e:
        logger.error(f"处理图片时出错: {str(e)}", exc_info=True)
        if progress_callback:
            await progress_callback(f"图片处理错误: {str(e)}")
        return f"[图片处理错误] {str(e)}"

def is_valid_base64(s):
    """
    检查字符串是否是有效的base64编码
    
    参数:
        s: 要检查的字符串
        
    返回:
        bool: 是否为有效的base64编码
    """
    # 移除所有可能的空白字符
    s = s.strip()
    
    # 检查长度是否是4的倍数(可能有等号填充)
    if len(s) % 4 != 0 and not s.endswith('='):
        return False
    
    # 检查是否只包含base64允许的字符
    allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    return all(c in allowed_chars for c in s)

async def extract_images_from_message(message: Dict[str, Any], compress=True) -> List[Dict[str, str]]:
    """
    从请求体或Ollama消息格式中提取图片数据

    参数:
        message: 请求体或Ollama消息，可能是整个body
        compress: 是否压缩图片

    返回:
        List[Dict[str, str]]: 提取的图片列表
    """
    images = []
    message_images = []

    if isinstance(message, dict):
        if "messages" in message:
            for msg in message.get("messages", []):
                if isinstance(msg, dict) and "images" in msg:
                    logger.info("在messages数组中找到images字段")
                    if isinstance(msg["images"], list):
                        message_images.extend(msg["images"])
                    else:
                        logger.warning("messages数组中的images字段不是列表")
        else:
            logger.warning("消息格式不正确, 未找到messages数组")
            return []
    else:
        logger.warning(f"消息格式不正确: {type(message)}")
        return []

    if message_images:
        logger.info(f"发现images字段，包含 {len(message_images)} 个图片")
        for index, image_data in enumerate(message_images):
            if isinstance(image_data, str):
                logger.info(f"处理第 {index + 1} 张图片")
                
                # 清理和验证base64数据
                cleaned_data = clean_base64_data(image_data)
                
                if not cleaned_data:
                    logger.warning(f"图片 {index + 1} 的base64数据无效，跳过")
                    continue
                
                images.append({
                    "data": cleaned_data,
                    "mime_type": "image/jpeg"  # 默认MIME类型
                })
                logger.info(f"成功添加图片 {len(images)}")
            else:
                logger.warning(f"图片 {index + 1} 的数据不是字符串类型，跳过")
    
    logger.info(f"从消息中提取了 {len(images)} 张图片")
    return images

def clean_base64_data(data):
    """
    清理base64数据，移除可能导致解码错误的字符
    
    参数:
        data: 原始base64数据
        
    返回:
        str: 清理后的base64数据
    """
    if not data:
        logger.warning("输入的base64数据为空")
        return ""
    
    # 检查数据是否已经是干净的base64格式
    if is_valid_base64(data):
        logger.info("输入数据已经是有效的base64格式")
        # 确保长度是4的倍数
        padding_needed = len(data) % 4
        if padding_needed:
            data += '=' * padding_needed
        return data
    
    # 记录清理步骤
    logger.info(f"开始清理base64数据 - 原始长度: {len(data)}")
    
    # 移除所有空白字符
    cleaned = ''.join(data.split())
    logger.info(f"移除空白字符后长度: {len(cleaned)}")
    
    # 移除data:image前缀(如果存在)
    if "base64," in cleaned:
        cleaned = cleaned.split("base64,")[1]
        logger.info(f"移除base64前缀后长度: {len(cleaned)}")
    
    # 确保长度是4的倍数，通过填充=
    padding_needed = len(cleaned) % 4
    if padding_needed:
        cleaned += '=' * (4 - padding_needed)
        logger.info(f"添加填充后长度: {len(cleaned)}")
    
    # 检查是否只包含有效的base64字符
    allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    invalid_chars = set(c for c in cleaned if c not in allowed_chars)
    
    if invalid_chars:
        logger.error(f"数据包含无效字符: {invalid_chars}")
        # 尝试移除无效字符
        cleaned = ''.join(c for c in cleaned if c in allowed_chars)
        logger.info(f"移除无效字符后长度: {len(cleaned)}")
        
        # 重新检查长度
        padding_needed = len(cleaned) % 4
        if padding_needed:
            cleaned += '=' * (4 - padding_needed)
    
    # 验证最终结果
    if not is_valid_base64(cleaned):
        logger.error("清理后数据仍然不是有效的base64编码")
        # 尝试验证数据有效性
        try:
            decoded = base64.b64decode(cleaned)
            # 如果能成功解码，说明数据有效
            logger.info(f"数据可以解码，解码后长度: {len(decoded)}")
            return cleaned
        except Exception as e:
            logger.error(f"base64解码失败: {e}")
            return ""
    else:
        logger.info("清理后的数据是有效的base64格式")
        return cleaned

# 添加一个更强大的验证函数，尝试实际解码
def is_valid_base64(s):
    """
    检查字符串是否是有效的base64编码
    
    参数:
        s: 要检查的字符串
        
    返回:
        bool: 是否为有效的base64编码
    """
    if not s:
        return False
    
    # 移除所有可能的空白字符
    s = s.strip()
    
    # 检查长度是否是4的倍数(可能有等号填充)
    if len(s) % 4 != 0:
        # 如果不是4的倍数且末尾没有=，可能需要填充
        if not s.endswith('='):
            padding_needed = 4 - (len(s) % 4)
            if padding_needed < 4:
                s += '=' * padding_needed
        else:
            # 如果已有=但长度仍不对，可能有问题
            return False
    
    # 检查是否只包含base64允许的字符
    allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    if not all(c in allowed_chars for c in s):
        return False
    
    # 最终验证：尝试解码
    try:
        base64.b64decode(s)
        return True
    except Exception:
        return False

# DNS预解析功能
def preload_dns():
    """
    预先解析常用API域名，减少首次请求的DNS解析延迟
    """
    import socket
    import threading
    
    def resolve_domain(domain):
        try:
            logger.info(f"正在预解析域名: {domain}")
            # 执行DNS解析
            socket.gethostbyname(domain)
            logger.info(f"域名 {domain} 解析完成")
        except Exception as e:
            logger.warning(f"解析域名 {domain} 失败: {e}")
    
    # 需要预解析的域名列表
    domains_to_resolve = []
    
    # 解析API URL的域名
    if OPENAI_API_URL:
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(OPENAI_API_URL)
            if parsed_url.netloc:
                domains_to_resolve.append(parsed_url.netloc)
        except Exception as e:
            logger.warning(f"解析API URL失败: {e}")
    
    # 添加其他可能用到的API域名
    common_api_domains = [
        "api.openai.com",
        "api.chatfire.cn",
        "api.chatfire.cc",
        "api.anthropic.com",
        "api.stability.ai"
    ]
    domains_to_resolve.extend(common_api_domains)
    
    # 创建线程列表
    threads = []
    
    # 使用线程并行解析域名
    for domain in set(domains_to_resolve):  # 使用set去重
        thread = threading.Thread(target=resolve_domain, args=(domain,))
        thread.daemon = True  # 设置为守护线程，不阻塞程序退出
        threads.append(thread)
        thread.start()
    
    # 设置超时时间（秒）
    timeout = 5
    
    # 等待所有线程完成，但最多等待timeout秒
    for thread in threads:
        thread.join(timeout / len(threads))
    
    logger.info("DNS预解析完成")

# 执行DNS预解析
try:
    preload_dns()
except Exception as e:
    logger.warning(f"DNS预解析过程中出现错误: {e}")
