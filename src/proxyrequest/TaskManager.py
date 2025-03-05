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
from proxyrequest.query_analyzer import QueryAnalyzer

logger = logging.getLogger(__name__)

class TaskManager:
    """任务管理器，处理图像处理、RAG和Web搜索任务"""
    
    def __init__(self, request_id, body_json, send_progress):
        self.request_id = request_id
        self.body_json = body_json
        self.send_progress = send_progress
        self.tasks_status = {
            "image_processing": {"started": False, "complete": False, "result": None},
            "rag": {"started": False, "complete": False, "result": None},
            "web_search": {"started": False, "complete": False, "result": None}
        }
        self.should_terminate = False
        self.context_lock = asyncio.Lock()
        self.enhanced_context = []
        self.query_analyzer = QueryAnalyzer()
        
        # 自动检测标志
        self.auto_detect_enabled = body_json.get("options", {}).get("auto_detect", True)
    
    async def on_task_complete(self, task_name, result):
        """任务完成时的回调函数"""
        async with self.context_lock:
            self.tasks_status[task_name]["complete"] = True
            self.tasks_status[task_name]["result"] = result
            logger.info(f"[{self.request_id}] {task_name} 任务完成")
    
    async def process_image_task(self):
        """图像处理任务"""
        # 标记任务已开始
        self.tasks_status["image_processing"]["started"] = True
        
        # 检测请求中是否包含图片
        model_name = self.body_json.get("model", "")
        images = await extract_images_from_message(self.body_json)
        
        if not images:
            await self.on_task_complete("image_processing", None)
            return None
            
        logger.info(f"[{self.request_id}] 检测到 {len(images)} 张图片")
        await self.send_progress(f"检测到 {len(images)} 张图片，处理中...")
        
        # 判断模型是否支持图像处理
        model_capabilities = await get_model_capabilities(model_name)
        
        if not model_capabilities.get("vision", False):
            # 如果模型不支持图像，则使用GPT-4V处理图片
            await self.send_progress(f"模型 {model_name} 不支持图像处理，使用GPT-4V分析图片中...")
            
            # 处理图片描述
            image_descriptions = await describe_images(images, self.send_progress)
            if image_descriptions:
                if image_descriptions.startswith("[图片处理错误]"):
                    # 如果图片处理出错，直接返回错误信息并停止处理
                    error_msg = image_descriptions
                    logger.error(f"[{self.request_id}] {error_msg}")
                    # 向客户端发送错误消息
                    error_data = create_ollama_response(
                        model=model_name,
                        response=error_msg,
                        done=True
                    )
                    await self.send_progress(error_msg)
                    self.should_terminate = True
                    return {"error": error_msg, "should_terminate": True}
                
                result = {
                    "image_descriptions": image_descriptions,
                    "context": f"图片内容分析:\n{image_descriptions}"
                }
                await self.on_task_complete("image_processing", result)
                await self.send_progress("图片分析完成")
                return result
        else:
            await self.send_progress(f"模型 {model_name} 支持图片处理，将直接处理图片")
            # 模型支持图像，需要确保请求格式正确
            
            # 如果是新消息格式，需要转换为 Ollama 支持的格式
            if "messages" in self.body_json and isinstance(self.body_json["messages"], list):
                logger.info(f"[{self.request_id}] 转换新消息格式为 Ollama 格式")
                self._convert_messages_format()
        
        # 没有图片或处理完成
        await self.on_task_complete("image_processing", None)
        return None
    
    def _convert_messages_format(self):
        """将新消息格式转换为 Ollama 支持的格式"""
        # 提取最后一条消息的内容和图片
        last_message = None
        for msg in reversed(self.body_json["messages"]):
            if msg.get("role") == "user":
                last_message = msg
                break
        
        if last_message:
            # 构建 Ollama 格式的 prompt
            prompt_items = []
            
            # 添加文本内容
            if "content" in last_message:
                prompt_items.append({
                    "type": "text",
                    "text": last_message["content"]
                })
            
            # 添加图片
            if "images" in last_message and isinstance(last_message["images"], list):
                for img in last_message["images"]:
                    prompt_items.append({
                        "type": "image",
                        "data": img,
                        "mime_type": "image/jpeg"  # 默认MIME类型
                    })
            
            # 更新请求体
            self.body_json["prompt"] = prompt_items
            
            # 删除原始messages字段
            if "messages" in self.body_json:
                del self.body_json["messages"]
    
    async def process_rag_task(self):
        """RAG处理任务"""
        # 标记任务已开始
        self.tasks_status["rag"]["started"] = True
        
        # 只有在选项中启用了RAG才执行
        if not self.body_json.get("options", {}).get("rag_enabled", False):
            logger.info(f"[{self.request_id}] RAG未启用，跳过处理")
            await self.on_task_complete("rag", None)
            return None
            
        await self.send_progress("正在从知识库检索相关内容...")
        
        try:
            rag_result = await process_rag(self.body_json)
            
            # 如果有检索结果则显示
            if rag_result.get("rag_results"):
                await self.send_progress("知识库检索完成，找到相关内容")
            else:
                await self.send_progress("知识库检索完成，未找到相关内容")
                
            # 更新任务状态
            await self.on_task_complete("rag", rag_result)
            return rag_result
        except Exception as e:
            logger.error(f"[{self.request_id}] RAG处理出错: {str(e)}")
            await self.send_progress(f"知识库检索出错: {str(e)}")
            await self.on_task_complete("rag", None)
            return None
    
    async def process_web_search_task(self):
        """Web搜索任务"""
        # 标记任务已开始
        self.tasks_status["web_search"]["started"] = True
        
        # 只有在选项中启用了Web搜索才执行
        if not self.body_json.get("options", {}).get("web_search_enabled", False):
            logger.info(f"[{self.request_id}] Web搜索未启用，跳过处理")
            await self.on_task_complete("web_search", None)
            return None
            
        await self.send_progress("正在进行网络搜索...")
        
        try:
            web_result = await process_web_search(self.body_json, self.send_progress)
            
            if web_result.get("search_results"):
                context = f"网络搜索结果:\n{web_result['search_results']}"
                web_result["context"] = context
                await self.on_task_complete("web_search", web_result)
                return web_result
            else:
                await self.send_progress("网络搜索完成，未找到相关内容")
                await self.on_task_complete("web_search", {"search_results": "", "context": ""})
                return {"search_results": "", "context": ""}
        except Exception as e:
            logger.error(f"[{self.request_id}] Web搜索出错: {str(e)}")
            await self.send_progress(f"网络搜索出错: {str(e)}")
            await self.on_task_complete("web_search", None)
            return None
    
    async def process_tasks(self):
        """处理所有任务并返回增强后的请求体"""
        # 获取用户选项和自动检测选项
        user_options = self.body_json.get("options", {})
        
        # 如果启用了自动检测，分析查询并更新选项
        if self.auto_detect_enabled:
            auto_options = self.query_analyzer.extract_options_from_message(self.body_json)
            
            # 日志记录自动检测结果
            if auto_options:
                logger.info(f"[{self.request_id}] 自动检测功能结果:")
                for feature, enabled in auto_options.items():
                    logger.info(f"  - {feature}: {enabled}")
            
            # 更新选项，但不覆盖用户明确设置的选项
            for key, value in auto_options.items():
                if key not in user_options:
                    user_options[key] = value
                    logger.info(f"[{self.request_id}] 自动启用功能: {key}")
        
        # 创建任务列表
        tasks = [
            asyncio.create_task(self.process_image_task())
        ]
        
        # 根据更新后的选项启用RAG任务
        if user_options.get("rag_enabled", False):
            logger.info(f"[{self.request_id}] 启用知识库检索功能")
            tasks.append(asyncio.create_task(self.process_rag_task()))
        
        # 根据更新后的选项启用Web搜索任务
        if user_options.get("web_search_enabled", False):
            logger.info(f"[{self.request_id}] 启用网络搜索功能")
            tasks.append(asyncio.create_task(self.process_web_search_task()))
        
        # 等待所有任务完成或超时
        start_time = datetime.now()
        try:
            # 最多等待60秒
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=60)
            
            # 检查任务结果，看是否有需要终止的情况
            for result in results:
                if isinstance(result, dict) and result.get("should_terminate", False):
                    logger.warning(f"[{self.request_id}] 检测到任务要求终止流程")
                    self.should_terminate = True
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"[{self.request_id}] 部分任务超时，将继续处理已完成的任务")
            await self.send_progress("部分增强功能处理超时，将使用已完成的结果继续")
        
        # 计算总处理时间
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"[{self.request_id}] 增强处理完成，耗时: {process_time:.2f} 秒")
        
        # 构建增强后的请求体
        enhanced_body = self.body_json.copy()
        
        # 获取用户查询
        user_query = self._extract_user_query()
        
        # 根据任务结果构建增强上下文
        if self.tasks_status["image_processing"]["complete"] and self.tasks_status["image_processing"]["result"]:
            img_result = self.tasks_status["image_processing"]["result"]
            if img_result.get("context"):
                self.enhanced_context.append(img_result["context"])
        
        if self.tasks_status["rag"]["complete"] and self.tasks_status["rag"]["result"]:
            rag_result = self.tasks_status["rag"]["result"]
            # 如果是旧格式（带prompt），转换为messages格式
            if "prompt" in rag_result:
                enhanced_message = {
                    "role": "user",
                    "content": rag_result["prompt"]
                }
                # 确保messages字段存在
                if "messages" not in enhanced_body:
                    enhanced_body["messages"] = []
                
                # 更新或添加用户消息
                if enhanced_body["messages"]:
                    # 找到最后一条用户消息并更新
                    for i in reversed(range(len(enhanced_body["messages"]))):
                        if enhanced_body["messages"][i]["role"] == "user":
                            enhanced_body["messages"][i] = enhanced_message
                            break
                    else:
                        # 如果没找到用户消息，添加一条
                        enhanced_body["messages"].append(enhanced_message)
                else:
                    enhanced_body["messages"] = [enhanced_message]
        
        if self.tasks_status["web_search"]["complete"] and self.tasks_status["web_search"]["result"]:
            web_result = self.tasks_status["web_search"]["result"]
            if web_result.get("context"):
                self.enhanced_context.append(web_result["context"])
                
                # 为用户显示网络搜索是自动触发的
                if self.auto_detect_enabled and user_options.get("web_search_enabled", False):
                    await self.send_progress("检测到您的问题可能需要最新信息，已自动为您搜索相关内容")
        
        # 如果有增强上下文，构建最终消息
        if self.enhanced_context and user_query:
            enhanced_content = enhance_prompt_with_context(user_query, self.enhanced_context)
            
            # 更新messages中的用户消息
            if "messages" in enhanced_body:
                for i in reversed(range(len(enhanced_body["messages"]))):
                    if enhanced_body["messages"][i]["role"] == "user":
                        enhanced_body["messages"][i]["content"] = enhanced_content
                        break
                else:
                    # 如果没找到用户消息，添加一条
                    enhanced_body["messages"].append({
                        "role": "user", 
                        "content": enhanced_content
                    })
            else:
                # 如果没有messages字段，创建一条用户消息
                enhanced_body["messages"] = [{
                    "role": "user",
                    "content": enhanced_content
                }]
            
        # 删除options字段和旧的prompt字段
        if "options" in enhanced_body:
            del enhanced_body["options"]
        if "prompt" in enhanced_body:
            del enhanced_body["prompt"]
            
        return enhanced_body
    
    def _extract_user_query(self):
        """从请求中提取用户查询"""
        # 从messages中提取
        if "messages" in self.body_json:
            for msg in reversed(self.body_json["messages"]):
                if msg.get("role") == "user" and "content" in msg:
                    return msg["content"]
        
        # 从prompt中提取
        if "prompt" in self.body_json:
            if isinstance(self.body_json["prompt"], str):
                return self.body_json["prompt"]
            elif isinstance(self.body_json["prompt"], list):
                for item in self.body_json["prompt"]:
                    if item.get("type") == "text":
                        return item.get("text", "")
        
        return ""
