import logging
from abc import ABC, abstractmethod
from typing import Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import sys
import io

class BaseSearchEngine(ABC):
    def __init__(self):
        # 配置日志编码 - 修改为更安全的方式
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
    
    def get_driver(self):
        """初始化并返回配置好的WebDriver"""
        options = Options()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        # 设置中文支持
        options.add_argument('--lang=zh-CN')
        # 添加字符集
        options.add_argument('--accept-charset=UTF-8')
        # 设置默认编码
        options.add_argument('--default-encoding=UTF-8')
        # 添加请求头，指定接受中文内容
        options.add_argument('--accept-language=zh-CN,zh;q=0.9,en;q=0.8')
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # 设置页面大小
            driver.set_window_size(1920, 1080)
            
            return driver
        except Exception as e:
            self.logger.error(f"创建WebDriver时出错: {str(e)}")
            raise
        
    @abstractmethod
    def search(self, query: str, min_results: int = 10, max_pages: int = 3) -> Dict:
        pass
