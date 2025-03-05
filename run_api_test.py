#!/usr/bin/env python3
"""
API连接测试工具，用于验证与API服务器的连接
"""

import os
import sys
import json
import requests
import argparse
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_api_connection(api_url=None, api_key=None, verbose=False):
    """测试API连接"""
    # 使用提供的参数或环境变量
    api_url = api_url or os.environ.get("OPENAI_API_URL", "https://api.chatfire.cn/v1/chat/completions")
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        print("错误: 未提供API密钥，请设置OPENAI_API_KEY环境变量或使用--api-key参数")
        return False
    
    print(f"正在测试连接: {api_url}")
    
    # 构建简单的测试请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "qwen2-7b-instruct",
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 10
    }
    
    try:
        # 测试1: 使用requests库，禁用SSL验证
        print("测试1: 使用requests库，禁用SSL验证...")
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=10,
            verify=False  # 禁用SSL验证
        )
        
        if response.status_code == 200:
            print(f"✅ 测试1成功! 响应码: {response.status_code}")
            if verbose:
                print("响应内容:")
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ 测试1失败. 响应码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"❌ 测试1失败. 错误: {str(e)}")
    
    try:
        # 测试2: 使用urllib3直接请求
        print("\n测试2: 使用urllib3库直接请求...")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        
        encoded_data = json.dumps(payload).encode('utf-8')
        resp = http.request(
            'POST',
            api_url,
            body=encoded_data,
            headers=headers,
            timeout=10.0
        )
        
        if resp.status == 200:
            print(f"✅ 测试2成功! 响应码: {resp.status}")
            return True
        else:
            print(f"❌ 测试2失败. 响应码: {resp.status}")
            print(f"错误信息: {resp.data.decode('utf-8')}")
    except Exception as e:
        print(f"❌ 测试2失败. 错误: {str(e)}")
    
    # 提供解决方案建议
    print("\n=== 可能的解决方案 ===")
    print("1. 检查API密钥是否正确")
    print("2. 确认API URL是否正确")
    print("3. 检查您的网络连接")
    print("4. 添加DNS映射 (在hosts文件中添加api.chatfire.cn的IP地址映射)")
    print("5. 尝试直接使用IP地址代替域名")
    print("6. 检查防火墙或代理设置")
    
    # 尝试ping域名
    try:
        import subprocess
        domain = api_url.split("://")[1].split("/")[0]
        print(f"\n尝试ping {domain}...")
        result = subprocess.run(['ping', '-c', '3', domain], 
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
        print(result.stdout)
    except Exception as e:
        print(f"无法执行ping: {str(e)}")
    
    return False

def main():
    parser = argparse.ArgumentParser(description='测试API连接')
    parser.add_argument('--api-url', help='API URL')
    parser.add_argument('--api-key', help='API密钥')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    success = test_api_connection(args.api_url, args.api_key, args.verbose)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
