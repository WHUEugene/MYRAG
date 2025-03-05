#!/usr/bin/env python3
"""
环境检查工具，用于验证系统配置、API连接和环境变量设置
"""

import os
import sys
import socket
import requests
import json
import logging
from urllib.parse import urlparse
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_api_connection(api_url, api_key=None):
    """
    检查API连接是否正常
    """
    logger.info(f"检查API连接: {api_url}")
    
    # 解析URL获取主机名
    parsed_url = urlparse(api_url)
    hostname = parsed_url.netloc.split(':')[0]
    
    # 检查DNS解析
    try:
        logger.info(f"尝试解析主机名: {hostname}")
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"DNS解析成功: {hostname} -> {ip_address}")
    except socket.gaierror as e:
        logger.error(f"DNS解析失败: {str(e)}")
        return False, f"DNS解析失败: 无法将主机名 {hostname} 解析为IP地址"
    
    # 简单的连接测试
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # 只发起一个HEAD请求，检查连接性
        response = requests.head(
            api_url,
            headers=headers,
            timeout=5
        )
        
        # 检查响应码
        if response.status_code < 400:
            logger.info(f"API连接成功，响应码: {response.status_code}")
            return True, f"API连接测试成功，响应码: {response.status_code}"
        else:
            logger.warning(f"API连接测试返回错误码: {response.status_code}")
            return False, f"API连接测试返回错误码: {response.status_code}"
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: {str(e)}")
        return False, f"连接错误: {str(e)}"
    except requests.exceptions.Timeout as e:
        logger.error(f"请求超时: {str(e)}")
        return False, f"请求超时: {str(e)}"
    except requests.exceptions.RequestException as e:
        logger.error(f"请求异常: {str(e)}")
        return False, f"请求异常: {str(e)}"

def check_environment_variables():
    """检查必要的环境变量是否设置"""
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API密钥",
    }
    
    optional_vars = {
        "OPENAI_API_URL": "OpenAI API URL (默认: https://api.chatfire.cn/v1/chat/completions)",
        "MODEL_CAPABILITIES_FILE": "模型能力配置文件路径",
        "TARGET_PORT": "Ollama服务端口"
    }
    
    status = True
    messages = []
    
    # 检查必要环境变量
    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            status = False
            messages.append(f"❌ 缺少必要环境变量: {var_name} - {description}")
        else:
            val = os.environ.get(var_name)
            masked_val = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
            messages.append(f"✅ {var_name} 已设置为: {masked_val}")
    
    # 检查可选环境变量
    for var_name, description in optional_vars.items():
        if os.environ.get(var_name):
            messages.append(f"✅ {var_name} 已设置为: {os.environ.get(var_name)}")
        else:
            messages.append(f"⚠️ {var_name} 未设置 - {description}")
    
    return status, messages

def main():
    parser = argparse.ArgumentParser(description='检查环境配置和API连接')
    parser.add_argument('--api-url', default=os.environ.get('OPENAI_API_URL', 'https://api.chatfire.cn/v1/chat/completions'),
                        help='要测试的API URL')
    parser.add_argument('--api-key', default=os.environ.get('OPENAI_API_KEY'),
                        help='API密钥')
    
    args = parser.parse_args()
    
    print("=== 环境变量检查 ===")
    env_status, env_messages = check_environment_variables()
    for msg in env_messages:
        print(msg)
    
    print("\n=== API连接测试 ===")
    if args.api_url:
        conn_status, conn_message = check_api_connection(args.api_url, args.api_key)
        if conn_status:
            print(f"✅ {conn_message}")
        else:
            print(f"❌ {conn_message}")
            
            # 提供解决方案建议
            print("\n=== 可能的解决方案 ===")
            if "DNS解析失败" in conn_message:
                print("1. 检查您的网络连接是否正常")
                print("2. 确认API域名是否正确")
                print(f"3. 尝试ping该域名: ping {urlparse(args.api_url).netloc}")
                print("4. 检查您的DNS设置")
            elif "连接错误" in conn_message:
                print("1. 确认API服务器是否在线")
                print("2. 检查您的防火墙设置")
                print("3. 如果使用代理，请验证代理设置")
            print(f"4. 尝试使用另一个API端点，例如 https://api.openai.com/v1/chat/completions")
    else:
        print("❌ 未提供API URL，无法进行连接测试")
    
    return 0 if env_status else 1

if __name__ == "__main__":
    sys.exit(main())
