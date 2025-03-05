from flask import Flask, render_template, send_from_directory, request, jsonify
import os, json
from datetime import datetime
from dotenv import load_dotenv
import logging
import traceback
import numpy as np
import faiss  # 使用 FAISS 作为向量数据库

# 加载.env文件
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# # 主要职责:主程序入口
# 1. Flask应用初始化和配置
# 2. Celery异步任务配置 
# 3. 知识库配置文件管理
# 4. 文件处理核心逻辑
app = Flask(__name__)
DOC_SERVER_PORT = int(os.getenv('DOC_SERVER_PORT', 5000))  # 默认5000,但可通过环境变量覆盖
app.config['DOC_SERVER_PORT'] = DOC_SERVER_PORT
# 修改为项目根目录下的knowledge_base文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_base')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 同样修改向量存储目录路径
VECTOR_STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vector_store')
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# 添加新的导入
from celery import Celery

# 配置Celery
celery = Celery('document_server',
                broker='redis://localhost:6379/0',
                backend='redis://localhost:6379/0',
                broker_transport_options={'visibility_timeout': 3600})

import vector_store as vector_store
from langchain.text_splitter import RecursiveCharacterTextSplitter
from RAG.utils.db_utils import DBManager
# 从新模块导入知识库配置相关函数
from RAG.utils.kb_utils import load_kb_config, save_kb_config

db_manager = DBManager(os.path.join(VECTOR_STORE_DIR, 'chunks.db'))

# 初始化 FAISS 向量数据库（假设嵌入维度为768）
faiss_index = faiss.IndexFlatL2(768)
# 元数据存储，生产环境建议使用持久化存储
metadata_store = {}

# 全局变量定义
vector_stores = {}  # 存储每个知识库的向量数据库实例
chunk_metadata = {}  # 存储文档分块的元数据

def initialize_vector_store(kb_id):
    """初始化向量数据库"""
    print(f"[DEBUG] 初始化知识库 {kb_id} 的向量数据库")
    vector_file = os.path.join(VECTOR_STORE_DIR, f'{kb_id}.index')
    
    if (kb_id not in vector_stores):
        if os.path.exists(vector_file):
            print(f"[DEBUG] 加载已存在的向量索引: {vector_file}")
            vector_stores[kb_id] = faiss.read_index(vector_file)
        else:
            print(f"[DEBUG] 创建新的向量索引")
            vector_stores[kb_id] = faiss.IndexFlatL2(768)
    
    return vector_stores[kb_id]

def save_vector_store(kb_id):
    """保存向量索引到文件"""
    if kb_id in vector_stores:
        vector_file = os.path.join(VECTOR_STORE_DIR, f'{kb_id}.index')
        faiss.write_index(vector_stores[kb_id], vector_file)
        print(f"[DEBUG] 向量索引已保存: {vector_file}")

def delete_vectors(dataset_id):
    """从向量库中彻底删除指定数据集的所有数据"""
    print(f"[DEBUG] 删除数据集的向量数据: dataset_id={dataset_id}")
    
    try:
        # 1. 获取数据集的chunks
        chunks = db_manager.get_chunks(dataset_id=dataset_id)
        if not chunks:
            print(f"[DEBUG] 未找到数据集的chunks: dataset_id={dataset_id}")
            return
        
        # 2. 获取kb_id
        kb_id = chunks[0][2]  # 从查询结果中获取kb_id
        print(f"[DEBUG] 关联的知识库: kb_id={kb_id}")
        
        # 3. 处理向量存储
        if (kb_id in vector_stores):
            # 获取该知识库下其他数据集的chunks
            remaining_chunks = db_manager.get_chunks(kb_id=kb_id, dataset_id=None)
            remaining_chunks = [c for c in remaining_chunks if c[1] != dataset_id]
            
            if remaining_chunks:
                # 重建向量索引
                print(f"[DEBUG] 重建向量索引: kb_id={kb_id}")
                new_index = faiss.IndexFlatL2(768)
                vectors = [chunk[3] for chunk in remaining_chunks]
                new_index.add(np.array(vectors).astype('float32'))
                vector_stores[kb_id] = new_index
            else:
                # 如果知识库没有其他数据集，删除整个向量索引
                print(f"[DEBUG] 删除整个向量索引: kb_id={kb_id}")
                vector_stores.pop(kb_id, None)
                vector_file = os.path.join(VECTOR_STORE_DIR, f'{kb_id}.index')
                if os.path.exists(vector_file):
                    os.remove(vector_file)
        
        # 4. 从数据库中删除chunks
        db_manager.delete_chunks(dataset_id)
        print(f"[DEBUG] 已从数据库删除chunks: dataset_id={dataset_id}")
        
        # 5. 保存更新后的向量索引
        save_vector_store(kb_id)
        print(f"[DEBUG] 向量数据删除完成: dataset_id={dataset_id}")
        
    except Exception as e:
        print(f"[ERROR] 删除向量数据失败: {str(e)}")
        raise

