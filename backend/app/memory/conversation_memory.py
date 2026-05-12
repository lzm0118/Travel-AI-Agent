"""
对话记忆系统
管理多轮对话历史、上下文保持和对话总结
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json
from collections import deque

from loguru import logger

from ..models.schemas import ChatMessage, MessageRole


class ConversationMemory:
    """
    对话记忆管理器
    负责存储和管理用户与助手的对话历史
    """
    
    def __init__(
        self,
        session_id: str,
        max_history: int = 20,
        summary_threshold: int = 10
    ):
        """
        初始化对话记忆
        
        Args:
            session_id: 会话唯一标识
            max_history: 最大保留消息数
            summary_threshold: 触发总结的阈值
        """
        self.session_id = session_id
        self.max_history = max_history
        self.summary_threshold = summary_threshold
        
        # 消息历史
        self._messages: deque = deque(maxlen=max_history)
        
        # 对话总结（用于长期记忆）
        self._summary: Optional[str] = None
        
        # 元数据
        self._metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
            "last_active": datetime.now().isoformat()
        }
        
        logger.debug(f"初始化会话记忆: {session_id}")
    
    def add_message(
        self, 
        role: MessageRole, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """
        添加消息到历史
        
        Args:
            role: 消息角色
            content: 消息内容
            metadata: 附加元数据
            
        Returns:
            ChatMessage: 添加的消息对象
        """
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self._messages.append(message)
        self._metadata["message_count"] += 1
        self._metadata["last_active"] = datetime.now().isoformat()
        
        # 检查是否需要触发总结
        if len(self._messages) >= self.summary_threshold:
            self._trigger_summary()
        
        logger.debug(f"添加消息到 {self.session_id}: {role.value}")
        return message
    
    def add_user_message(self, content: str, **kwargs) -> ChatMessage:
        """添加用户消息"""
        return self.add_message(MessageRole.USER, content, kwargs)
    
    def add_assistant_message(
        self, 
        content: str, 
        tools_used: Optional[List[str]] = None,
        **kwargs
    ) -> ChatMessage:
        """添加助手消息"""
        metadata = kwargs.copy()
        if tools_used:
            metadata["tools_used"] = tools_used
        return self.add_message(MessageRole.ASSISTANT, content, metadata)
    
    def add_system_message(self, content: str, **kwargs) -> ChatMessage:
        """添加系统消息"""
        return self.add_message(MessageRole.SYSTEM, content, kwargs)
    
    def get_messages(
        self, 
        include_system: bool = True,
        last_n: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        获取消息历史
        
        Args:
            include_system: 是否包含系统消息
            last_n: 只返回最后 N 条
            
        Returns:
            消息列表
        """
        messages = list(self._messages)
        
        if not include_system:
            messages = [m for m in messages if m.role != MessageRole.SYSTEM]
        
        if last_n:
            messages = messages[-last_n:]
        
        return messages
    
    def get_context_messages(
        self,
        context_window: int = 10,
        include_summary: bool = True
    ) -> List[Dict[str, str]]:
        """
        获取用于 LLM 上下文的消息
        
        返回格式化为 OpenAI 风格的对话列表
        
        Args:
            context_window: 上下文窗口大小
            include_summary: 是否包含历史总结
            
        Returns:
            格式化的消息列表
        """
        messages = []
        
        # 添加总结作为系统提示的一部分
        if include_summary and self._summary:
            messages.append({
                "role": "system",
                "content": f"【历史对话总结】{self._summary}"
            })
        
        # 添加最近的消息
        recent_messages = self.get_messages(last_n=context_window)
        for msg in recent_messages:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return messages
    
    def get_last_message(self) -> Optional[ChatMessage]:
        """获取最后一条消息"""
        if self._messages:
            return self._messages[-1]
        return None
    
    def get_user_intent_history(self) -> List[str]:
        """获取用户历史意图（用户消息列表）"""
        return [
            msg.content 
            for msg in self._messages 
            if msg.role == MessageRole.USER
        ]
    
    def _trigger_summary(self):
        """触发对话总结（可以由外部 LLM 调用）"""
        # 标记需要总结，实际总结由外部处理
        self._metadata["needs_summary"] = True
        logger.info(f"会话 {self.session_id} 需要总结")
    
    def update_summary(self, summary: str):
        """
        更新对话总结
        
        Args:
            summary: 总结文本
        """
        self._summary = summary
        self._metadata["needs_summary"] = False
        self._metadata["summary_updated"] = datetime.now().isoformat()
        
        logger.info(f"更新会话 {self.session_id} 的总结")
    
    def get_summary(self) -> Optional[str]:
        """获取当前总结"""
        return self._summary
    
    def clear(self):
        """清空对话历史"""
        self._messages.clear()
        self._summary = None
        self._metadata["message_count"] = 0
        logger.info(f"清空会话 {self.session_id} 的记忆")
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "session_id": self.session_id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in self._messages
            ],
            "summary": self._summary,
            "metadata": self._metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """从字典恢复"""
        memory = cls(
            session_id=data["session_id"],
            max_history=data.get("max_history", 20)
        )
        
        # 恢复消息
        for msg_data in data.get("messages", []):
            msg = ChatMessage(
                role=MessageRole(msg_data["role"]),
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                metadata=msg_data.get("metadata", {})
            )
            memory._messages.append(msg)
        
        memory._summary = data.get("summary")
        memory._metadata = data.get("metadata", memory._metadata)
        
        return memory


