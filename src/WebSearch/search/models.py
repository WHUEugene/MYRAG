import json
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class ContentParagraph:
    """代表文章中的一个段落及其相关性分数"""
    text: str
    score: float = 0.0
    
    def to_dict(self):
        return {
            'text': self.text,
            'score': self.score
        }

@dataclass
class SearchResult:
    """代表一个搜索结果"""
    title: str
    link: str
    snippet: str
    content: str = ""
    paragraphs: Optional[List[ContentParagraph]] = None
    relevance_score: float = 0.0
    
    def to_dict(self):
        return {
            'title': self.title,
            'link': self.link,
            'snippet': self.snippet,
            'content': self.content,
            'paragraphs': [p.to_dict() for p in self.paragraphs] if self.paragraphs else [],
            'relevance_score': self.relevance_score
        }

@dataclass
class SearchResponse:
    """搜索响应，包含查询和结果"""
    query: str
    results: List[SearchResult]
    total_results: int = 0
    search_time: float = 0.0
    
    def to_json(self):
        return json.dumps({
            'query': self.query,
            'results': [r.to_dict() for r in self.results],
            'total_results': self.total_results,
            'search_time': self.search_time
        }, ensure_ascii=False)
