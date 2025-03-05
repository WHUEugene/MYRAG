import requests
import json
import argparse
import sys
import base64
import os
from typing import Optional, Dict, Any, Union

def send_request(
    prompt: str = "",
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    model: str = "Qwen/Qwen2-VL-72B-Instruct", 
    stream: bool = True, 
    max_tokens: int = 1000,
    api_key: str = "sk-uraxvklolwrdxsywxrjlurefzrznlifsjjubzzmjrvtfbwiu"
) -> Union[str, Dict[str, Any]]:
    """发送请求到SiliconFlow API"""
    
    url = "https://api.siliconflow.cn/v1/chat/completions"
    
    # 构建消息内容
    content = []
    
    # 处理图片：优先使用本地图片通过base64编码
    if image_path:
        if not os.path.exists(image_path):
            print(f"错误: 图片文件不存在 '{image_path}'")
            sys.exit(1)
        
        # 读取图片并base64编码
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        # 确定MIME类型
        mime_type = "image/jpeg"  # 默认MIME类型
        if image_path.lower().endswith('.png'):
            mime_type = "image/png"
        elif image_path.lower().endswith('.gif'):
            mime_type = "image/gif"
        elif image_path.lower().endswith('.webp'):
            mime_type = "image/webp"
            
        # 添加base64编码的图片
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{encoded_image}"
            }
        })
    elif image_url:
        # 如果没有提供本地图片，使用URL
        content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
    
    # 如果有文本提示，添加文本
    if prompt:
        content.append({
            "type": "text",
            "text": prompt
        })
    
    payload = {
        "model": model,
        "stream": stream,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.request("POST", url, json=payload, headers=headers, stream=stream)
        response.raise_for_status()
        
        # 处理流式响应
        if stream:
            full_response = ""
            print("流式输出开始:")
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content:
                                print(content, end='', flush=True)
                                full_response += content
                        except json.JSONDecodeError:
                            print(f"解析响应失败: {data_str}")
            print("\n流式输出结束")
            return full_response
        else:
            # 非流式响应
            return response.json()
            
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="SiliconFlow API测试工具")
    parser.add_argument("--prompt", type=str, help="文本提示", default="")
    parser.add_argument("--image-file", type=str, help="本地图像文件路径",default="/Users/linyong/Downloads/WechatIMG482.jpg")
    parser.add_argument("--image-url", type=str, help="图像URL", 
                       )
    parser.add_argument("--model", type=str, default="Qwen/Qwen2-VL-72B-Instruct", help="使用的模型")
    parser.add_argument("--no-stream", action="store_true", help="禁用流式输出")
    parser.add_argument("--max-tokens", type=int, default=1000, help="最大生成令牌数")
    parser.add_argument("--api-key", type=str, 
                       default="sk-uraxvklolwrdxsywxrjlurefzrznlifsjjubzzmjrvtfbwiu", 
                       help="API密钥")
    
    args = parser.parse_args()
    
    # 如果既没有提供本地图片也没有提供URL，使用默认URL
    image_url = None if args.image_file else args.image_url
    
    result = send_request(
        prompt=args.prompt,
        image_path=args.image_file,
        image_url=image_url,
        model=args.model,
        stream=not args.no_stream,
        max_tokens=args.max_tokens,
        api_key=args.api_key
    )
    
    if not args.no_stream:
        print(f"\n\n完整响应:{result}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()