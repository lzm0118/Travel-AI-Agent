"""
API 路由定义
包含 RESTful API 和 WebSocket 端点
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
import json

from loguru import logger

from ..models.schemas import (
    ChatRequest, ChatResponse, StreamChunk,
    ToolExecuteRequest, ToolExecuteResponse,
    AmapPOISearchRequest, AmapWeatherRequest,
    WebSearchRequest, BaseResponse, HealthCheck
)
from ..agents import get_travel_agent, chat_with_agent
from ..tools import get_all_tools, get_tool, list_available_tools
from ..memory import get_session_memory, get_memory_store, get_user_profile_manager
from ..core import get_mcp_server, get_a2a_server


# 创建路由器
router = APIRouter(prefix="/api", tags=["api"])


# ==================== 健康检查 ====================

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """健康检查端点"""
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(),
        components={
            "llm": "ok",
            "tools": "ok",
            "memory": "ok"
        }
    )


# ==================== 对话接口 ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    发送对话消息
    
    - **message**: 用户消息内容
    - **session_id**: 会话ID（可选，为空则创建新会话）
    - **model**: 指定模型（可选）
    - **stream**: 是否流式响应（当前仅支持 false）
    """
    try:
        # 生成或验证 session_id
        session_id = request.session_id or str(uuid.uuid4())
        
        # 调用 Agent
        start_time = datetime.now()
        result = await chat_with_agent(
            message=request.message,
            session_id=session_id,
            user_id=request.context.get("user_id") if request.context else None
        )
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "未知错误"))
        
        return ChatResponse(
            session_id=session_id,
            message={
                "role": "assistant",
                "content": result.get("message", ""),
                "type": "text"
            },
            tools_used=result.get("tools_used", []),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"对话请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口
    
    使用 Server-Sent Events (SSE) 返回流式响应
    """
    async def event_generator():
        session_id = request.session_id or str(uuid.uuid4())
        agent = get_travel_agent()
        
        async for chunk in agent.stream_chat(
            message=request.message,
            session_id=session_id,
            user_id=request.context.get("user_id") if request.context else None
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ==================== 会话管理 ====================

@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100)
):
    """获取会话历史消息"""
    memory = get_memory_store().get(session_id)
    
    if not memory:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    messages = memory.get_messages(last_n=limit)
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in messages
        ],
        "summary": memory.get_summary()
    }


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """清空会话历史"""
    memory = get_memory_store().get(session_id)
    
    if memory:
        memory.clear()
        return {"success": True, "message": "会话已清空"}
    
    return {"success": False, "message": "会话不存在"}


# ==================== 工具接口 ====================

@router.get("/tools", response_model=BaseResponse)
async def list_tools():
    """列出所有可用工具"""
    tools = list_available_tools()
    
    return BaseResponse(
        success=True,
        data={
            "count": len(tools),
            "tools": [
                {
                    "name": name,
                    "description": desc,
                    "enabled": True
                }
                for name, desc in tools.items()
            ]
        }
    )


@router.post("/tools/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest):
    """
    执行指定工具
    
    - **tool_name**: 工具名称
    - **parameters**: 工具参数
    """
    tool = get_tool(request.tool_name)
    
    if not tool:
        raise HTTPException(
            status_code=404, 
            detail=f"工具不存在: {request.tool_name}"
        )
    
    try:
        import asyncio
        from datetime import datetime
        
        start_time = datetime.now()
        result = await tool.run(**request.parameters)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return ToolExecuteResponse(
            success=result.success,
            tool_name=request.tool_name,
            result=result.data,
            execution_time=execution_time,
            error=result.error
        )
        
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 高德地图工具快捷接口 ====================

@router.post("/tools/amap/poi-search", response_model=BaseResponse)
async def amap_poi_search(request: AmapPOISearchRequest):
    """高德地图 POI 搜索"""
    tool = get_tool("amap_poi_search")
    
    if not tool:
        raise HTTPException(status_code=503, detail="POI 搜索服务不可用")
    
    try:
        result = await tool.run(
            keywords=request.keywords,
            city=request.city,
            location=request.location,
            radius=request.radius,
            types=request.types,
            page=request.page,
            page_size=request.page_size
        )
        
        return BaseResponse(
            success=result.success,
            data=result.data,
            message="搜索成功" if result.success else result.error
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/amap/weather", response_model=BaseResponse)
async def amap_weather(city: str, extensions: str = "all"):
    """高德地图天气查询"""
    tool = get_tool("amap_weather")
    
    if not tool:
        raise HTTPException(status_code=503, detail="天气查询服务不可用")
    
    try:
        result = await tool.run(city=city, extensions=extensions)
        
        return BaseResponse(
            success=result.success,
            data=result.data,
            message="查询成功" if result.success else result.error
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 联网搜索接口 ====================

@router.post("/tools/web-search", response_model=BaseResponse)
async def web_search(request: WebSearchRequest):
    """联网搜索"""
    tool = get_tool("web_search")
    
    if not tool:
        raise HTTPException(status_code=503, detail="搜索服务不可用")
    
    try:
        result = await tool.run(
            query=request.query,
            num_results=request.num_results,
            search_type=request.search_type
        )
        
        return BaseResponse(
            success=result.success,
            data=result.data,
            message="搜索成功" if result.success else result.error
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 用户画像接口 ====================

@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """获取用户画像"""
    profile_mgr = get_user_profile_manager()
    profile = await profile_mgr.get_profile(user_id)
    
    return {
        "user_id": profile.user_id,
        "preferences": profile.preferences,
        "travel_style": profile.travel_style,
        "preferred_destinations": profile.preferred_destinations,
        "dietary_restrictions": profile.dietary_restrictions,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat()
    }


@router.post("/users/{user_id}/profile")
async def update_user_profile(user_id: str, updates: Dict[str, Any]):
    """更新用户画像"""
    profile_mgr = get_user_profile_manager()
    profile = await profile_mgr.update_profile(user_id, updates)
    
    return {
        "success": True,
        "user_id": profile.user_id,
        "updated_at": profile.updated_at.isoformat()
    }


# ==================== MCP 协议接口 ====================

@router.post("/mcp/invoke", response_model=BaseResponse)
async def mcp_invoke(request: Dict[str, Any]):
    """MCP 协议调用接口（用于 HTTP 传输）"""
    server = get_mcp_server()
    
    try:
        response_json = await server.process_message(json.dumps(request))
        response_data = json.loads(response_json)
        
        return BaseResponse(
            success="error" not in response_data,
            data=response_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/sse")
async def mcp_sse():
    """MCP SSE (Server-Sent Events) 端点"""
    from fastapi.responses import StreamingResponse
    import asyncio
    
    async def event_stream():
        handler = get_mcp_server()
        client_id = str(uuid.uuid4())
        
        # 发送连接确认
        yield f"event: connected\ndata: {{\"client_id\": \"{client_id}\"}}\n\n"
        
        # 保持连接，定期发送心跳
        while True:
            await asyncio.sleep(30)
            yield f"event: heartbeat\ndata: {{\"time\": \"{datetime.now().isoformat()}\"}}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


# ==================== A2A 协议接口 ====================

@router.get("/a2a/agents")
async def list_a2a_agents():
    """列出所有 A2A Agent"""
    server = get_a2a_server()
    return {
        "agents": server.list_agents()
    }


@router.post("/a2a/send")
async def a2a_send_message(request: Dict[str, Any]):
    """发送 A2A 消息"""
    from ..models.schemas import A2AMessage
    from ..core.a2a_server import A2AMessageType
    
    server = get_a2a_server()
    
    message = A2AMessage(
        message_id=str(uuid.uuid4()),
        sender=request.get("from_agent", "system"),
        recipient=request.get("to_agent"),
        content=request.get("content", {}),
        message_type=request.get("message_type", "request")
    )
    
    response = await server.send_message(message)
    
    if response:
        return {
            "success": True,
            "response": {
                "sender": response.sender,
                "content": response.content,
                "timestamp": response.timestamp.isoformat()
            }
        }
    
    return {"success": False, "error": "未收到响应"}


@router.post("/a2a/task")
async def a2a_create_task(request: Dict[str, Any]):
    """创建 A2A 任务"""
    server = get_a2a_server()
    
    result = await server.dispatch_task(request)
    return result


# ==================== 根路由 ====================

@router.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "智能旅游助手 API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "tools": "/api/tools",
            "health": "/api/health"
        },
        "docs": "/docs"
    }
