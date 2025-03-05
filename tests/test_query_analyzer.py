import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from proxyrequest.query_analyzer import QueryAnalyzer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_query_analyzer():
    # 创建查询分析器实例
    analyzer = QueryAnalyzer(min_confidence=0.6)
    
    # 测试案例 - 每组包含查询文本和预期结果
    test_cases = [
        # 网络搜索案例
        {"query": "最近的世界杯是在哪里举办的？", 
         "expected": {"web_search_enabled": True, "rag_enabled": False}},
        {"query": "今年的诺贝尔奖得主是谁？", 
         "expected": {"web_search_enabled": True, "rag_enabled": False}},
        {"query": "在网上搜索一下关于气候变化的最新报告", 
         "expected": {"web_search_enabled": True, "rag_enabled": False}},
        
        # 知识库检索案例
        {"query": "在知识库中查找关于太阳能电池的资料", 
         "expected": {"rag_enabled": True, "web_search_enabled": False}},
        {"query": "请查询一下我们公司的内部文档", 
         "expected": {"rag_enabled": True, "web_search_enabled": False}},
        
        # 混合案例
        {"query": "请在知识库中查找关于太阳能的最新研究进展", 
         "expected": {"rag_enabled": True, "web_search_enabled": True}},
        
        # 否定案例
        {"query": "告诉我关于Python的基础知识，但不要搜索网络", 
         "expected": {"web_search_enabled": False, "rag_enabled": False}},
        {"query": "不要使用知识库，直接回答我的问题", 
         "expected": {"rag_enabled": False, "web_search_enabled": False}},
        
        # 中性案例
        {"query": "你好，请介绍一下自己", 
         "expected": {"rag_enabled": False, "web_search_enabled": False}},
        {"query": "1+1等于几？", 
         "expected": {"rag_enabled": False, "web_search_enabled": False}},
    ]
    
    # 执行测试
    for i, case in enumerate(test_cases):
        query = case["query"]
        expected = case["expected"]
        
        print(f"\n测试案例 {i+1}: {query}")
        result = analyzer.analyze(query)
        
        # 检查结果
        success = True
        for feature, expected_value in expected.items():
            actual_value = result.get(feature, False)
            if actual_value != expected_value:
                success = False
                print(f"❌ {feature}: 预期={expected_value}, 实际={actual_value}")
            else:
                print(f"✓ {feature}: 正确")
        
        if success:
            print("✅ 测试通过")
        else:
            print("❌ 测试失败")
            # 打印详细分析
            score_details = analyzer._calculate_feature_score(
                query, analyzer.patterns.get(list(expected.keys())[0], {})
            )
            print(f"分数详情: {score_details}")

if __name__ == "__main__":
    test_query_analyzer()
