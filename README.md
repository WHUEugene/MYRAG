# MyRag - Ollama增强代理服务

MyRag是一个智能代理服务，它扩展了Ollama API的功能，通过添加RAG(检索增强生成)、网络搜索和图像处理等能力，大幅提升模型响应质量。该项目将多种增强功能无缝集成到Ollama的API中，使本地大语言模型更加强大和实用。
![image](https://github.com/user-attachments/assets/27834fd3-5d5d-4ee7-a117-2065232d13b5)

## 功能特点

- **完全兼容Ollama API**: 可作为Ollama API的直接替代品，与所有支持Ollama的客户端兼容
- **知识库检索(RAG)**: 自动从私有知识库中检索相关信息，增强回答的准确性
- **实时网络搜索**: 为模型提供最新的互联网信息，克服本地模型知识时效性的限制
- **图像处理能力**: 支持模型理解和描述图像内容（支持多模态模型）
- **智能模式检测**: 自动检测查询意图，按需启用合适的增强功能
- **上下文优化**: 智能组织检索到的信息，优化提示词结构

## 系统架构

```
+----------------+
| proxy_server.py|
|   (主入口点)    |
+-------+--------+
        |
        v
+----------+---------+
|request_handlers.py |
|  (请求处理逻辑)    |
+--+-------+-------+-+
   |       |       |
   v       v       v
图像处理   RAG服务  Web搜索
   |       |       |
   +---+---+---+---+
       |       |
       v       v
  上下文增强   响应格式化
       |       |
       v       v
    Ollama API
```

## 安装指南

1. 克隆仓库
```bash
git clone https://github.com/yourusername/MyRag.git
cd MyRag
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
创建一个 `.env` 文件在项目根目录，包含以下配置：

```
# Ollama API地址(默认为http://localhost:11434)
TARGET_PORT=11434

# MyRag代理服务端口(默认为11435)
PROXY_PORT=11435

# 知识库路径(可选)
KNOWLEDGE_BASE_PATH=./knowledge_base

# 网络搜索API密钥(可选，用于加速网络搜索功能)
GOOGLE_API_KEY=xxxx
GOOGLE_SEARCH_ENGINE_ID=xxxx


```

## 使用方法


1. 启动服务器
```bash
python src/server_manager.py
```

2. 服务器默认在`http://localhost:11435`启动，可使用任何Ollama客户端连接此地址

3. 通过命令行使用
```bash
# 设置OLLAMA_HOST环境变量指向MyRag代理
export OLLAMA_HOST=http://localhost:11435

# 使用ollama命令与增强模型交互
```

4. 使用前端客户端

您可以将任何支持Ollama的前端客户端(如ChatBox、Ollama WebUI等)的API端点设置为`http://localhost:11435`，即可使用增强功能：

- [ChatBox](https://github.com/Bin-Huang/chatbox)：设置API端点为`http://localhost:11435`
- [Ollama WebUI](https://github.com/ollama/ollama-ui)：在设置中修改Ollama URL

5. 对于图像处理(多模态模型)
```bash
# 使用支持图像的客户端，或通过API：
curl -X POST http://localhost:11435/api/chat -d '{
  "model": "llava",
  "messages": [
    {
      "role": "user", 
      "content": "描述这张图片",
      "images": ["base64编码的图片..."]
    }
  ]
}'
```
！！！！现在需要ollama本地拥有以下模型：nomic-embed-text（用于知识库），qwen2.5（用于关键词提取），请使用ollama安装模型后使用，图像增强需要配置qwen2.5vl apikey或者使用openai gpt4o的apikey
## 配置选项

在请求中可以通过`options`字段配置增强功能:

```json
{
  "model": "llama3",
  "messages": [...],
  "options": {
    "rag_enabled": true,        // 启用知识库检索
    "web_search_enabled": true, // 启用网络搜索
    "auto_detect": true         // 启用自动检测(默认开启)
  }
}
```

## 依赖项目

- Ollama: https://github.com/ollama/ollama
- aiohttp: 异步HTTP服务器和客户端
- langchain: 知识库检索组件

## 许可证

MIT License

## 贡献指南

欢迎提交问题和功能请求。如需贡献代码，请先开issue讨论您想要更改的内容。

---

*MyRag - 让本地大模型更智能*
