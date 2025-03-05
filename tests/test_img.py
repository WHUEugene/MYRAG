import aiohttp
import asyncio
import json
import base64
from pathlib import Path
import sys
import mimetypes

# 代理服务器地址
PROXY_URL = "http://localhost:11435/api/chat"  # 根据代理服务器实际端口调整

async def send_message_with_image(prompt, image_path, model="qwen2.5", format_type="messages"):
    """发送包含图片的消息到代理服务器
    
    Args:
        prompt: 提示词`
        image_path: 图片路径
        model: 使用的模型
        format_type: 格式类型 ("messages"=新格式, "prompt"=Ollama格式)
    """
    # 读取并编码图片
    try:
        # 获取正确的MIME类型
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = 'image/jpeg'  # 默认MIME类型
            
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
        print(f"图片编码完成，长度: {len(image_data)}")
        print(f"MIME类型: {mime_type}")
        print(f"图片数据前20个字符: {image_data[:20]}...")
    except Exception as e:
        print(f"无法读取图片文件 {image_path}: {e}")
        return
    
    # 根据选择的格式类型构建请求体
    if format_type == "messages":
        # 使用新的消息格式
        request_data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_data]
                }
            ],
            "options": {
                "rag_enabled": False,
                "web_search_enabled": False
            }
        }
        print("使用新消息格式 (messages)")
    else:
        # 使用Ollama原生格式
        request_data = {
            "model": model,
            "prompt": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image",
                    "data": image_data,
                    "mime_type": mime_type
                }
            ],
            "options": {
                "rag_enabled": False,
                "web_search_enabled": False
            }
        }
        print("使用Ollama原生格式 (prompt)")
    
    print(f"发送请求到: {PROXY_URL}")
    print(f"使用模型: {model}")
    print(f"提示词: {prompt}")
    print(f"图片路径: {image_path}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(PROXY_URL, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"错误: 服务器返回状态码 {response.status}")
                    print(f"错误信息: {error_text}")
                    return
                
                print("\n--- 开始接收服务器响应 ---")
                # 处理流式响应
                full_response = ""
                async for line in response.content:
                    if not line.strip():
                        continue
                        
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            text_chunk = data["response"]
                            print(text_chunk, end="", flush=True)
                            full_response += text_chunk
                    except json.JSONDecodeError as e:
                        print(f"无法解析响应数据: {line} ({e})")
                
                print("\n--- 响应结束 ---")
                return full_response
                
    except aiohttp.ClientError as e:
        print(f"请求出错: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")

async def main():
    import sys
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "/Users/linyong/Downloads/4801740467936_.pic.jpg"
    
    if len(sys.argv) > 2:
        model = sys.argv[2]
    else:
        model = "qwen2.5"
    
    prompt = "请详细描述这张图片并附上诗意的语言。"
    if len(sys.argv) > 3:
        prompt = sys.argv[3]
    
    format_type = "messages"  # 默认使用新格式
    if len(sys.argv) > 4:
        format_type = sys.argv[4]
        
    print(f"使用图片: {image_path}")
    print(f"使用模型: {model}")
    print(f"使用提示: {prompt}")
    print(f"使用格式: {format_type}")
    
    await send_message_with_image(prompt, image_path, model, format_type)

if __name__ == "__main__":
    asyncio.run(main())