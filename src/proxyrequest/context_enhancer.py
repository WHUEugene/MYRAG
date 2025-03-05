import logging
from typing import List

# 配置日志
logger = logging.getLogger(__name__)

def enhance_prompt_with_context(original_prompt: str, contexts: List[str]) -> str:
    """
    使用上下文增强原始提示词
    
    参数:
        original_prompt: 原始用户提示词
        contexts: 上下文列表，例如RAG结果、网络搜索结果等
        
    返回:
        str: 增强后的提示词
    """
    if not contexts:
        return original_prompt
    
    # 添加智能提示前缀
    enhanced_prompt = "我有一个问题，但在回答前，请考虑我提供的以下参考信息：\n\n"
    
    # 添加上下文信息
    for i, context in enumerate(contexts):
        if context.strip():
            enhanced_prompt += f"===参考信息 {i+1}===\n{context.strip()}\n\n"
    
    # 添加分隔符
    enhanced_prompt += "===我的问题===\n"
    
    # 添加原始提示词
    enhanced_prompt += original_prompt
    
    # 添加智能指令后缀
    enhanced_prompt += "\n\n请基于以上参考信息回答我的问题。如果参考信息与我的问题无关，请告诉我并尽力回答。如果参考信息已经过时，请明确指出并提供你知道的最新信息。"
    
    logger.info(f"已创建增强提示词，长度: {len(enhanced_prompt)} 字符")
    return enhanced_prompt
