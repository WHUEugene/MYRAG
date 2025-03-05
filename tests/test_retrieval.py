import requests
import json

def test_search(kb_id, query, top_k=3):
    """测试知识库检索"""
    url = f"http://127.0.0.1:5000/api/knowledge-base/{kb_id}/search"
    data = {
        "query": query,
        "top_k": top_k
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"检索失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"请求异常: {str(e)}")
        return None

def main():
    # 替换为实际的知识库ID
    KB_ID = "4582657b-211f-4c9f-863a-1c859ad6a7f8"
    
    test_queries = [
        "中华人民共和国的一切权力属于？",
        "城市的土地属于谁所有？",
        "中华人民共和国的行政区域划分是怎么样的？",
        
    ]
    
    for query in test_queries:
        print("\n" + "="*50)
        print(f"查询: {query}")
        print("-"*50)
        
        result = test_search(KB_ID, query)
        if result:
            for i, hit in enumerate(result['results'], 1):
                print(f"\n结果 {i} (相似度得分: {hit['score']:.4f}):")
                print(hit['text'])

if __name__ == "__main__":
    main()
