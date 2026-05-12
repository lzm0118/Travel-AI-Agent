"""
必应 Bing 搜索工具
国内可访问的搜索服务
"""
from typing import Any, Dict, List, Optional
import asyncio

import httpx
from loguru import logger

from .base_tool import BaseTool, ToolResult, ToolRegistry
from ..core.config import get_search_config


@ToolRegistry.register
class BingSearchTool(BaseTool):
    """
    必应 Bing 搜索工具
    国内可访问，每月有 1000 次免费额度
    申请地址：https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
    """
    
    name = "bing_search"
    description = "使用必应 Bing 搜索引擎在互联网上搜索实时信息，获取最新旅游资讯、景点评价、当地新闻等。国内网络可直接访问，需要配置 Bing API Key。"
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
                "description": "返回结果数量，默认10条，最大50",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            },
            "search_type": {
                "type": "string",
                "description": "搜索类型：web-网页搜索, news-新闻搜索, images-图片搜索",
                "enum": ["web", "news", "images"],
                "default": "web"
            },
            "market": {
                "type": "string",
                "description": "市场/区域代码，如'zh-CN'（中国）、'en-US'（美国）",
                "default": "zh-CN"
            },
            "freshness": {
                "type": "string",
                "description": "时间范围：Day-过去24小时, Week-过去一周, Month-过去一月",
                "enum": ["Day", "Week", "Month"],
                "default": None
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # 从全局配置获取
        search_config = get_search_config()
        
        # API Key 优先级：配置传入 > 环境变量 BING_SEARCH_KEY > SEARCH_API_KEY
        self.api_key = (
            self.config.get("api_key") or 
            self.config.get("bing_key") or
            search_config.api_key or  # 从环境变量读取
            ""
        )
        
        self.timeout = self.config.get("timeout") or search_config.timeout or 30
        self.max_results = self.config.get("max_results") or search_config.max_results or 10
        self.endpoint = (
            self.config.get("endpoint") or 
            getattr(search_config, 'bing_endpoint', None) or
            "https://api.bing.microsoft.com/v7.0"
        )
        
        if not self.api_key:
            logger.warning(f"{self.name} 未配置 Bing API Key，工具将不可用")
            logger.info("请申请必应搜索 API: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api")
            self.enabled = False
    
    async def execute(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "web",
        market: str = "zh-CN",
        freshness: Optional[str] = None
    ) -> ToolResult:
        """
        执行必应搜索
        
        Args:
            query: 搜索关键词
            num_results: 结果数量
            search_type: 搜索类型
            market: 市场代码
            freshness: 时间范围
            
        Returns:
            ToolResult: 搜索结果
        """
        try:
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Accept": "application/json"
            }
            
            # 构建请求参数
            params = {
                "q": query,
                "count": min(num_results, 50),
                "offset": 0,
                "mkt": market,  # 市场
                "setLang": "zh" if market.startswith("zh") else "en",  # 语言
                "safesearch": "Moderate"
            }
            
            # 添加时间筛选
            if freshness:
                params["freshness"] = freshness
            
            # 构建端点
            if search_type == "web":
                endpoint = f"{self.endpoint}/search"
            elif search_type == "news":
                endpoint = f"{self.endpoint}/news/search"
            elif search_type == "images":
                endpoint = f"{self.endpoint}/images/search"
            else:
                endpoint = f"{self.endpoint}/search"
            
            logger.debug(f"必应搜索请求: {query}, 类型: {search_type}, 市场: {market}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    endpoint,
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            # 解析结果
            parsed_results = self._parse_results(data, search_type)
            
            # 获取总结果数
            total_count = 0
            if search_type == "web" and "webPages" in data:
                total_count = data["webPages"].get("totalEstimatedMatches", 0)
            elif search_type == "news" and "value" in data:
                total_count = len(data.get("value", []))
            
            result_data = {
                "query": query,
                "search_type": search_type,
                "market": market,
                "total_results": total_count,
                "count": len(parsed_results),
                "results": parsed_results
            }
            
            logger.info(f"必应搜索完成: {query}, 找到 {len(parsed_results)} 条结果")
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "provider": "bing",
                    "search_type": search_type,
                    "market": market
                }
            )
            
        except httpx.TimeoutException:
            logger.error("必应搜索请求超时")
            return ToolResult(
                success=False,
                data=None,
                error="搜索请求超时，请稍后重试"
            )
        except httpx.HTTPStatusError as e:
            error_msg = "搜索服务暂时不可用"
            if e.response.status_code == 401:
                error_msg = "API Key 无效或已过期，请检查 BING_SEARCH_KEY"
            elif e.response.status_code == 429:
                error_msg = "请求过于频繁，已超出必应 API 配额限制（每月1000次免费额度）"
            else:
                error_msg = f"HTTP {e.response.status_code}: {str(e)}"
            
            logger.error(f"必应搜索 HTTP 错误: {error_msg}")
            return ToolResult(
                success=False,
                data=None,
                error=error_msg
            )
        except Exception as e:
            logger.error(f"必应搜索失败: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=f"搜索失败: {str(e)}"
            )
    
    def _parse_results(self, data: Dict, search_type: str) -> List[Dict]:
        """解析必应搜索结果"""
        results = []
        
        if search_type == "web":
            # 网页搜索
            web_pages = data.get("webPages", {}).get("value", [])
            for item in web_pages[:self.max_results]:
                results.append({
                    "title": item.get("name"),
                    "link": item.get("url"),
                    "snippet": item.get("snippet"),
                    "source": item.get("siteName") or self._extract_domain(item.get("url", "")),
                    "date": item.get("dateLastCrawled", "").split("T")[0] if item.get("dateLastCrawled") else None,
                    "position": len(results) + 1
                })
            
            # 添加相关搜索建议
            related_searches = data.get("relatedSearches", {}).get("value", [])
            if related_searches:
                suggestions = [r.get("text", "") for r in related_searches[:5]]
                if suggestions:
                    results.append({
                        "type": "related_searches",
                        "suggestions": suggestions
                    })
            
            # 添加知识卡片（如果有）
            if "entities" in data and data["entities"].get("value"):
                entity = data["entities"]["value"][0]
                results.insert(0, {
                    "type": "knowledge_card",
                    "title": entity.get("name"),
                    "description": entity.get("description"),
                    "image": entity.get("image", {}).get("thumbnailUrl") if entity.get("image") else None,
                    "source": entity.get("contractualRules", [{}])[0].get("source", {}).get("name")
                })
        
        elif search_type == "news":
            # 新闻搜索
            news_items = data.get("value", [])
            for item in news_items[:self.max_results]:
                results.append({
                    "title": item.get("name"),
                    "link": item.get("url"),
                    "snippet": item.get("description"),
                    "source": item.get("provider", [{}])[0].get("name"),
                    "date": item.get("datePublished", "").split("T")[0] if item.get("datePublished") else None,
                    "image": item.get("image", {}).get("thumbnail", {}).get("contentUrl") if item.get("image") else None,
                    "category": item.get("category")
                })
        
        elif search_type == "images":
            # 图片搜索
            images = data.get("value", [])
            for item in images[:self.max_results]:
                results.append({
                    "title": item.get("name"),
                    "link": item.get("contentUrl"),
                    "thumbnail": item.get("thumbnailUrl"),
                    "source": item.get("hostPageDisplayUrl"),
                    "width": item.get("width"),
                    "height": item.get("height")
                })
        
        return results
    
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
