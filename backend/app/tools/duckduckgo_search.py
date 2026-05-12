"""
DuckDuckGo 搜索工具
免费、无需 API Key，国内部分网络可访问
作为必应搜索的免费替代方案
"""
from typing import Any, Dict, List, Optional
import asyncio
import json
import re
from urllib.parse import quote

import httpx
from loguru import logger

from .base_tool import BaseTool, ToolResult, ToolRegistry


@ToolRegistry.register
class DuckDuckGoSearchTool(BaseTool):
    """
    DuckDuckGo 搜索工具
    免费、无需 API Key，适合作为默认搜索方案
    支持网页搜索和新闻搜索
    """
    
    name = "web_search"
    description = "在互联网上搜索实时信息，获取最新旅游资讯、景点评价、当地新闻等。使用 DuckDuckGo 搜索引擎，免费且无需 API Key。"
    version = "1.0.0"
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，支持中文和英文。如'杭州西湖旅游攻略 2024'、'成都美食推荐'"
            },
            "num_results": {
                "type": "integer",
                "description": "返回结果数量，默认10条，最大30",
                "default": 10,
                "minimum": 1,
                "maximum": 30
            },
            "search_type": {
                "type": "string",
                "description": "搜索类型：web-网页搜索, news-新闻搜索",
                "enum": ["web", "news"],
                "default": "web"
            },
            "region": {
                "type": "string",
                "description": "区域代码，如'cn-zh'（中国）、'us-en'（美国）",
                "default": "cn-zh"
            },
            "time_range": {
                "type": "string",
                "description": "时间范围：d-过去一天, w-过去一周, m-过去一月",
                "enum": ["d", "w", "m"],
                "default": None
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        self.timeout = self.config.get("timeout", 30)
        self.max_results = self.config.get("max_results", 10)
        
        # DuckDuckGo 搜索 API 端点
        self.base_url = "https://duckduckgo.com"
        self.html_url = "https://html.duckduckgo.com"
        
        # 无需 API Key，默认启用
        logger.info(f"{self.name} 初始化完成（DuckDuckGo 免费搜索）")
    
    async def execute(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "web",
        region: str = "cn-zh",
        time_range: Optional[str] = None
    ) -> ToolResult:
        """
        执行 DuckDuckGo 搜索
        
        Args:
            query: 搜索关键词
            num_results: 结果数量
            search_type: 搜索类型
            region: 区域代码
            time_range: 时间范围
            
        Returns:
            ToolResult: 搜索结果
        """
        try:
            if search_type == "news":
                results = await self._search_news(query, num_results, region)
            else:
                results = await self._search_web(query, num_results, region, time_range)
            
            result_data = {
                "query": query,
                "search_type": search_type,
                "region": region,
                "count": len(results),
                "results": results
            }
            
            logger.info(f"DuckDuckGo 搜索完成: {query}, 找到 {len(results)} 条结果")
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "provider": "duckduckgo",
                    "search_type": search_type,
                    "region": region
                }
            )
            
        except httpx.TimeoutException:
            logger.error("DuckDuckGo 搜索请求超时")
            return ToolResult(
                success=False,
                data=None,
                error="搜索请求超时，请稍后重试"
            )
        except Exception as e:
            logger.error(f"DuckDuckGo 搜索失败: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=f"搜索服务暂时不可用: {str(e)}。提示：国内网络访问 DuckDuckGo 可能需要代理。"
            )
    
    async def _search_web(
        self, 
        query: str, 
        num_results: int,
        region: str,
        time_range: Optional[str] = None
    ) -> List[Dict]:
        """
        执行网页搜索
        
        使用 DuckDuckGo HTML 版本，更稳定
        """
        results = []
        
        # 构建参数
        params = {
            "q": query,
            "kl": region,  # 区域和语言
        }
        
        # 时间范围参数
        if time_range:
            time_params = {
                "d": "d",      # 过去24小时
                "w": "w",      # 过去一周
                "m": "m"       # 过去一月
            }
            if time_range in time_params:
                params["df"] = time_params[time_range]
        
        # 请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            # 第一步：获取搜索结果页面
            search_url = f"{self.html_url}/html"
            response = await client.get(search_url, params=params, headers=headers)
            response.raise_for_status()
            html = response.text
            
            # 解析搜索结果
            results = self._parse_html_results(html, num_results)
        
        return results
    
    async def _search_news(
        self, 
        query: str, 
        num_results: int,
        region: str
    ) -> List[Dict]:
        """
        执行新闻搜索
        """
        # DuckDuckGo 新闻搜索参数
        params = {
            "q": query,
            "kl": region,
            "iar": "news",  # 新闻筛选
            "df": "w",       # 过去一周的新闻
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            search_url = f"{self.html_url}/html"
            response = await client.get(search_url, params=params, headers=headers)
            response.raise_for_status()
            html = response.text
            
            results = self._parse_html_results(html, num_results, is_news=True)
        
        return results
    
    def _parse_html_results(self, html: str, max_results: int, is_news: bool = False) -> List[Dict]:
        """
        解析 HTML 搜索结果
        
        从 DuckDuckGo HTML 页面提取搜索结果
        """
        results = []
        
        # 使用正则表达式提取结果
        # DuckDuckGo HTML 结果通常在这个结构中
        result_pattern = r'<div class="result[^"]*"[^>]*>.*?<h[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?(?:<a[^>]*class="result__snippet"[^>]*>(.*?)</a>|<div[^>]*class="result__snippet"[^>]*>(.*?)</div>)?</div>'
        
        matches = re.findall(result_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for i, match in enumerate(matches[:max_results]):
            if len(match) >= 3:
                link = match[0]
                title = self._clean_html(match[1])
                snippet = self._clean_html(match[2]) if match[2] else (self._clean_html(match[3]) if len(match) > 3 and match[3] else "")
                
                # 过滤广告和不相关结果
                if link and not link.startswith("/") and title:
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet,
                        "source": self._extract_domain(link),
                        "position": i + 1,
                        "type": "news" if is_news else "web"
                    })
        
        # 如果正则没有匹配到，尝试备用解析方式
        if not results:
            results = self._parse_html_fallback(html, max_results)
        
        return results
    
    def _parse_html_fallback(self, html: str, max_results: int) -> List[Dict]:
        """
        备用 HTML 解析方法
        """
        results = []
        
        # 查找所有链接和标题
        # 匹配包含搜索结果特征的元素
        patterns = [
            # 方法1：查找具有 result 类的 div
            r'<div[^>]*class="[^"]*result[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<div[^>]*>(.*?)</div>.*?</div>',
            # 方法2：查找结果链接
            r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            
            for match in matches[:max_results]:
                if isinstance(match, tuple):
                    link = match[0]
                    title = self._clean_html(match[1])
                    snippet = self._clean_html(match[2]) if len(match) > 2 else ""
                else:
                    link = match
                    title = "[需要进一步获取标题]"
                    snippet = ""
                
                if link and title and not link.startswith("/"):
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet,
                        "source": self._extract_domain(link),
                        "position": len(results) + 1
                    })
            
            if results:
                break
        
        return results[:max_results]
    
    def _clean_html(self, text: str) -> str:
        """清理 HTML 标签和实体"""
        if not text:
            return ""
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 解码 HTML 实体
        html_entities = {
            '&quot;': '"',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&nbsp;': ' ',
            '&#39;': "'",
            '&ndash;': '-',
            '&mdash;': '-',
        }
        
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        # 移除多余空白
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return url


