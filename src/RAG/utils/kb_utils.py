import os
import json
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 修改配置文件路径
KB_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'kb_config.json')
logger.debug(f"KB_CONFIG_FILE 路径: {KB_CONFIG_FILE}")

def load_kb_config():
    """加载知识库配置文件"""
    if os.path.exists(KB_CONFIG_FILE):
        with open(KB_CONFIG_FILE, 'r') as f:
            try:
                config = json.load(f)
                if 'kb_list' not in config:
                    config['kb_list'] = {}
                logger.debug("load_kb_config: 读取配置成功")
                return config
            except Exception as e:
                logger.error(f"load_kb_config: 读取配置失败，异常: {e}")
                return {'kb_list': {}}
    logger.debug("load_kb_config: 配置文件不存在，返回空配置")
    return {'kb_list': {}}

def save_kb_config(config):
    """保存知识库配置文件"""
    with open(KB_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    logger.debug(f"save_kb_config: 配置保存成功")
