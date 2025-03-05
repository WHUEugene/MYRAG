def create_ollama_response(model, response, done=False):
    """
    创建符合Ollama Chat API格式的响应
    
    参数:
        model (str): 模型名称
        response (str): 响应内容
        done (bool): 是否是最终响应
    
    返回:
        dict: Ollama Chat API格式的响应字典
    """
    import time
    
    if done:
        # 最终响应格式
        return {
            "model": model,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "done": True,
            "total_duration": 0,  # 这些字段在最终响应时由Ollama填充
            "load_duration": 0,
            "prompt_eval_count": 0,
            "prompt_eval_duration": 0,
            "eval_count": 0,
            "eval_duration": 0
        }
    else:
        # 流式响应格式 - 对于chat接口
        return {
            "model": model,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "message": {
                "role": "assistant",
                "content": response,
                "images": None
            },
            "done": False
        }