# 备选：使用 DuckDuckGo 的 Instant Answer API（更轻量）
@ToolRegistry.register  
class DuckDuckGoInstantTool(BaseTool):
    """
    DuckDuckGo Instant Answer API
    用于快速获取摘要信息，如景点介绍、定义等
    """
    
    name = "instant_answer"
    description = "快速获取实体信息摘要，如景点介绍、名人简介、定义解释等。"
    version = "1.0.0"
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "查询关键词，如'西湖简介'、'黄山风景区'"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.timeout = self.config.get("timeout", 20)
    
    async def execute(self, query: str) -> ToolResult:
        """执行 Instant Answer 查询"""
        try:
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
                "t": "TravelAI"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
            
            # 提取相关信息
            answer = data.get("AbstractText", "")
            source = data.get("AbstractSource", "")
            url = data.get("AbstractURL", "")
            heading = data.get("Heading", "")
            
            # 获取相关主题
            related = [
                {"text": t.get("Text", ""), "url": t.get("FirstURL", "")}
                for t in data.get("RelatedTopics", [])[:5]
                if t.get("Text")
            ]
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "heading": heading,
                    "answer": answer,
                    "source": source,
                    "url": url,
                    "related_topics": related
                }
            )
            
        except Exception as e:
            logger.error(f"Instant Answer 查询失败: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
