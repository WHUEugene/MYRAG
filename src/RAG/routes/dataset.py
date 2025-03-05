from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import uuid
import os
import json
import fitz  # PyMuPDF for PDF processing

# 从kb_utils导入配置函数，而不是从document_server
from RAG.utils.kb_utils import load_kb_config, save_kb_config
# 使用Blueprint而不是直接依赖app实例
dataset_bp = Blueprint('dataset', __name__)

# 定义允许的文件扩展名
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'html', 'json', 'md'}

@dataset_bp.route('/api/knowledge-base/<kb_id>/preview', methods=['POST'])
def preview_file(kb_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file and file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
        preview_text = get_file_preview(file)
        return jsonify({'preview': preview_text})
    return jsonify({'error': 'Unsupported file type'}), 400

@dataset_bp.route('/api/knowledge-base/<kb_id>/dataset', methods=['POST'])
def upload_dataset(kb_id):
    """处理数据集上传"""
    try:
        # 获取上传的文件
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No selected file'}), 400
            
        # 生成唯一数据集ID
        dataset_id = str(uuid.uuid4())
        
        # 获取上传文件夹路径
        upload_folder = current_app.config['UPLOAD_FOLDER']
        kb_folder = os.path.join(upload_folder, kb_id)
        os.makedirs(kb_folder, exist_ok=True)
        
        # 保存文件
        filename = file.filename
        filepath = os.path.join(kb_folder, filename)
        file.save(filepath)
        
        # 更新知识库配置
        config = load_kb_config()
        if kb_id not in config['kb_list']:
            return jsonify({'error': 'Knowledge base not found'}), 404
            
        # 添加数据集信息
        dataset_info = {
            'id': dataset_id,
            'name': filename,
            'file_path': filepath,
            'created_at': datetime.now().isoformat(),
            'status': 'PENDING',
            'enabled': True
        }
        config['kb_list'][kb_id]['datasets'].append(dataset_info)
        save_kb_config(config)
        
        # 获取Celery实例以运行异步任务
        # 使用current_app的扩展来获取celery实例
        from document_server import process_file
        task = process_file.delay(kb_id, dataset_id, filepath, 1000, 100)
        
        return jsonify({
            'id': dataset_id,
            'name': filename,
            'status': 'PENDING',
            'task_id': task.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dataset_bp.route('/api/knowledge-base/<kb_id>/dataset/<dataset_id>', methods=['DELETE'])
def delete_dataset(kb_id, dataset_id):
    """删除数据集"""
    try:
        # 加载配置
        config = load_kb_config()
        if kb_id not in config['kb_list']:
            return jsonify({'error': 'Knowledge base not found'}), 404
            
        # 查找并删除数据集
        datasets = config['kb_list'][kb_id]['datasets']
        dataset = None
        for ds in datasets:
            if ds['id'] == dataset_id:
                dataset = ds
                datasets.remove(ds)
                break
                
        if not dataset:
            return jsonify({'error': 'Dataset not found'}), 404
            
        # 保存更新后的配置
        save_kb_config(config)
        
        # 删除文件
        if 'file_path' in dataset and os.path.exists(dataset['file_path']):
            os.remove(dataset['file_path'])
            
        # 删除向量数据
        from document_server import delete_vectors
        delete_vectors(dataset_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dataset_bp.route('/api/knowledge-base/<kb_id>/dataset/<dataset_id>/toggle', methods=['PUT'])
def toggle_dataset(kb_id, dataset_id):
    """启用/禁用数据集"""
    try:
        # 验证请求
        data = request.json
        if not data or 'enabled' not in data:
            return jsonify({'error': 'Missing enabled parameter'}), 400
            
        enabled = data['enabled']
        
        # 加载配置
        config = load_kb_config()
        if kb_id not in config['kb_list']:
            return jsonify({'error': 'Knowledge base not found'}), 404
            
        # 查找并更新数据集
        datasets = config['kb_list'][kb_id]['datasets']
        dataset = None
        for ds in datasets:
            if ds['id'] == dataset_id:
                ds['enabled'] = enabled
                dataset = ds
                break
                
        if not dataset:
            return jsonify({'error': 'Dataset not found'}), 404
            
        # 保存配置
        save_kb_config(config)
        
        # 更新向量检索状态
        from document_server import toggle_vectors
        toggle_vectors(dataset_id, enabled)
        
        return jsonify({'success': True, 'enabled': enabled})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_file_preview(file):
    try:
        if file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')
            preview = content[:1000]
            if len(content) > 1000:
                preview += "\n\n仅预览前1000字"
            return preview
        elif file.filename.endswith('.pdf'):
            doc = fitz.open(stream=file.read(), filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
                if len(text) > 1000:
                    break
            doc.close()
            return text[:1000]
        return "预览不可用"
    except Exception as e:
        return f"预览失败: {str(e)}"
# 后端通过 get_file_preview() 函数来生成文件预览内容，其主要逻辑如下：
# 当上传的文件后缀为 .txt 时，直接读取文件内容并返回前 1000 个字符作为预览。
# 当文件为 .pdf 时，使用 fitz（PyMuPDF）库从文件数据流中打开 PDF，然后遍历页面并提取文本，累积文本达到 1000 个字符后停止，返回这部分文本。
# 对于其他文件类型（如 .doc、.docx、.html、.json、.md），目前不做预览处理，返回 “预览不可用”。
# 整个过程采用 try/except 包裹，如果出现异常，则返回 “预览失败: {错误信息}”。