def toggle_vectors(dataset_id, enabled):
    """启用/禁用向量数据的检索"""
    print(f"[DEBUG] {'启用' if enabled else '禁用'}数据集 {dataset_id} 的向量检索")
    db_manager.toggle_chunks(dataset_id, enabled)

# 修改 search_knowledge_base 函数中的错误处理
@app.route('/api/knowledge-base/<kb_id>/search', methods=['POST'])
def search_knowledge_base(kb_id):
    """知识库检索API"""
    try:
        # 1. 验证请求参数
        data = request.json
        if not data or 'query' not in data:
            error_msg = "缺少查询参数"
            logger.error(f"{error_msg}, 请求数据: {data}")
            return jsonify({'error': error_msg, 'details': '请求体必须包含query字段'}), 400
            
        query = data['query']
        top_k = data.get('top_k', 3)
        logger.info(f"接收到检索请求 - kb_id: {kb_id}, query: {query}, top_k: {top_k}")
        
        # 2. 检查知识库是否存在
        kb_config = load_kb_config()
        if (kb_id not in kb_config.get('kb_list', {})):
            error_msg = f"知识库 {kb_id} 不存在"
            logger.error(f"{error_msg}, 当前配置: {kb_config}")
            return jsonify({'error': error_msg, 'details': '请检查知识库ID是否正确'}), 404
        
        # 3. 获取所有启用的chunks
        try:
            chunks = db_manager.get_chunks(kb_id=kb_id)
            logger.debug(f"获取到知识库chunks数量: {len(chunks) if chunks else 0}")
        except Exception as e:
            error_msg = f"获取知识库chunks失败: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return jsonify({'error': error_msg, 'details': str(e)}), 500
            
        if not chunks:
            msg = f"知识库 {kb_id} 中未找到任何文档"
            logger.warning(msg)
            return jsonify({
                'query': query,
                'results': [],
                'message': msg
            })
        
        # 4. 生成查询向量
        logger.debug(f"开始生成查询向量，文本长度: {len(query)}")
        query_vector = embed_text(query)
        if query_vector is None:
            error_msg = "生成查询向量失败"
            logger.error(f"{error_msg}, 请检查Ollama服务")
            return jsonify({
                'error': error_msg, 
                'details': '请检查Ollama服务是否正常运行'
            }), 500
        
        # 5. 执行向量检索
        query_vector_np = np.array([query_vector]).astype('float32')
        vector_store = initialize_vector_store(kb_id)
        D, I = vector_store.search(query_vector_np, top_k)
        
        # 6. 整理检索结果 - 修改为符合RAG预期的格式
        results = []
        for i, idx in enumerate(I[0]):
            if idx < len(chunks):
                chunk_data = chunks[idx]
                # 构建标准化的结果格式 - 关键是这里包含text字段
                results.append({
                    'text': chunk_data[4],  # 文本内容放在text字段
                    'content': chunk_data[4],  # 保留原content字段以兼容
                    'score': float(1.0/(1.0 + D[0][i])),  # 归一化得分
                    'metadata': {
                        'dataset_id': chunk_data[1],
                        'kb_id': chunk_data[2]
                    }
                })
        
        # 7. 返回结果
        return jsonify({
            'query': query,
            'results': results
        })
        
    except Exception as e:
        error_msg = f"检索过程发生异常: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'error': error_msg,
            'details': traceback.format_exc(),
            'query': query if 'query' in locals() else None
        }), 500

# 添加用于获取知识库列表的API
@app.route('/api/knowledge-base/list', methods=['GET'])
def list_knowledge_bases():
    """获取所有知识库列表"""
    try:
        kb_config = load_kb_config()
        return jsonify({
            'kb_list': kb_config.get('kb_list', {})
        })
    except Exception as e:
        error_msg = f"获取知识库列表失败: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'error': error_msg,
            'details': traceback.format_exc()
        }), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@celery.task
