def split_text(text, chunk_size, overlap):
    """
    将文本分割成指定大小的块
    
    Args:
        text (str): 要分割的文本
        chunk_size (int): 每个块的大小（字符数）
        overlap (int): 相邻块之间的重叠字符数
        
    Returns:
        list: 分割后的文本块列表
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # 确定当前块的结束位置
        end = start + chunk_size
        
        # 如果不是最后一块，尝试在适当的位置（句号、问号、感叹号后）断开
        if end < text_length:
            # 在chunk_size范围内寻找最后一个句子结束符
            for i in range(min(end + 100, text_length) - 1, start + chunk_size//2, -1):
                if text[i] in '。.!?！？':
                    end = i + 1
                    break
        
        # 确保不超过文本总长度
        end = min(end, text_length)
        
        # 添加文本块
        chunks.append(text[start:end])
        
        # 移动到下一个起始位置，考虑重叠
        start = end - overlap
        
    return chunks
