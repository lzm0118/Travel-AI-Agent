"""
用户画像系统
管理用户偏好、旅行风格和个性化设置
"""
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import json
import asyncio

from loguru import logger

from ..models.schemas import UserProfile


class UserProfileManager:
    """
    用户画像管理器
    存储和管理用户的长期偏好和旅行习惯
    """
    
    def __init__(self, storage_backend: str = "memory"):
        """
        初始化用户画像管理器
        
        Args:
            storage_backend: 存储后端，支持 memory, sqlite, redis
        """
        self.storage_backend = storage_backend
        self._profiles: Dict[str, UserProfile] = {}
        self._dirty: Set[str] = set()  # 标记需要持久化的用户
        
        logger.info(f"初始化用户画像管理器，存储后端: {storage_backend}")
    
    async def get_profile(self, user_id: str) -> UserProfile:
        """
        获取用户画像（如果不存在则创建）
        
        Args:
            user_id: 用户唯一标识
            
        Returns:
            UserProfile: 用户画像
        """
        if user_id not in self._profiles:
            # 尝试从持久化存储加载
            profile = await self._load_profile(user_id)
            if profile is None:
                profile = UserProfile(user_id=user_id)
                logger.info(f"创建新用户画像: {user_id}")
            self._profiles[user_id] = profile
        
        return self._profiles[user_id]
    
    async def update_profile(
        self, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> UserProfile:
        """
        更新用户画像
        
        Args:
            user_id: 用户ID
            updates: 更新字段
            
        Returns:
            UserProfile: 更新后的画像
        """
        profile = await self.get_profile(user_id)
        
        # 更新字段
        if "preferences" in updates:
            profile.preferences.update(updates["preferences"])
        
        if "travel_style" in updates:
            profile.travel_style = updates["travel_style"]
        
        if "preferred_destinations" in updates:
            # 合并目的地列表，去重
            existing = set(profile.preferred_destinations)
            new = set(updates["preferred_destinations"])
            profile.preferred_destinations = list(existing | new)
        
        if "dietary_restrictions" in updates:
            profile.dietary_restrictions = updates["dietary_restrictions"]
        
        profile.updated_at = datetime.now()
        
        # 标记需要持久化
        self._dirty.add(user_id)
        
        logger.info(f"更新用户画像: {user_id}")
        return profile
    
    async def extract_preferences_from_message(
        self,
        user_id: str,
        message: str,
        assistant_response: str
    ) -> Dict[str, Any]:
        """
        从对话中提取用户偏好
        
        这个方法是简化版，实际可以使用 LLM 来分析提取
        
        Args:
            user_id: 用户ID
            message: 用户消息
            assistant_response: 助手回复
            
        Returns:
            提取的偏好信息
        """
        preferences = {}
        
        # 简单的关键词提取（实际应该用 NLP）
        budget_keywords = {
            "budget": ["便宜", "实惠", "经济", "省钱", "低价"],
            "luxury": ["豪华", "高端", "奢华", "五星", "顶级"],
            "medium": ["中等", "适中", "性价比", "合理"]
        }
        
        style_keywords = {
            "adventure": ["冒险", "刺激", "户外", "徒步", "探险"],
            "relaxed": ["轻松", "休闲", "度假", "放松", "慢节奏"],
            "cultural": ["文化", "历史", "博物馆", "古迹", "艺术"],
            "food": ["美食", "吃货", "餐厅", "特色小吃", "味道"]
        }
        
        # 检测预算偏好
        for style, keywords in budget_keywords.items():
            if any(kw in message for kw in keywords):
                preferences["budget_preference"] = style
                break
        
        # 检测旅行风格
        for style, keywords in style_keywords.items():
            if any(kw in message for kw in keywords):
                preferences["travel_style"] = style
                break
        
        # 提取目的地偏好
        # 这里简化处理，实际可以用 NER 提取地名
        
        return preferences
    
    async def update_from_conversation(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str
    ):
        """
        从对话中学习和更新用户画像
        
        Args:
            user_id: 用户ID
            user_message: 用户消息
            assistant_response: 助手回复
        """
        preferences = await self.extract_preferences_from_message(
            user_id, user_message, assistant_response
        )
        
        if preferences:
            await self.update_profile(user_id, {"preferences": preferences})
            logger.debug(f"从对话更新用户 {user_id} 的偏好")
    
    def get_profile_summary(self, user_id: str) -> str:
        """
        获取用户画像摘要（用于添加到系统提示）
        
        Args:
            user_id: 用户ID
            
        Returns:
            画像摘要文本
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return ""
        
        parts = []
        
        if profile.travel_style:
            style_map = {
                "budget": "经济型",
                "luxury": "豪华型",
                "medium": "舒适型",
                "adventure": "冒险型",
                "relaxed": "休闲型",
                "cultural": "文化型",
                "food": "美食型"
            }
            style_cn = style_map.get(profile.travel_style, profile.travel_style)
            parts.append(f"旅行风格: {style_cn}")
        
        if profile.preferred_destinations:
            parts.append(f"喜欢目的地: {', '.join(profile.preferred_destinations[:5])}")
        
        if profile.dietary_restrictions:
            parts.append(f"饮食限制: {', '.join(profile.dietary_restrictions)}")
        
        if profile.preferences:
            pref_items = []
            for k, v in list(profile.preferences.items())[:3]:
                pref_items.append(f"{k}: {v}")
            if pref_items:
                parts.append(f"其他偏好: {'; '.join(pref_items)}")
        
        if parts:
            return f"【用户画像】{'; '.join(parts)}"
        return ""
    
    async def _load_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        从持久化存储加载用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            UserProfile 或 None
        """
        if self.storage_backend == "memory":
            return None
        
        # TODO: 实现 SQLite/Redis 加载
        return None
    
    async def _save_profile(self, user_id: str) -> bool:
        """
        保存用户画像到持久化存储
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        if self.storage_backend == "memory":
            return True
        
        profile = self._profiles.get(user_id)
        if not profile:
            return False
        
        # TODO: 实现 SQLite/Redis 保存
        return True
    
    async def persist(self):
        """持久化所有脏数据"""
        for user_id in list(self._dirty):
            await self._save_profile(user_id)
        self._dirty.clear()
    
    async def get_all_profiles(self) -> List[UserProfile]:
        """获取所有用户画像"""
        return list(self._profiles.values())


# 全局用户画像管理器
_profile_manager: Optional[UserProfileManager] = None


def get_user_profile_manager() -> UserProfileManager:
    """获取全局用户画像管理器"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = UserProfileManager()
    return _profile_manager


async def get_user_profile(user_id: str) -> UserProfile:
    """获取用户画像的便捷函数"""
    return await get_user_profile_manager().get_profile(user_id)
