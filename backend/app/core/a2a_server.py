"""
A2A (Agent-to-Agent) 协议服务实现
支持多 Agent 之间的通信和协作
"""
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from loguru import logger

from ..agents import get_travel_agent, chat_with_agent
from ..models.schemas import A2AMessage, A2ACapability


class A2AMessageType(Enum):
    """A2A 消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    TASK = "task"
    HANDOFF = "handoff"  # 任务交接


class A2ATaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class A2ATask:
    """A2A 任务定义"""
    task_id: str
    task_type: str
    status: A2ATaskStatus
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    result: Optional[Dict] = None
    parent_task_id: Optional[str] = None


class A2AAgent:
    """
    A2A Agent 基类
    可与其他 Agent 通信协作
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        capabilities: List[str],
        description: str = ""
    ):
        """
        初始化 A2A Agent
        
        Args:
            agent_id: Agent 唯一标识
            name: Agent 名称
            capabilities: 能力列表
            description: 描述
        """
        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities
        self.description = description
        
        # 消息处理器
        self._message_handlers: Dict[A2AMessageType, List[Callable]] = {}
        
        # 任务处理器
        self._task_handlers: Dict[str, Callable] = {}
        
        logger.info(f"A2A Agent 初始化: {name} ({agent_id})")
    
    def get_capability(self) -> A2ACapability:
        """获取能力描述"""
        return A2ACapability(
            name=self.name,
            description=self.description,
            version="1.0.0",
            skills=[
                {
                    "id": cap,
                    "name": cap,
                    "description": f"能力: {cap}"
                }
                for cap in self.capabilities
            ]
        )
    
    def register_message_handler(
        self, 
        message_type: A2AMessageType, 
        handler: Callable
    ):
        """注册消息处理器"""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self._task_handlers[task_type] = handler
    
    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        处理传入消息
        
        Args:
            message: A2A 消息
            
        Returns:
            响应消息（可选）
        """
        msg_type = A2AMessageType(message.message_type)
        handlers = self._message_handlers.get(msg_type, [])
        
        for handler in handlers:
            try:
                result = await handler(message)
                if result:
                    return result
            except Exception as e:
                logger.error(f"消息处理失败: {e}")
        
        return None
    
    async def send_message(
        self,
        to_agent: str,
        content: Dict[str, Any],
        message_type: A2AMessageType = A2AMessageType.REQUEST
    ) -> A2AMessage:
        """
        发送消息
        
        Args:
            to_agent: 目标 Agent ID
            content: 消息内容
            message_type: 消息类型
            
        Returns:
            发送的消息
        """
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient=to_agent,
            content=content,
            message_type=message_type.value
        )
        
        logger.debug(f"发送消息: {self.agent_id} -> {to_agent}")
        return message


class TravelA2AAgent(A2AAgent):
    """
    旅游助手 A2A Agent
    继承旅游助手能力和 A2A 通信能力
    """
    
    def __init__(self):
        super().__init__(
            agent_id="travel-assistant-001",
            name="智能旅游助手",
            capabilities=[
                "itinerary_planning",
                "poi_search",
                "weather_query",
                "travel_advice",
                "emergency_handling"
            ],
            description="专业的旅游助手，提供行程规划、景点推荐、天气查询等服务"
        )
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认消息处理器"""
        
        async def handle_travel_request(message: A2AMessage) -> A2AMessage:
            """处理旅游请求"""
            content = message.content
            user_query = content.get("query", "")
            session_id = content.get("session_id", str(uuid.uuid4()))
            
            # 调用旅游助手 Agent
            result = await chat_with_agent(user_query, session_id)
            
            return A2AMessage(
                message_id=str(uuid.uuid4()),
                sender=self.agent_id,
                recipient=message.sender,
                content={
                    "response": result.get("message", ""),
                    "tools_used": result.get("tools_used", []),
                    "session_id": session_id
                },
                message_type=A2AMessageType.RESPONSE.value
            )
        
        async def handle_poi_search(message: A2AMessage) -> A2AMessage:
            """处理 POI 搜索请求"""
            from ..tools import get_tool
            
            content = message.content
            keywords = content.get("keywords", "")
            city = content.get("city")
            
            tool = get_tool("amap_poi_search")
            if tool:
                result = await tool.run(keywords=keywords, city=city)
                
                return A2AMessage(
                    message_id=str(uuid.uuid4()),
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={
                        "results": result.data if result.success else None,
                        "error": result.error
                    },
                    message_type=A2AMessageType.RESPONSE.value
                )
            
            return None
        
        # 注册处理器
        self.register_message_handler(A2AMessageType.REQUEST, handle_travel_request)
        self.register_message_handler(A2AMessageType.TASK, handle_poi_search)