class ConversationMemoryStore:
    """
    对话记忆存储管理器
    管理多个会话的记忆，支持持久化
    """
    
    def __init__(self):
        """初始化存储"""
        self._memories: Dict[str, ConversationMemory] = {}
        logger.info("初始化对话记忆存储")
    
    def get_or_create(
        self, 
        session_id: str,
        max_history: int = 20
    ) -> ConversationMemory:
        """
        获取或创建会话记忆
        
        Args:
            session_id: 会话ID
            max_history: 最大历史记录数
            
        Returns:
            ConversationMemory: 会话记忆对象
        """
        if session_id not in self._memories:
            self._memories[session_id] = ConversationMemory(
                session_id=session_id,
                max_history=max_history
            )
            logger.info(f"创建新会话记忆: {session_id}")
        
        return self._memories[session_id]
    
    def get(self, session_id: str) -> Optional[ConversationMemory]:
        """获取会话记忆"""
        return self._memories.get(session_id)
    
    def delete(self, session_id: str) -> bool:
        """删除会话记忆"""
        if session_id in self._memories:
            del self._memories[session_id]
            logger.info(f"删除会话记忆: {session_id}")
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """列出所有会话ID"""
        return list(self._memories.keys())
    
    def clear_all(self):
        """清空所有会话记忆"""
        self._memories.clear()
        logger.info("清空所有会话记忆")
    
    def get_active_sessions(
        self, 
        since_minutes: int = 30
    ) -> List[str]:
        """
        获取活跃会话
        
        Args:
            since_minutes: 最近 N 分钟内有活动的会话
            
        Returns:
            活跃会话ID列表
        """
        from datetime import timedelta
        
        active = []
        now = datetime.now()
        
        for session_id, memory in self._memories.items():
            last_active = datetime.fromisoformat(
                memory._metadata["last_active"]
            )
            if now - last_active < timedelta(minutes=since_minutes):
                active.append(session_id)
        
        return active
    
    def to_dict(self) -> Dict[str, Any]:
        """导出所有记忆为字典"""
        return {
            session_id: memory.to_dict()
            for session_id, memory in self._memories.items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemoryStore":
        """从字典恢复存储"""
        store = cls()
        for session_id, memory_data in data.items():
            store._memories[session_id] = ConversationMemory.from_dict(memory_data)
        return store


# 全局存储实例
_memory_store: Optional[ConversationMemoryStore] = None


def get_memory_store() -> ConversationMemoryStore:
    """获取全局记忆存储实例"""
    global _memory_store
    if _memory_store is None:
        _memory_store = ConversationMemoryStore()
    return _memory_store


def get_session_memory(
    session_id: str,
    max_history: int = 20
) -> ConversationMemory:
    """获取会话记忆的便捷函数"""
    return get_memory_store().get_or_create(session_id, max_history)
