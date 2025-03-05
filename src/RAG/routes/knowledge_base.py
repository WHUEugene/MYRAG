from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import uuid
import json, os

# 从新模块导入知识库配置相关函数，而不是从document_server导入
from RAG.utils.kb_utils import load_kb_config, save_kb_config

# # 主要API:
# - POST /api/knowledge-base        # 创建知识库
# - GET /api/knowledge-bases        # 获取知识库列表
# - PUT /api/knowledge-base/<id>    # 更新知识库配置
# - GET /api/knowledge-base/<id>/datasets  # 获取数据集列表
kb_bp = Blueprint('knowledge_base', __name__)

@kb_bp.route('/knowledge-base/<kb_id>')
def knowledge_base_page(kb_id):
    return render_template('knowledge_base.html')

@kb_bp.route('/knowledge-base/<kb_id>/upload', methods=['GET'])
def upload_page(kb_id):
    # 渲染上传数据集页面，并传入 kb_id
    return render_template('upload.html', kb_id=kb_id)

@kb_bp.route('/api/knowledge-base', methods=['POST'])
def create_knowledge_base():
    print("[DEBUG] create_knowledge_base: 请求数据", request.json)
    data = request.json
    config = load_kb_config()
    print("[DEBUG] create_knowledge_base: 加载配置", config)
    kb_id = str(uuid.uuid4())
    config['kb_list'][kb_id] = {
        'id': kb_id,
        'name': data['name'],
        'created_at': datetime.now().isoformat(),
        'embedding_model': 'text2vec',
        'text_model': 'chatglm2',
        'datasets': []
    }
    save_kb_config(config)
    # 重新加载查看写入结果
    new_config = load_kb_config()
    print("[DEBUG] create_knowledge_base: 保存后的配置", new_config)
    return jsonify({'id': kb_id})

@kb_bp.route('/api/knowledge-bases', methods=['GET'])
def list_knowledge_bases():
    config = load_kb_config()
    return jsonify([{
        'id': kb_id,
        'name': kb_data['name'],
        'created_at': kb_data['created_at']
    } for kb_id, kb_data in config['kb_list'].items()])

@kb_bp.route('/api/knowledge-base/<kb_id>/config', methods=['PUT'])
def update_kb_config(kb_id):
    data = request.json
    config = load_kb_config()
    if kb_id in config['kb_list']:
        config['kb_list'][kb_id].update({
            'embedding_model': data['embedding_model'],
            'text_model': data['text_model']
        })
        save_kb_config(config)
        return jsonify({'success': True})
    return jsonify({'error': 'Knowledge base not found'}), 404

@kb_bp.route('/api/knowledge-base/<kb_id>/config', methods=['POST'])
def create_kb_config(kb_id):
    config = load_kb_config()
    if kb_id not in config['kb_list']:
        return jsonify({'error': 'Knowledge base not found'}), 404
    default_config = {
        'embedding_model': 'default_embedding',
        'text_model': 'default_text'
    }
    config['kb_list'][kb_id].update(default_config)
    save_kb_config(config)
    return jsonify({**default_config, 'success': True})

@kb_bp.route('/api/knowledge-base/<kb_id>/config', methods=['GET'])
def get_kb_config(kb_id):
    config = load_kb_config()
    if kb_id in config['kb_list']:
        kb_config = config['kb_list'][kb_id]
        return jsonify({
            'embedding_model': kb_config.get('embedding_model', ''),
            'text_model': kb_config.get('text_model', '')
        })
    return jsonify({'error': 'Knowledge base not found'}), 404

@kb_bp.route('/api/knowledge-base/<kb_id>/datasets', methods=['GET'])
def list_datasets(kb_id):
    config = load_kb_config()
    if kb_id in config['kb_list']:
        # 确保每个数据集都有enabled字段
        datasets = config['kb_list'][kb_id]['datasets']
        for dataset in datasets:
            if 'enabled' not in dataset:
                dataset['enabled'] = True
        return jsonify(datasets)
    return jsonify({'error': 'Knowledge base not found'}), 404
