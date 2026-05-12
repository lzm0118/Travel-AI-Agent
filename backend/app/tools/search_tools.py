"""
联网搜索工具
支持多种搜索提供商：Serper, Bing, Google 等
"""
from typing import Any, Dict, List, Optional
import asyncio

import httpx
from loguru import logger

from .base_tool import BaseTool, ToolResult, ToolRegistry
from ..core.config import get_search_config


class WebSearchTool(BaseTool):
    """联网搜索工具基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        search_config = get_search_config()
        self.api_key = self.config.get("api_key") or search_config.api_key
        self.timeout = self.config.get("timeout") or search_config.timeout
        self.max_results = self.config.get("max_results") or search_config.max_results
        
        if not self.api_key:
            logger.warning(f"{self.name} 未配置 API Key，工具将不可用")
            self.enabled = False


# Serper 搜索工具（可选，需要 API Key）
# 默认不使用，可通过配置文件启用
class SerperSearchTool(WebSearchTool):
    """
    Serper (Google Search API) 搜索工具
    通过 Serper API 执行 Google 搜索
    """
    
    name = "serper_search"
    description = "在互联网上搜索实时信息，获取最新旅游资讯、景点评价、当地新闻等。使用 Google 搜索引擎。"
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
                "description": "返回结果数量，默认10条",
                "default": 10,
                "minimum": 1,
                "maximum": 20
            },
            "search_type": {
                "type": "string",
                "description": "搜索类型：search-网页搜索, news-新闻搜索, places-地点搜索",
                "enum": ["search", "news", "places"],
                "default": "search"
            },
            "location": {
                "type": "string",
                "description": "搜索地点偏好（可选），如'China'"
            },
            "time_range": {
                "type": "string",
                "description": "时间范围：d-过去24小时, w-过去一周, m-过去一月, y-过去一年",
                "enum": ["d", "w", "m", "y"],
                "default": None
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://google.serper.dev"
    
    async def execute(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
        location: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> ToolResult:
        """
        执行搜索
        
        Args:
            query: 搜索关键词
            num_results: 结果数量
            search_type: 搜索类型
            location: 地点偏好
            time_range: 时间范围
            
        Returns:
            ToolResult: 搜索结果
        """
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": query,
                "num": min(num_results, 20)
            }
            
            if location:
                payload["gl"] = location
            if time_range:
                payload["tbs"] = f"qdr:{time_range}"
            
            # 构建端点
            endpoint = f"{self.base_url}/{search_type}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            # 解析结果
            parsed_results = self._parse_results(data, search_type)
            
            result_data = {
                "query": query,
                "search_type": search_type,
                "total_results": data.get("searchInformation", {}).get("totalResults", "0"),
                "results": parsed_results
            }
            
            logger.info(f"搜索完成: {query}, 找到 {len(parsed_results)} 条结果")
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "provider": "serper",
                    "search_type": search_type
                }
            )
            
        except httpx.TimeoutException:
            logger.error("搜索请求超时")
            return ToolResult(
                success=False,
                data=None,
                error="搜索请求超时，请稍后重试"
            )
        except httpx.HTTPError as e:
            logger.error(f"搜索 HTTP 错误: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=f"搜索服务暂时不可用: {str(e)}"
            )
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    def _parse_results(self, data: Dict, search_type: str) -> List[Dict]:
        """解析搜索结果"""
        results = []
        
        if search_type == "search":
            # 解析普通搜索
            organic = data.get("organic", [])
            for item in organic[:self.max_results]:
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": item.get("source"),
                    "date": item.get("date"),
                    "position": item.get("position")
                })
            
            # 添加知识图谱信息（如果有）
            knowledge_graph = data.get("knowledgeGraph")
            if knowledge_graph:
                results.insert(0, {
                    "title": knowledge_graph.get("title"),
                    "type": "knowledge_graph",
                    "description": knowledge_graph.get("description"),
                    "attributes": knowledge_graph.get("attributes", {})
                })
                
        elif search_type == "news":
            # 解析新闻搜索
            news = data.get("news", [])
            for item in news[:self.max_results]:
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": item.get("source"),
                    "date": item.get("date"),
                    "image": item.get("imageUrl")
                })
                
        elif search_type == "places":
            # 解析地点搜索
            places = data.get("places", [])
            for item in places[:self.max_results]:
                results.append({
                    "title": item.get("title"),
                    "address": item.get("address"),
                    "rating": item.get("ratingValue"),
                    "reviews": item.get("reviewCount"),
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude")
                })
        
        return results


@ToolRegistry.register
class CalculatorTool(BaseTool):
    """
    计算器工具
    执行基础数学运算，如计算旅行费用、汇率转换等
    """
    
    name = "calculator"
    description = "执行数学计算，如费用计算、汇率换算、时间计算等。支持加减乘除、百分比、幂运算等。"
    version = "1.0.0"
    
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如'100 * 7.2'、'500 / 3'、'(100 + 200) * 0.8'"
            }
        },
        "required": ["expression"]
    }
    
    async def execute(self, expression: str) -> ToolResult:
        """
        安全地执行数学表达式
        
        Args:
            expression: 数学表达式
            
        Returns:
            ToolResult: 计算结果
        """
        try:
            # 清理表达式
            cleaned = self._sanitize_expression(expression)
            
            # 安全求值
            result = self._safe_eval(cleaned)
            
            return ToolResult(
                success=True,
                data={
                    "expression": expression,
                    "result": result,
                    "formatted": self._format_result(result)
                }
            )
            
        except Exception as e:
            logger.error(f"计算失败: {expression}, 错误: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=f"计算错误: {str(e)}"
            )
    
    def _sanitize_expression(self, expr: str) -> str:
        """清理表达式，只允许安全字符"""
        allowed_chars = set("0123456789+-*/().,^% ")
        cleaned = "".join(c for c in expr if c in allowed_chars)
        
        # 替换 ^ 为 **
        cleaned = cleaned.replace("^", "**")
        
        # 替换 , 为空（处理千位分隔符）
        cleaned = cleaned.replace(",", "")
        
        return cleaned.strip()
    
    def _safe_eval(self, expr: str) -> float:
        """安全地求值表达式"""
        # 使用 eval 但限制可用名称
        safe_dict = {
            "__builtins__": {},
            "abs": abs,
            "max": max,
            "min": min,
            "round": round,
            "pow": pow
        }
        
        try:
            result = eval(expr, safe_dict)
            return float(result)
        except:
            raise ValueError("无效的数学表达式")
    
    def _format_result(self, result: float) -> str:
        """格式化结果"""
        if result == int(result):
            return str(int(result))
        return f"{result:.2f}"


@ToolRegistry.register
class DateTimeTool(BaseTool):
    """
    日期时间工具
    获取当前日期时间、计算日期差、格式化日期等
    """
    
    name = "datetime"
    description = "获取当前日期时间信息，计算日期差（如旅行天数），格式化日期显示。"
    version = "1.0.0"
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["now", "days_between", "add_days", "format"],
                "default": "now"
            },
            "date1": {
                "type": "string",
                "description": "第一个日期，格式'YYYY-MM-DD'，用于 days_between"
            },
            "date2": {
                "type": "string",
                "description": "第二个日期，格式'YYYY-MM-DD'，用于 days_between"
            },
            "date": {
                "type": "string",
                "description": "基准日期，格式'YYYY-MM-DD'，用于 add_days"
            },
            "days": {
                "type": "integer",
                "description": "天数，用于 add_days"
            },
            "format": {
                "type": "string",
                "description": "日期格式字符串",
                "default": "%Y-%m-%d %H:%M:%S"
            }
        },
        "required": ["action"]
    }
    
    async def execute(
        self,
        action: str = "now",
        date1: Optional[str] = None,
        date2: Optional[str] = None,
        date: Optional[str] = None,
        days: int = 0,
        format: str = "%Y-%m-%d %H:%M:%S"
    ) -> ToolResult:
        """
        执行日期时间操作
        
        Args:
            action: 操作类型
            date1, date2: 日期字符串
            date: 基准日期
            days: 天数
            format: 格式字符串
            
        Returns:
            ToolResult: 操作结果
        """
        from datetime import datetime, timedelta
        
        try:
            if action == "now":
                now = datetime.now()
                result = {
                    "datetime": now.strftime(format),
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "timestamp": int(now.timestamp()),
                    "weekday": now.strftime("%A"),
                    "weekday_cn": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
                }
                
            elif action == "days_between":
                if not date1 or not date2:
                    raise ValueError("days_between 需要 date1 和 date2 参数")
                
                d1 = datetime.strptime(date1, "%Y-%m-%d")
                d2 = datetime.strptime(date2, "%Y-%m-%d")
                delta = abs((d2 - d1).days)
                
                result = {
                    "days": delta,
                    "date1": date1,
                    "date2": date2,
                    "is_future": d2 > d1
                }
                
            elif action == "add_days":
                if not date:
                    base = datetime.now()
                else:
                    base = datetime.strptime(date, "%Y-%m-%d")
                
                new_date = base + timedelta(days=days)
                result = {
                    "original_date": base.strftime("%Y-%m-%d"),
                    "days_added": days,
                    "new_date": new_date.strftime("%Y-%m-%d"),
                    "weekday": new_date.strftime("%A")
                }
                
            elif action == "format":
                now = datetime.now()
                result = {
                    "formatted": now.strftime(format)
                }
            else:
                raise ValueError(f"未知的操作类型: {action}")
            
            return ToolResult(
                success=True,
                data=result,
                metadata={"action": action}
            )
            
        except Exception as e:
            logger.error(f"日期操作失败: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
