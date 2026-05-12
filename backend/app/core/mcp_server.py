"""
MCP (Model Context Protocol) 服务实现
遵循 MCP 协议标准，允许其他 AI 系统与本服务交互
"""
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime
import json
import asyncio

from loguru import logger

from ..tools import list_available_tools, get_all_tools, ToolRegistry
from ..models.schemas import MCPRequest, MCPResponse


class MCPServer:
    """
    MCP 协议服务器
    实现 Model Context Protocol，使 Agent 可以作为 MCP 资源被其他 AI 使用
    """
    
    def __init__(self, server_name: str = "travel-agent-mcp", version: str = "1.0.0"):
        """
        初始化 MCP 服务器
        
        Args:
            server_name: 服务器名称
            version: 版本号
        """
        self.server_name = server_name
        self.version = version
        self.tools = get_all_tools()
        
        logger.info(f"MCP 服务器初始化: {server_name} v{version}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取服务器能力声明
        
        Returns:
            MCP 能力描述
        """
        tool_definitions = []
        for name, tool in self.tools.items():
            tool_definitions.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            })
        
        return {
            "server_info": {
                "name": self.server_name,
                "version": self.version,
                "protocol_version": "2024-11-05"
            },
            "capabilities": {
                "tools": tool_definitions,
                "resources": [
                    {
                        "uri": "travel://destinations",
                        "name": "旅游目的地",
                        "description": "获取热门旅游目的地信息"
                    },
                    {
                        "uri": "travel://tips",
                        "name": "旅游贴士",
                        "description": "获取实用旅游建议"
                    }
                ]
            }
        }
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        处理 MCP 请求
        
        Args:
            request: MCP 请求
            
        Returns:
            MCP 响应
        """
        method = request.method
        params = request.params or {}
        
        logger.info(f"MCP 请求: {method}")
        
        try:
            if method == "initialize":
                return await self._handle_initialize(params)
            
            elif method == "tools/list":
                return await self._handle_tools_list(params)
            
            elif method == "tools/call":
                return await self._handle_tool_call(params)
            
            elif method == "resources/list":
                return await self._handle_resources_list(params)
            
            elif method == "resources/read":
                return await self._handle_resource_read(params)
            
            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": f"未知方法: {method}"
                    }
                )
                
        except Exception as e:
            logger.error(f"MCP 请求处理失败: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": f"内部错误: {str(e)}"
                }
            )
    
    async def _handle_initialize(self, params: Dict) -> MCPResponse:
        """处理初始化请求"""
        return MCPResponse(
            id=params.get("id"),
            result=self.get_capabilities()
        )
    
    async def _handle_tools_list(self, params: Dict) -> MCPResponse:
        """处理工具列表请求"""
        tools = []
        for name, tool in self.tools.items():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters
            })
        
        return MCPResponse(
            id=params.get("id"),
            result={"tools": tools}
        )
    
    async def _handle_tool_call(self, params: Dict) -> MCPResponse:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return MCPResponse(
                id=params.get("id"),
                error={
                    "code": -32602,
                    "message": "缺少工具名称"
                }
            )
        
        tool = self.tools.get(tool_name)
        if not tool:
            return MCPResponse(
                id=params.get("id"),
                error={
                    "code": -32602,
                    "message": f"未知工具: {tool_name}"
                }
            )
        
        try:
            # 执行工具
            result = await tool.run(**arguments)
            
            return MCPResponse(
                id=params.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result.data, ensure_ascii=False) if result.success else result.error
                        }
                    ],
                    "isError": not result.success
                }
            )
            
        except Exception as e:
            return MCPResponse(
                id=params.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"工具执行失败: {str(e)}"
                        }
                    ],
                    "isError": True
                }
            )
    
    async def _handle_resources_list(self, params: Dict) -> MCPResponse:
        """处理资源列表请求"""
        return MCPResponse(
            id=params.get("id"),
            result={
                "resources": [
                    {
                        "uri": "travel://destinations",
                        "name": "热门旅游目的地",
                        "mimeType": "application/json",
                        "description": "中国及全球热门旅游目的地列表"
                    },
                    {
                        "uri": "travel://tips/general",
                        "name": "通用旅游贴士",
                        "mimeType": "text/plain",
                        "description": "出行前准备、注意事项等"
                    }
                ]
            }
        )
    
    async def _handle_resource_read(self, params: Dict) -> MCPResponse:
        """处理资源读取请求"""
        uri = params.get("uri", "")
        
        if uri == "travel://destinations":
            content = {
                "domestic": ["北京", "上海", "杭州", "成都", "西安", "厦门", "云南", "西藏"],
                "international": ["日本", "泰国", "新加坡", "法国", "意大利", "新西兰"]
            }
        elif uri == "travel://tips/general":
            content = """
旅游通用贴士：
1. 出行前检查证件有效期
2. 购买旅游保险
3. 提前了解目的地天气
4. 准备常用药品
5. 下载离线地图
            """
        else:
            return MCPResponse(
                id=params.get("id"),
                error={
                    "code": -32602,
                    "message": f"未知资源: {uri}"
                }
            )
        
        return MCPResponse(
            id=params.get("id"),
            result={
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json" if isinstance(content, dict) else "text/plain",
                        "text": json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content
                    }
                ]
            }
        )
    
    async def process_message(self, message: str) -> str:
        """
        处理 MCP 消息（JSON-RPC 格式）
        
        Args:
            message: JSON-RPC 消息字符串
            
        Returns:
            JSON-RPC 响应字符串
        """
        try:
            data = json.loads(message)
            
            # 处理批量请求
            if isinstance(data, list):
                responses = []
                for req in data:
                    request = MCPRequest(**req)
                    response = await self.handle_request(request)
                    responses.append(response.model_dump())
                return json.dumps(responses, ensure_ascii=False)
            
            # 处理单个请求
            request = MCPRequest(**data)
            response = await self.handle_request(request)
            return json.dumps(response.model_dump(), ensure_ascii=False)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": f"解析错误: {str(e)}"
                },
                "id": None
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"内部错误: {str(e)}"
                },
                "id": None
            }, ensure_ascii=False)


# SSE (Server-Sent Events) 端点处理器
class MCPSSEHandler:
    """MCP SSE 处理器"""
    
    def __init__(self, server: MCPServer):
        self.server = server
        self.connections: Dict[str, Any] = {}
    
    async def handle_connect(self, client_id: str) -> AsyncIterator[str]:
        """处理 SSE 连接"""
        self.connections[client_id] = True
        
        # 发送初始事件
        yield f"event: connected\ndata: {{\"client_id\": \"{client_id}\"}}\n\n"
        
        # 保持连接
        while self.connections.get(client_id):
            await asyncio.sleep(1)
            yield f"event: heartbeat\ndata: {{\"time\": \"{datetime.now().isoformat()}\"}}\n\n"
    
    async def handle_message(self, client_id: str, message: str) -> str:
        """处理客户端消息"""
        return await self.server.process_message(message)
    
    def disconnect(self, client_id: str):
        """断开连接"""
        self.connections.pop(client_id, None)


# 全局 MCP 服务器实例
_mcp_server: Optional[MCPServer] = None
_mcp_sse_handler: Optional[MCPSSEHandler] = None


def get_mcp_server() -> MCPServer:
    """获取 MCP 服务器实例"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server


def get_mcp_sse_handler() -> MCPSSEHandler:
    """获取 MCP SSE 处理器"""
    global _mcp_sse_handler
    if _mcp_sse_handler is None:
        _mcp_sse_handler = MCPSSEHandler(get_mcp_server())
    return _mcp_sse_handler
