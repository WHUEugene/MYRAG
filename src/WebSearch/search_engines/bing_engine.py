from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from typing import Dict
from .base_engine import BaseSearchEngine

class BingSearchEngine(BaseSearchEngine):
    def search(self, query: str, min_results: int = 10, max_pages: int = 3) -> Dict:
        results = []
        driver = self.get_driver()
        
        try:
            # 使用正确编码的查询并添加 &setlang=zh-Hans 参数来获取中文结果
            encoded_query = query.replace(' ', '+')
            driver.get(f"https://www.bing.com/search?q={encoded_query}")
            
            # 设置页面编码
            driver.execute_script("document.charset='utf-8';")
            
            pages_searched = 0
            while len(results) < min_results and pages_searched < max_pages:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "b_algo"))
                )
                
                # 获取搜索结果列表
                search_results = driver.find_elements(By.CLASS_NAME, "b_algo")
                
                for result in search_results:
                    try:
                        # 提取标题
                        title_element = result.find_element(By.CSS_SELECTOR, "h2 a")
                        title = title_element.text
                        link = title_element.get_attribute('href')
                        
                        # 提取摘要
                        snippet = ""
                        try:
                            snippet_element = result.find_element(By.CLASS_NAME, "b_caption")
                            p_element = snippet_element.find_element(By.TAG_NAME, "p")
                            snippet = p_element.text
                        except:
                            continue
                        
                        # 确保文本内容是 UTF-8 编码    
                        title = title.encode('utf-8').decode('utf-8', errors='ignore')
                        snippet = snippet.encode('utf-8').decode('utf-8', errors='ignore')
                            
                        if title and link and snippet:
                            results.append({
                                'title': title,
                                'link': link,
                                'snippet': snippet
                            })
                            
                    except Exception as e:
                        continue
                
                # 尝试点击下一页
                try:
                    next_button = driver.find_element(By.CLASS_NAME, "sb_pagN")
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)  # 等待页面加载
                    pages_searched += 1
                except:
                    break
                    
        finally:
            driver.quit()
            
        return {'items': results[:min_results]}
