"""
高德地图工具集
包含 POI 搜索、天气查询、地理编码等功能
"""
from typing import Any, Dict, List, Optional
import asyncio

import httpx
from loguru import logger

from .base_tool import BaseTool, ToolResult, ToolRegistry
from ..core.config import get_amap_config


class AmapBaseTool(BaseTool):
    """高德地图工具基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        amap_config = get_amap_config()
        self.api_key = self.config.get("key") or amap_config.key
        self.base_url = self.config.get("base_url") or amap_config.base_url
        self.timeout = self.config.get("timeout") or amap_config.timeout
        
        if not self.api_key:
            logger.warning(f"{self.name} 未配置 API Key，工具将不可用")
            self.enabled = False
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        发起高德 API 请求
        
        Args:
            endpoint: API 端点
            params: 请求参数
            
        Returns:
            API 响应数据
        """
        url = f"{self.base_url}/{endpoint}"
        params["key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # 检查高德 API 状态
                if data.get("status") != "1":
                    error_info = data.get("info", "未知错误")
                    raise Exception(f"高德 API 错误: {error_info}")
                
                return data
                
            except httpx.TimeoutException:
                raise Exception("请求高德 API 超时")
            except httpx.HTTPError as e:
                raise Exception(f"HTTP 请求失败: {str(e)}")


@ToolRegistry.register
class AmapPOISearchTool(AmapBaseTool):
    """
    高德地图 POI 搜索工具
    搜索周边的景点、餐厅、酒店等兴趣点
    """
    
    name = "amap_poi_search"
    description = "搜索指定位置周边的 POI（兴趣点），如景点、餐厅、酒店、购物中心等。支持按关键词、城市、类型筛选。"
    version = "1.0.0"
    
    parameters = {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "string",
                "description": "搜索关键词，如'酒店'、'景点'、'餐厅'。多个关键词用'|'分隔"
            },
            "city": {
                "type": "string",
                "description": "搜索城市，如'北京'、'上海'、'杭州'。不指定则全国搜索"
            },
            "location": {
                "type": "string",
                "description": "中心点经纬度，格式为'经度,纬度'，如'116.397428,39.90923'。指定后按周边搜索"
            },
            "radius": {
                "type": "integer",
                "description": "搜索半径，单位米，默认3000米，最大50000米",
                "default": 3000,
                "minimum": 0,
                "maximum": 50000
            },
            "types": {
                "type": "string",
                "description": "POI类型编码，如'010000'表示风景名胜，'050000'表示餐饮服务"
            },
            "page": {
                "type": "integer",
                "description": "页码，从1开始",
                "default": 1,
                "minimum": 1
            },
            "page_size": {
                "type": "integer",
                "description": "每页记录数，最大25",
                "default": 10,
                "minimum": 1,
                "maximum": 25
            }
        },
        "required": ["keywords"]
    }
    
    # POI 类型映射（常用）
    POI_TYPES = {
        "景点": "010000",
        "风景名胜": "010000",
        "公园": "011100",
        "博物馆": "140500",
        "餐厅": "050000",
        "美食": "050000",
        "酒店": "100000",
        "宾馆": "100000",
        "购物": "060000",
        "购物中心": "060100",
        "超市": "060400",
        "交通": "150000",
        "机场": "150100",
        "火车站": "150200",
        "地铁站": "150500"
    }
    
    async def execute(
        self,
        keywords: str,
        city: Optional[str] = None,
        location: Optional[str] = None,
        radius: int = 3000,
        types: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> ToolResult:
        """
        执行 POI 搜索
        
        Args:
            keywords: 搜索关键词
            city: 搜索城市
            location: 中心点经纬度
            radius: 搜索半径
            types: POI类型编码
            page: 页码
            page_size: 每页数量
            
        Returns:
            ToolResult: 搜索结果
        """
        try:
            # 处理类型映射
            if types and types in self.POI_TYPES:
                types = self.POI_TYPES[types]
            
            # 构建请求参数
            params = {
                "keywords": keywords,
                "page": page,
                "offset": page_size,
                "extensions": "all"  # 返回详细信息
            }
            
            if city:
                params["city"] = city
                params["citylimit"] = "true"  # 强制城市限制
            
            if location:
                # 周边搜索模式
                search_type = "around" if location else "text"
                params["location"] = location
                params["radius"] = radius
            else:
                # 关键字搜索模式
                search_type = "text"
            
            if types:
                params["types"] = types
            
            # 发起请求
            endpoint = f"place/{search_type}"
            data = await self._make_request(endpoint, params)
            
            # 解析结果
            pois = data.get("pois", [])
            parsed_pois = self._parse_pois(pois, location)
            
            result_data = {
                "total": int(data.get("count", 0)),
                "count": len(parsed_pois),
                "page": page,
                "page_size": page_size,
                "pois": parsed_pois
            }
            
            logger.info(f"POI 搜索完成: {keywords}, 找到 {len(parsed_pois)} 个结果")
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "keywords": keywords,
                    "city": city,
                    "search_type": search_type
                }
            )
            
        except Exception as e:
            logger.error(f"POI 搜索失败: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    def _parse_pois(
        self, 
        pois: List[Dict], 
        center_location: Optional[str] = None
    ) -> List[Dict]:
        """解析 POI 数据"""
        parsed = []
        
        for poi in pois:
            parsed_poi = {
                "id": poi.get("id"),
                "name": poi.get("name"),
                "type": poi.get("type"),
                "address": poi.get("address"),
                "location": poi.get("location"),
                "tel": poi.get("tel"),
                "rating": self._extract_rating(poi),
                "photos": self._extract_photos(poi),
                "business_hours": poi.get("business_hours"),
                "cost": poi.get("average_cost"),
                "distance": poi.get("distance")
            }
            parsed.append(parsed_poi)
        
        return parsed
    
    def _extract_rating(self, poi: Dict) -> Optional[float]:
        """提取评分信息"""
        biz_ext = poi.get("biz_ext", {})
        rating_str = biz_ext.get("rating")
        if rating_str:
            try:
                return float(rating_str)
            except:
                pass
        return None
    
    def _extract_photos(self, poi: Dict) -> List[str]:
        """提取图片 URL"""
        photos = poi.get("photos", [])
        return [p.get("url") for p in photos if p.get("url")]


