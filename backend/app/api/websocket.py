"""
WebSocket 接口
支持实时双向通信
"""
from typing import Dict, Set
import json

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from ..models.schemas import WSMessage
from ..agents import get_travel_agent
from ..memory import get_session_memory


class ConnectionManager:
    """
    WebSocket 连接管理器
    管理所有活跃的 WebSocket 连接
    """
    
    def __init__(self):
        """初始化连接管理器"""
        # 存储连接: {session_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 按用户分组: {user_id: Set[session_id]}
        self.user_connections: Dict[str, Set[str]] = {}
        
        logger.info("WebSocket 连接管理器初始化完成")
    
    async def connect(
        self, 
        websocket: WebSocket, 
        session_id: str,
        user_id: str = None
    ):
        """
        接受新连接
        
        Args:
            websocket: WebSocket 对象
            session_id: 会话ID
            user_id: 用户ID（可选）
        """
        await websocket.accept()
        
        self.active_connections[session_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(session_id)
        
        logger.info(f"WebSocket 连接建立: {session_id} (user: {user_id})")
        
        # 发送连接成功消息
        await self.send_message(
            session_id,
            {
                "type": "connected",
                "payload": {
                    "session_id": session_id,
                    "message": "连接成功"
                }
            }
        )
    
    def disconnect(self, session_id: str, user_id: str = None):
        """
        断开连接
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（可选）
        """
        self.active_connections.pop(session_id, None)
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(session_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket 连接断开: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict):
        """
        发送消息给指定会话
        
        Args:
            session_id: 会话ID
            message: 消息内容
        """
        websocket = self.active_connections.get(session_id)
        
        if websocket:
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"发送消息失败: {session_id}, {e}")
    
    async def broadcast(self, message: Dict, exclude: str = None):
        """
        广播消息给所有连接
        
        Args:
            message: 消息内容
            exclude: 排除的会话ID
        """
        for session_id, websocket in self.active_connections.items():
            if session_id != exclude:
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"广播消息失败: {session_id}, {e}")
    
    async def send_to_user(self, user_id: str, message: Dict):
        """
        发送消息给用户的所有连接
        
        Args:
            user_id: 用户ID
            message: 消息内容
        """
        session_ids = self.user_connections.get(user_id, set())
        
        for session_id in session_ids:
            await self.send_message(session_id, message)
    
    def is_connected(self, session_id: str) -> bool:
        """检查会话是否连接"""
        return session_id in self.active_connections


# 全局连接管理器实例
manager = ConnectionManager()


async def handle_websocket(
    websocket: WebSocket,
    session_id: str,
    user_id: str = None
):
    """
    处理 WebSocket 连接
    
    支持的消息类型：
    - chat: 聊天消息
    - ping: 心跳检测
    - typing: 正在输入
    - tool_request: 工具调用请求
    
    Args:
        websocket: WebSocket 对象
        session_id: 会话ID
        user_id: 用户ID
    """
    await manager.connect(websocket, session_id, user_id)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "chat")
                
                if msg_type == "ping":
                    # 心跳响应
                    await manager.send_message(
                        session_id,
                        {"type": "pong", "timestamp": message.get("timestamp")}
                    )
                
                elif msg_type == "chat":
                    # 处理聊天消息
                    await handle_chat_message(
                        websocket,
                        session_id,
                        user_id,
                        message.get("payload", {})
                    )
                
                elif msg_type == "typing":
                    # 正在输入指示（可以广播给其他参与者）
                    pass
                
                elif msg_type == "tool_request":
                    # 直接工具调用请求
                    await handle_tool_request(
                        session_id,
                        message.get("payload", {})
                    )
                
                else:
                    await manager.send_message(
                        session_id,
                        {
                            "type": "error",
                            "payload": {"message": f"未知消息类型: {msg_type}"}
                        }
                    )
                    
            except json.JSONDecodeError:
                await manager.send_message(
                    session_id,
                    {
                        "type": "error",
                        "payload": {"message": "无效的 JSON 格式"}
                    }
                )
            
    except WebSocketDisconnect:
        manager.disconnect(session_id, user_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {session_id}, {e}")
        manager.disconnect(session_id, user_id)


async def handle_chat_message(
    websocket: WebSocket,
    session_id: str,
    user_id: str,
    payload: Dict
):
    """
    处理聊天消息
    
    Args:
        websocket: WebSocket 对象
        session_id: 会话ID
        user_id: 用户ID
        payload: 消息内容
    """
    user_message = payload.get("message", "")
    stream = payload.get("stream", True)
    
    if not user_message:
        await manager.send_message(
            session_id,
            {
                "type": "error",
                "payload": {"message": "消息不能为空"}
            }
        )
        return
    
    # 发送"正在处理"指示
    await manager.send_message(
        session_id,
        {
            "type": "processing",
            "payload": {"status": "thinking"}
        }
    )
    
    try:
        if stream:
            # 流式响应
            agent = get_travel_agent()
            
            full_response = ""
            async for chunk in agent.stream_chat(
                message=user_message,
                session_id=session_id,
                user_id=user_id
            ):
                # 发送流式块
                await manager.send_message(
                    session_id,
                    {
                        "type": "stream_chunk",
                        "payload": chunk
                    }
                )
                
                if not chunk.get("is_finished"):
                    full_response += chunk.get("chunk", "")
            
            # 发送完成消息
            await manager.send_message(
                session_id,
                {
                    "type": "stream_complete",
                    "payload": {
                        "session_id": session_id,
                        "full_message": full_response
                    }
                }
            )
        
        else:
            # 非流式响应
            result = await chat_with_agent(
                message=user_message,
                session_id=session_id,
                user_id=user_id
            )
            
            await manager.send_message(
                session_id,
                {
                    "type": "chat_response",
                    "payload": {
                        "message": result.get("message", ""),
                        "tools_used": result.get("tools_used", []),
                        "session_id": session_id
                    }
                }
            )
    
    except Exception as e:
        logger.error(f"处理聊天消息失败: {e}")
        await manager.send_message(
            session_id,
            {
                "type": "error",
                "payload": {"message": f"处理失败: {str(e)}"}
            }
        )


async def handle_tool_request(session_id: str, payload: Dict):
    """
    处理工具调用请求
    
    Args:
        session_id: 会话ID
        payload: 请求内容
    """
    tool_name = payload.get("tool_name")
    parameters = payload.get("parameters", {})
    
    from ..tools import get_tool
    
    tool = get_tool(tool_name)
    
    if not tool:
        await manager.send_message(
            session_id,
            {
                "type": "tool_error",
                "payload": {"message": f"工具不存在: {tool_name}"}
            }
        )
        return
    
    try:
        result = await tool.run(**parameters)
        
        await manager.send_message(
            session_id,
            {
                "type": "tool_result",
                "payload": {
                    "tool_name": tool_name,
                    "success": result.success,
                    "result": result.data,
                    "error": result.error,
                    "execution_time": result.execution_time
                }
            }
        )
    
    except Exception as e:
        await manager.send_message(
            session_id,
            {
                "type": "tool_error",
                "payload": {
                    "tool_name": tool_name,
                    "error": str(e)
                }
            }
        )
