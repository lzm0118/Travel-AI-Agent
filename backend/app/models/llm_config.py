"""
LLM 模型配置和工厂
支持通义千问 (Qwen) 和智谱 (GLM)
"""
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from ..core.config import get_qwen_config, get_zhipu_config, get_settings


class LLMProvider:
    """LLM 提供商枚举"""
    QWEN = "qwen"
    ZHIPU = "zhipu"


class LLMConfig:
    """LLM 配置类"""
    
    def __init__(
        self,
        provider: str,
        model_name: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_params = kwargs


class LLMFactory:
    """
    LLM 模型工厂
    创建和管理不同的 LLM 实例
    """
    
    @staticmethod
    def create_qwen(
        model_name: str = "qwen-max",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ChatOpenAI:
        """
        创建通义千问模型实例
        
        Args:
            model_name: 模型名称，如 qwen-max, qwen-plus, qwen-turbo
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            
        Returns:
            ChatOpenAI: 模型实例
        """
        config = get_qwen_config()
        
        if not config.api_key:
            raise ValueError("未配置 Qwen API Key")
        
        return ChatOpenAI(
            model=model_name,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @staticmethod
    def create_zhipu(
        model_name: str = "glm-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ChatOpenAI:
        """
        创建智谱 AI 模型实例
        
        Args:
            model_name: 模型名称，如 glm-4, glm-4-flash
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            
        Returns:
            ChatOpenAI: 模型实例
        """
        config = get_zhipu_config()
        
        if not config.api_key:
            raise ValueError("未配置 Zhipu API Key")
        
        return ChatOpenAI(
            model=model_name,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @classmethod
    def create(
        cls,
        provider: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ChatOpenAI:
        """
        通用创建方法
        
        Args:
            provider: 提供商名称 (qwen/zhipu)
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            
        Returns:
            ChatOpenAI: 模型实例
        """
        if provider == LLMProvider.QWEN:
            default_model = model_name or "qwen-max"
            return cls.create_qwen(default_model, temperature, max_tokens, **kwargs)
        
        elif provider == LLMProvider.ZHIPU:
            default_model = model_name or "glm-4"
            return cls.create_zhipu(default_model, temperature, max_tokens, **kwargs)
        
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")
    
    @classmethod
    def get_default(cls) -> ChatOpenAI:
        """获取默认模型"""
        settings = get_settings()
        
        # 尝试使用默认配置
        try:
            return cls.create(settings.llm.default_model)
        except:
            # 如果失败，尝试备用
            return cls.create(settings.llm.fallback_model)


class EmbeddingFactory:
    """
    Embedding 模型工厂
    """
    
    @staticmethod
    def create_qwen_embedding():
        """创建通义千问 Embedding"""
        from langchain.embeddings import OpenAIEmbeddings
        
        config = get_qwen_config()
        
        return OpenAIEmbeddings(
            model="text-embedding-v3",
            api_key=config.api_key,
            base_url=config.base_url
        )


# 系统提示模板
SYSTEM_PROMPTS = {
    "travel_assistant": """你是智能旅游助手，专门为游客提供个性化、全流程的旅游服务。

你的核心能力：
1. **行程规划**：根据用户偏好（预算、时间、兴趣）制定个性化行程
2. **目的地探索**：推荐景点、餐厅、酒店，支持实时 POI 搜索
3. **实时咨询**：天气查询、交通建议、应急处理
4. **记忆学习**：记住用户偏好，持续优化推荐

可用工具：
- amap_poi_search：搜索周边景点、餐厅、酒店
- amap_weather：查询城市天气
- amap_geocode：地址与坐标转换
- web_search：联网搜索最新资讯
- calculator：计算费用、汇率等
- datetime：日期时间相关计算

对话风格：
- 友好、热情、专业
- 回答简洁明了，重点突出
- 主动询问用户偏好以提供更好的服务
- 使用中文回答

注意事项：
- 当用户询问具体地点时，使用 POI 搜索工具获取准确信息
- 涉及天气时，主动查询实时天气
- 需要最新信息时，使用联网搜索
- 计算费用时，使用计算器确保准确
""",

    "itinerary_planner": """你是专业的行程规划师，擅长为用户制定详细的旅游行程。

规划原则：
1. **合理性**：考虑地理位置、开放时间、交通时间
2. **个性化**：结合用户偏好（美食、文化、户外等）
3. **灵活性**：预留自由活动时间
4. **实用性**：包含实用的贴士和注意事项

输出格式：
- 按天规划，分为上午/下午/晚上
- 每个活动包含：时间、地点、预计时长、推荐理由
- 提供交通建议
- 包含预算估算
- 添加实用贴士

工具使用：
- 使用 POI 搜索获取景点详细信息
- 使用天气查询获取目的地天气
- 使用联网搜索获取最新景点信息
""",

    "emergency_handler": """你是旅游应急助手，专门处理旅行中的紧急情况和突发问题。

处理能力：
1. **医疗急救**：推荐附近医院、药店，提供急救建议
2. **交通问题**：替代交通方案、延误处理
3. **安全问题**：安全建议、紧急联系方式
4. **物品丢失**：补办证件流程、失物招领

响应原则：
- 保持冷静、专业
- 优先确保人身安全
- 提供可执行的具体步骤
- 提供紧急联系方式（110/120/119等）

工具使用：
- 使用 POI 搜索附近医院/派出所/大使馆
- 使用联网搜索获取最新应急信息
"""
}


def get_system_prompt(agent_type: str = "travel_assistant") -> str:
    """
    获取系统提示
    
    Args:
        agent_type: Agent 类型
        
    Returns:
        系统提示文本
    """
    return SYSTEM_PROMPTS.get(agent_type, SYSTEM_PROMPTS["travel_assistant"])


def create_system_message(
    agent_type: str = "travel_assistant",
    user_profile: Optional[str] = None,
    memory_summary: Optional[str] = None
) -> SystemMessage:
    """
    创建系统消息
    
    Args:
        agent_type: Agent 类型
        user_profile: 用户画像摘要
        memory_summary: 历史对话总结
        
    Returns:
        SystemMessage: 系统消息
    """
    base_prompt = get_system_prompt(agent_type)
    
    # 添加用户画像
    if user_profile:
        base_prompt += f"\n\n{user_profile}"
    
    # 添加历史总结
    if memory_summary:
        base_prompt += f"\n\n【历史对话总结】\n{memory_summary}"
    
    return SystemMessage(content=base_prompt)


# 便捷函数

def get_llm(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs
) -> ChatOpenAI:
    """
    获取 LLM 实例的便捷函数
    
    Args:
        provider: 提供商
        model_name: 模型名称
        **kwargs: 其他参数
        
    Returns:
        ChatOpenAI: 模型实例
    """
    settings = get_settings()
    
    if provider is None:
        provider = settings.llm.default_model
    
    return LLMFactory.create(provider, model_name, **kwargs)
