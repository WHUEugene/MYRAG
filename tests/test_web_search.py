import sys
import os
import json
import asyncio

# 添加项目根目录和src目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from src.web_search import process_web_search, extract_search_queries
from src.WebSearch.search.search_service import SearchService
import logging

# 修正日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def test_keyword_extraction():
    """测试关键词提取功能"""
    print("\n=== 测试关键词提取 ===")
    
    test_prompts = [
        "我想了解一下大模型训练需要什么样的硬件设备，以及具体的训练流程是怎样的？",
        "请介绍一下向量数据库的原理和应用场景，最好能给出一些实际的使用案例。",
        "最近GPT-4有什么新进展和突破吗？它在什么领域表现特别出色？"
    ]
    
    for prompt in test_prompts:
        print(f"\n原始问题: {prompt}")
        keywords = extract_search_queries(prompt)
        print(f"提取的关键词: {keywords}")

async def test_web_search():
    """测试网页搜索功能"""
    print("\n=== 测试网页搜索 ===")
    
    request_data = {
        "prompt": "搜索佛罗伦萨？",
        "search_options": {
            "engines": ["bing"],
            "min_results": 16,
            "max_pages": 15
        }
    }
    
    print("\n原始问题:", request_data["prompt"])
    
    # 执行搜索 - 使用await
    result = await process_web_search(request_data)
    
    # 打印结果
    print("\n搜索元数据:")
    print(f"- 提取的关键词: {result['metadata']['search_queries']}")
    print(f"- 找到的结果数: {result['metadata']['total_results']}")
    print(f"- 信息来源数: {len(result['metadata']['sources'])}")
    
    # 保存完整结果到文件
    output_file = 'search_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n完整结果已保存到: {output_file}")
    
    # 打印增强后的提示词前300个字符
    print("\n增强后的提示词预览:")
    print(result["prompt"])

async def main():
    """运行所有测试"""
    try:
        # 测试关键词提取
        # await test_keyword_extraction()
        
        # 测试网页搜索
        await test_web_search()
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {str(e)}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    # 使用asyncio运行异步主函数
    asyncio.run(main())
