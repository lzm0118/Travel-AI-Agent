"""
记忆系统包
提供对话记忆、用户画像和向量存储功能
"""
from .conversation_memory import (
    ConversationMemory,
    ConversationMemoryStore,
    get_memory_store,
    get_session_memory
)
from .user_profile import (
    UserProfileManager,
    get_user_profile_manager,
    get_user_profile
)
from .vector_store import (
    VectorMemoryStore,
    get_vector_store,
    add_long_term_memory,
    search_long_term_memory
)

__all__ = [
    # 对话记忆
    "ConversationMemory",
    "ConversationMemoryStore",
    "get_memory_store",
    "get_session_memory",
    
    # 用户画像
    "UserProfileManager",
    "get_user_profile_manager",
    "get_user_profile",
    
    # 向量存储
    "VectorMemoryStore",
    "get_vector_store",
    "add_long_term_memory",
    "search_long_term_memory"
]
