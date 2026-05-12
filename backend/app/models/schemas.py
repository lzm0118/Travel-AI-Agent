"""
Pydantic 数据模型定义
定义所有 API 请求和响应的数据结构
"""
from typing import Any, Dict, List, Optional, Literal, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ==================== 基础枚举 ====================

class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageType(str, Enum):
    """消息类型"""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    STREAM = "stream"


class ToolType(str, Enum):
    """工具类型"""
    AMAP_POI = "amap_poi_search"
    AMAP_WEATHER = "amap_weather"
    WEB_SEARCH = "web_search"
    CALCULATOR = "calculator"
    DATETIME = "datetime"


class AgentType(str, Enum):
    """Agent 类型"""
    TRAVEL = "travel_assistant"
    ITINERARY = "itinerary_planner"
    EMERGENCY = "emergency_handler"


# ==================== 基础模型 ====================

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "success"
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class PaginatedResponse(BaseResponse):
    """分页响应模型"""
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


# ==================== 消息相关模型 ====================

class ToolCall(BaseModel):
    """工具调用定义"""
    id: str
    type: str = "function"
    function: Dict[str, Any] = Field(..., description="包含 name 和 arguments")


class ToolResult(BaseModel):
    """工具调用结果"""
    tool_call_id: str
    role: str = "tool"
    content: str
    is_error: bool = False


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: MessageRole
    content: str
    type: MessageType = MessageType.TEXT
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            return ""
        return v


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID，为空则创建新会话")
    model: Optional[str] = Field(None, description="指定使用的模型")
    stream: bool = Field(default=False, description="是否使用流式响应")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    tools: Optional[List[str]] = Field(None, description="指定要使用的工具列表")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文信息")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    session_id: str
    message: ChatMessage
    usage: Optional[Dict[str, int]] = None
    tools_used: Optional[List[str]] = None
    processing_time: Optional[float] = None


class StreamChunk(BaseModel):
    """流式响应块"""
    session_id: str
    chunk: str
    is_finished: bool = False
    tools_used: Optional[List[str]] = None


# ==================== 用户相关模型 ====================

class UserProfile(BaseModel):
    """用户画像"""
    user_id: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    travel_style: Optional[str] = None  # budget, luxury, adventure, etc.
    preferred_destinations: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


# ==================== 工具相关模型 ====================

class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: List[ToolParameter]
    return_type: str = "string"


class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    tool_name: str
    parameters: Dict[str, Any]


class ToolExecuteResponse(BaseModel):
    """工具执行响应"""
    success: bool
    tool_name: str
    result: Any
    execution_time: float
    error: Optional[str] = None


# ==================== 高德地图工具模型 ====================

class AmapPOISearchRequest(BaseModel):
    """高德 POI 搜索请求"""
    keywords: str = Field(..., description="搜索关键词，如'酒店'、'景点'")
    city: Optional[str] = Field(None, description="城市名，如'北京'")
    location: Optional[str] = Field(None, description="经纬度，如'116.397428,39.90923'")
    radius: Optional[int] = Field(3000, ge=0, le=50000, description="搜索半径，单位米")
    types: Optional[str] = Field(None, description="POI类型编码")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=25)


class AmapPOI(BaseModel):
    """高德 POI 信息"""
    id: str
    name: str
    type: str
    address: Optional[str] = None
    location: str  # 经纬度
    tel: Optional[str] = None
    rating: Optional[float] = None
    cost: Optional[str] = None
    photos: List[str] = Field(default_factory=list)
    distance: Optional[int] = None  # 与搜索中心的距离


class AmapPOISearchResponse(BaseModel):
    """高德 POI 搜索响应"""
    status: str
    info: str
    count: int
    pois: List[AmapPOI]


class AmapWeatherRequest(BaseModel):
    """高德天气查询请求"""
    city: str = Field(..., description="城市名或城市编码")
    extensions: str = Field("all", description="base-实况天气,all-预报天气")


class AmapWeatherData(BaseModel):
    """高德天气数据"""
    city: str
    adcode: str
    province: str
    report_time: str
    weather: str
    temperature: str
    wind_direction: str
    wind_power: str
    humidity: str
    forecast: Optional[List[Dict[str, Any]]] = None


class AmapWeatherResponse(BaseModel):
    """高德天气查询响应"""
    status: str
    info: str
    lives: Optional[List[AmapWeatherData]] = None
    forecasts: Optional[List[AmapWeatherData]] = None


# ==================== 搜索工具模型 ====================

class WebSearchRequest(BaseModel):
    """联网搜索请求"""
    query: str = Field(..., min_length=1, max_length=200)
    num_results: int = Field(10, ge=1, le=20)
    search_type: str = Field("news", description="news, search, places")


class WebSearchResult(BaseModel):
    """搜索结果"""
    title: str
    link: str
    snippet: str
    source: Optional[str] = None
    date: Optional[str] = None


class WebSearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: List[WebSearchResult]
    total_results: int
    search_time: float


# ==================== 行程相关模型 ====================

class ItineraryDay(BaseModel):
    """行程单日规划"""
    day: int
    date: Optional[str] = None
    theme: Optional[str] = None
    morning: List[Dict[str, Any]] = Field(default_factory=list)
    afternoon: List[Dict[str, Any]] = Field(default_factory=list)
    evening: List[Dict[str, Any]] = Field(default_factory=list)
    accommodation: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class ItineraryRequest(BaseModel):
    """行程规划请求"""
    destination: str = Field(..., description="目的地")
    days: int = Field(..., ge=1, le=30, description="天数")
    budget: Optional[str] = Field(None, description="预算级别：budget, medium, luxury")
    travel_style: Optional[str] = Field(None, description="旅行风格：adventure, relaxed, cultural, food")
    interests: List[str] = Field(default_factory=list, description="兴趣点")
    avoid: List[str] = Field(default_factory=list, description="避免的景点或活动")
    start_date: Optional[str] = None
    travelers: int = Field(1, ge=1)
    special_requirements: Optional[str] = None


class Itinerary(BaseModel):
    """完整行程"""
    id: str
    destination: str
    days: int
    total_budget_estimate: Optional[str] = None
    summary: str
    daily_plans: List[ItineraryDay]
    tips: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


# ==================== MCP/A2A 相关模型 ====================

class MCPRequest(BaseModel):
    """MCP 协议请求"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP 协议响应"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class A2ACapability(BaseModel):
    """A2A Agent 能力描述"""
    name: str
    description: str
    version: str
    skills: List[Dict[str, Any]]


class A2AMessage(BaseModel):
    """A2A 消息"""
    message_id: str
    sender: str
    recipient: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    message_type: str = "request"  # request, response, notification


# ==================== WebSocket 相关模型 ====================

class WSMessage(BaseModel):
    """WebSocket 消息"""
    type: str  # chat, ping, pong, error
    payload: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheck(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    uptime: Optional[float] = None
    components: Optional[Dict[str, str]] = None