def process_file(kb_id, dataset_id, filepath, chunk_size, overlap):
    """异步处理文件任务"""
    try:
        print(f"[DEBUG] 开始处理文件: {filepath}")
        
        # 读取文件内容
        content = get_file_content(filepath)
        print(f"[DEBUG] 文件内容读取完成，长度: {len(content)}")
        
        # 文本分段
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap
        )
        chunks = splitter.split_text(content)
        print(f"[DEBUG] 文本分段完成，共 {len(chunks)} 个分段")
        
        # 生成向量嵌入
        processed_chunks = []
        processed_vectors = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            try:
                vector = embed_text(chunk)
                if vector is not None and len(vector) == 768:
                    processed_chunks.append(chunk)
                    processed_vectors.append(vector)
                    print(f"[DEBUG] 成功处理第 {i+1}/{len(chunks)} 个分段")
            except Exception as e:
                print(f"[WARNING] 分段 {i+1} 处理失败: {str(e)}")
                continue
        
        if not processed_vectors:
            raise Exception("没有成功生成任何有效向量")
            
        # 直接保存向量和文本到数据库
        try:
            db_manager.add_chunks(kb_id, dataset_id, processed_chunks, processed_vectors)
            print(f"[DEBUG] 已保存 {len(processed_chunks)} 个分块到数据库")
            
            # 更新向量存储
            vectors_array = np.array(processed_vectors).astype('float32')
            vector_store = initialize_vector_store(kb_id)
            vector_store.add(vectors_array)
            save_vector_store(kb_id)
            print(f"[DEBUG] 已更新向量索引，当前总数: {vector_store.ntotal}")
            
        except Exception as e:
            raise Exception(f"保存数据失败: {str(e)}")
        
        # 验证数据是否正确保存
        saved_chunks = db_manager.get_chunks(kb_id=kb_id)
        if not saved_chunks:
            raise Exception("数据保存验证失败: 未找到保存的chunks")
        print(f"[DEBUG] 数据保存验证成功，找到 {len(saved_chunks)} 个chunks")
        
        # 更新状态
        config = load_kb_config()
        for dataset in config['kb_list'][kb_id]['datasets']:
            if dataset['id'] == dataset_id:
                dataset['status'] = 'COMPLETED'
                dataset['total_count'] = len(processed_chunks)
                break
        save_kb_config(config)
        
        print(f"[DEBUG] 文件处理完成: {dataset_id}")
        return True
        
    except Exception as e:
        error_msg = f"文件处理失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        
        # 更新失败状态
        config = load_kb_config()
        for dataset in config['kb_list'][kb_id]['datasets']:
            if dataset['id'] == dataset_id:
                dataset['status'] = 'FAILED'
                dataset['error'] = error_msg
                break
        save_kb_config(config)
        return False

def embed_text(text):
    """生成文本的向量嵌入"""
    import requests
    
    url = "http://127.0.0.1:11434/api/embeddings"
    payload = {
        "model": "nomic-embed-text",
        "prompt": text
    }
    
    try:
        print(f"[DEBUG] 发送向量嵌入请求，文本长度: {len(text)}")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            embeddings = data.get('embedding', [])
            if not embeddings:
                print(f"[WARNING] API返回空向量: {data}")
                return None
            
            # 打印向量维度信息用于调试
            print(f"[DEBUG] 生成向量维度: {len(embeddings)}")
            return embeddings
        else:
            print(f"[ERROR] API请求失败: 状态码={response.status_code}, 响应={response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Ollama embedding API 调用异常: {str(e)}")
        return None

def update_dataset_status(dataset_id, status):
    # 根据 dataset_id 更新配置中对应数据集的状态
    # 实现时可加载配置文件，遍历查找 dataset_id 后修改状态并保存配置
    pass

def get_file_content(filepath):
    """读取不同类型文件的内容"""
    ext = filepath.split('.')[-1].lower()
    
    if ext == 'txt':
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == 'pdf':
        import fitz
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    # TODO: 添加其他文件类型的处理
    raise ValueError(f"Unsupported file type: {ext}")

# 注册蓝图 - 将这些移到文件末尾
# 这样，我们的蓝图文件可以导入document_server中的函数，但document_server不会在导入蓝图时就完全执行蓝图模块
from RAG.routes.knowledge_base import kb_bp
from RAG.routes.dataset import dataset_bp

# 最后再注册蓝图
def register_blueprints():
    app.register_blueprint(kb_bp)
    app.register_blueprint(dataset_bp)

# 在文件结尾调用注册函数
if __name__ == '__main__':
    register_blueprints()
    app.run(port=DOC_SERVER_PORT, debug=True, host='0.0.0.0')
else:
    # 在非主程序情况下也注册蓝图
    register_blueprints()
