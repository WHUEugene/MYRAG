import requests
from bs4 import BeautifulSoup
import json
import time
from fake_useragent import UserAgent
from urllib.parse import quote_plus

class GoogleScraper:
    def __init__(self):
        self.base_url = "https://www.bing.com/search"
        self.ua = UserAgent()
        
    def search(self, query, num_results=10):
        formatted_results = {
            "searchInformation": {
                "searchTime": None,
                "totalResults": "0",
            },
            "items": []
        }
        
        try:
            start_time = time.time()
            
            headers = {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
                "TE": "Trailers",
                "DNT": "1"
            }
            
            params = {
                "q": query,
                "num": num_results,
            }
            
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                search_results = soup.find_all('div', class_='g')
                
                for result in search_results:
                    try:
                        title_element = result.find('h3')
                        link_element = result.find('a')
                        snippet_element = result.find('div', class_='VwiC3b')
                        
                        if title_element and link_element and snippet_element:
                            item = {
                                "title": title_element.text,
                                "htmlTitle": str(title_element),
                                "link": link_element.get('href'),
                                "displayLink": self._extract_domain(link_element.get('href')),
                                "snippet": snippet_element.text,
                                "htmlSnippet": str(snippet_element),
                                "pagemap": self._extract_meta(result)
                            }
                            formatted_results["items"].append(item)
                    except Exception as inner_e:
                        print(f"Error parsing search result: {inner_e}")
                
                end_time = time.time()
                formatted_results["searchInformation"]["searchTime"] = end_time - start_time
                formatted_results["searchInformation"]["totalResults"] = str(len(formatted_results["items"]))
                
                return formatted_results
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return formatted_results
    
    def _extract_domain(self, url):
        if url.startswith('http'):
            from urllib.parse import urlparse
            return urlparse(url).netloc
        return ''
    
    def _extract_meta(self, result):
        meta = {
            "metatags": [],
            "images": []
        }
        
        images = result.find_all('img')
        if images:
            meta["images"] = [{"src": img.get('src')} for img in images if img.get('src')]
        return meta

def main():
    scraper = GoogleScraper()
    results = scraper.search("Deepseek")
    
    # 保存结果到文件
    with open('scraped_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("搜索完成！结果已保存到 scraped_results.json")
    print(f"找到 {len(results['items'])} 个结果")
    print(f"搜索用时: {results['searchInformation']['searchTime']:.2f} 秒")

if __name__ == "__main__":
    main()