@ToolRegistry.register
class AmapWeatherTool(AmapBaseTool):
    """
    高德地图天气查询工具
    查询指定城市的实时天气和预报
    """
    
    name = "amap_weather"
    description = "查询指定城市的天气信息，包括实时天气（温度、湿度、风向风力）和未来3天天气预报。支持中国所有城市。"
    version = "1.0.0"
    
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，如'北京'、'上海'、'杭州'，或城市编码如'110000'"
            },
            "extensions": {
                "type": "string",
                "description": "返回内容类型：base-仅实况天气，all-实况+预报天气",
                "enum": ["base", "all"],
                "default": "all"
            }
        },
        "required": ["city"]
    }
    
    async def execute(
        self,
        city: str,
        extensions: str = "all"
    ) -> ToolResult:
        """
        执行天气查询
        
        Args:
            city: 城市名或城市编码
            extensions: 返回内容类型
            
        Returns:
            ToolResult: 天气信息
        """
        try:
            params = {
                "city": city,
                "extensions": extensions
            }
            
            data = await self._make_request("weather/weatherInfo", params)
            
            # 解析结果
            result = {
                "city": city,
                "realtime": None,
                "forecast": []
            }
            
            # 实况天气
            lives = data.get("lives", [])
            if lives:
                live = lives[0]
                result["realtime"] = {
                    "weather": live.get("weather"),
                    "temperature": live.get("temperature"),
                    "wind_direction": live.get("winddirection"),
                    "wind_power": live.get("windpower"),
                    "humidity": live.get("humidity"),
                    "report_time": live.get("reporttime"),
                    "province": live.get("province")
                }
            
            # 预报天气
            if extensions == "all":
                forecasts = data.get("forecasts", [])
                if forecasts:
                    forecast_data = forecasts[0]
                    casts = forecast_data.get("casts", [])
                    result["forecast"] = [
                        {
                            "date": c.get("date"),
                            "week": c.get("week"),
                            "day_weather": c.get("dayweather"),
                            "night_weather": c.get("nightweather"),
                            "day_temp": c.get("daytemp"),
                            "night_temp": c.get("nighttemp"),
                            "day_wind": c.get("daywind"),
                            "night_wind": c.get("nightwind"),
                            "day_power": c.get("daypower"),
                            "night_power": c.get("nightpower")
                        }
                        for c in casts
                    ]
            
            logger.info(f"天气查询完成: {city}")
            
            return ToolResult(
                success=True,
                data=result,
                metadata={"extensions": extensions}
            )
            
        except Exception as e:
            logger.error(f"天气查询失败: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )


@ToolRegistry.register
class AmapGeocodeTool(AmapBaseTool):
    """
    高德地理编码工具
    地址转坐标（地理编码）和坐标转地址（逆地理编码）
    """
    
    name = "amap_geocode"
    description = "地址与经纬度坐标相互转换。支持将具体地址转换为经纬度坐标（地理编码），或将经纬度转换为详细地址（逆地理编码）。"
    version = "1.0.0"
    
    parameters = {
        "type": "object",
        "properties": {
            "address": {
                "type": "string",
                "description": "具体地址，用于地理编码。如'北京市朝阳区望京街9号'"
            },
            "location": {
                "type": "string",
                "description": "经纬度坐标，用于逆地理编码。格式'经度,纬度'，如'116.481488,39.990464'"
            },
            "city": {
                "type": "string",
                "description": "查询城市，用于提高地理编码准确性"
            }
        },
        "anyOf": [
            {"required": ["address"]},
            {"required": ["location"]}
        ]
    }
    
    async def execute(
        self,
        address: Optional[str] = None,
        location: Optional[str] = None,
        city: Optional[str] = None
    ) -> ToolResult:
        """
        执行地理编码/逆地理编码
        
        Args:
            address: 地址（地理编码）
            location: 坐标（逆地理编码）
            city: 城市
            
        Returns:
            ToolResult: 编码结果
        """
        try:
            if address:
                # 地理编码
                params = {"address": address}
                if city:
                    params["city"] = city
                
                data = await self._make_request("geocode/geo", params)
                geocodes = data.get("geocodes", [])
                
                if not geocodes:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"无法解析地址: {address}"
                    )
                
                result = {
                    "type": "geocode",
                    "input": address,
                    "locations": [
                        {
                            "formatted_address": g.get("formatted_address"),
                            "location": g.get("location"),
                            "province": g.get("province"),
                            "city": g.get("city"),
                            "district": g.get("district"),
                            "street": g.get("street"),
                            "number": g.get("number"),
                            "adcode": g.get("adcode"),
                            "level": g.get("level")
                        }
                        for g in geocodes
                    ]
                }
                
            else:
                # 逆地理编码
                params = {"location": location}
                
                data = await self._make_request("geocode/regeo", params)
                regeocode = data.get("regeocode", {})
                
                if not regeocode:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"无法解析坐标: {location}"
                    )
                
                address_component = regeocode.get("addressComponent", {})
                
                result = {
                    "type": "regeocode",
                    "input": location,
                    "formatted_address": regeocode.get("formatted_address"),
                    "province": address_component.get("province"),
                    "city": address_component.get("city"),
                    "district": address_component.get("district"),
                    "street": address_component.get("street"),
                    "number": address_component.get("streetNumber"),
                    "adcode": address_component.get("adcode"),
                    "township": address_component.get("township")
                }
            
            return ToolResult(success=True, data=result)
            
        except Exception as e:
            logger.error(f"地理编码失败: {str(e)}")
            return ToolResult(success=False, data=None, error=str(e))
