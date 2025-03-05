import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from typing import Dict
from .base_engine import BaseSearchEngine

class GoogleSearchEngine(BaseSearchEngine):
    def search(self, query: str, min_results: int = 10, max_pages: int = 3) -> Dict:
        results = []
        driver = self.get_driver()
        
        try:
            print(f"正在访问 Google 搜索页面...")
            # 确保 URL 中的查询参数正确编码，并设置返回中文结果
            encoded_query = query.replace(' ', '+')
            # 添加 gl=cn 参数优先显示中文结果，同时保持 hl=en 使界面为英文
            driver.get(f"https://www.google.com/search?q={encoded_query}&hl=en&gl=cn")
            
            # 设置页面的字符编码
            driver.execute_script("document.charset='utf-8';")
            
            pages_searched = 0
            while len(results) < min_results and pages_searched < max_pages:
                try:
                    print(f"等待搜索结果加载... 第 {pages_searched + 1} 页")
                    # 增加等待时间，使用多个可能的选择器
                    results_present = False
                    for selector in ["div.g", "div[jscontroller]", "div.MjjYud"]:
                        try:
                            WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            results_present = True
                            break
                        except:
                            continue
                            
                    if not results_present:
                        print("未找到搜索结果元素")
                        break
                    
                    # 获取搜索结果
                    search_results = driver.find_elements(By.CSS_SELECTOR, "div.g")
                    print(f"找到 {len(search_results)} 个结果")
                    
                    for result in search_results:
                        try:
                            title = result.find_element(By.CSS_SELECTOR, "h3").text
                            link = result.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
                            snippet = result.find_element(By.CSS_SELECTOR, "div.VwiC3b, div[data-content-feature='1']").text
                            
                            # 确保文本内容是 UTF-8 编码
                            title = title.encode('utf-8').decode('utf-8', errors='ignore')
                            snippet = snippet.encode('utf-8').decode('utf-8', errors='ignore')
                            
                            if title and link and snippet:
                                results.append({
                                    'title': title,
                                    'link': link,
                                    'snippet': snippet
                                })
                                print(f"已添加结果: {title[:30]}...")
                        except Exception as e:
                            print(f"解析结果时出错: {str(e)}")
                            continue
                    
                    if pages_searched < max_pages - 1:
                        print("尝试跳转到下一页...")
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.ID, "pnnext"))
                        )
                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(3)  # 增加页面加载等待时间
                        pages_searched += 1
                    else:
                        break
                        
                except Exception as e:
                    print(f"处理页面时出错: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"Google搜索过程出错: {str(e)}")
            
        finally:
            print(f"搜索完成，共找到 {len(results)} 个结果")
            driver.quit()
            
        return {'items': results[:min_results]}