class A2AServer:
    """
    A2A 协议服务器
    管理多个 Agent 之间的通信
    """
    
    def __init__(self, server_name: str = "travel-agent-a2a"):
        """
        初始化 A2A 服务器
        
        Args:
            server_name: 服务器名称
        """
        self.server_name = server_name
        self.agents: Dict[str, A2AAgent] = {}
        self.tasks: Dict[str, A2ATask] = {}
        
        # 注册默认旅游助手 Agent
        self.register_agent(TravelA2AAgent())
        
        logger.info(f"A2A 服务器初始化: {server_name}")
    
    def register_agent(self, agent: A2AAgent):
        """
        注册 Agent
        
        Args:
            agent: Agent 实例
        """
        self.agents[agent.agent_id] = agent
        logger.info(f"注册 Agent: {agent.name} ({agent.agent_id})")
    
    def get_agent(self, agent_id: str) -> Optional[A2AAgent]:
        """获取 Agent"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Dict]:
        """列出所有 Agent"""
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "capabilities": agent.capabilities,
                "description": agent.description
            }
            for agent in self.agents.values()
        ]
    
    async def send_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        发送消息到目标 Agent
        
        Args:
            message: A2A 消息
            
        Returns:
            响应消息
        """
        target_agent = self.agents.get(message.recipient)
        
        if not target_agent:
            logger.error(f"目标 Agent 不存在: {message.recipient}")
            return None
        
        # 转发消息
        return await target_agent.handle_message(message)
    
    async def create_task(
        self,
        task_type: str,
        from_agent: str,
        to_agent: str,
        payload: Dict[str, Any],
        parent_task_id: Optional[str] = None
    ) -> A2ATask:
        """
        创建任务
        
        Args:
            task_type: 任务类型
            from_agent: 发起 Agent
            to_agent: 目标 Agent
            payload: 任务数据
            parent_task_id: 父任务ID
            
        Returns:
            创建的任务
        """
        task = A2ATask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            status=A2ATaskStatus.PENDING,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload,
            parent_task_id=parent_task_id
        )
        
        self.tasks[task.id] = task
        
        # 发送任务消息
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            sender=from_agent,
            recipient=to_agent,
            content={
                "task_id": task.id,
                "task_type": task_type,
                "payload": payload
            },
            message_type=A2AMessageType.TASK.value
        )
        
        await self.send_message(message)
        
        return task
    
    def get_task(self, task_id: str) -> Optional[A2ATask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task_status(
        self, 
        task_id: str, 
        status: A2ATaskStatus,
        result: Optional[Dict] = None
    ):
        """更新任务状态"""
        task = self.tasks.get(task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now()
            if result:
                task.result = result
            
            logger.info(f"任务 {task_id} 状态更新为 {status.value}")
    
    async def dispatch_task(self, task_request: Dict) -> Dict:
        """
        分派任务到合适的 Agent
        
        Args:
            task_request: 任务请求
            
        Returns:
            分派结果
        """
        task_type = task_request.get("task_type")
        
        # 找到能处理该任务的 Agent
        capable_agents = [
            agent for agent in self.agents.values()
            if task_type in agent.capabilities
        ]
        
        if not capable_agents:
            return {
                "success": False,
                "error": f"没有 Agent 能处理任务类型: {task_type}"
            }
        
        # 选择第一个可用的 Agent
        selected_agent = capable_agents[0]
        
        # 创建并发送任务
        task = await self.create_task(
            task_type=task_type,
            from_agent="system",
            to_agent=selected_agent.agent_id,
            payload=task_request.get("payload", {})
        )
        
        return {
            "success": True,
            "task_id": task.id,
            "assigned_to": selected_agent.agent_id
        }


# 全局 A2A 服务器实例
_a2a_server: Optional[A2AServer] = None


def get_a2a_server() -> A2AServer:
    """获取 A2A 服务器实例"""
    global _a2a_server
    if _a2a_server is None:
        _a2a_server = A2AServer()
    return _a2a_server


async def send_a2a_message(
    to_agent: str,
    content: Dict[str, Any],
    from_agent: str = "system",
    message_type: str = "request"
) -> Optional[Dict]:
    """
    发送 A2A 消息的便捷函数
    
    Args:
        to_agent: 目标 Agent ID
        content: 消息内容
        from_agent: 发送方 Agent ID
        message_type: 消息类型
        
    Returns:
        响应内容
    """
    server = get_a2a_server()
    
    message = A2AMessage(
        message_id=str(uuid.uuid4()),
        sender=from_agent,
        recipient=to_agent,
        content=content,
        message_type=message_type
    )
    
    response = await server.send_message(message)
    
    if response:
        return response.content
    return None
