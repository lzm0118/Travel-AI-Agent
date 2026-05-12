"""
配置管理模块
支持从环境变量和 YAML 配置文件加载配置
"""
import os
from typing import List, Optional
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import yaml

# 加载 .env 文件（从项目根目录查找）
def _load_env_file():
    """加载 .env 文件到环境变量"""
    # 尝试多个可能的位置
    possible_paths = [
        Path.cwd() / ".env",  # 当前目录
        Path(__file__).parent.parent.parent.parent / ".env",  # 项目根目录
        Path(__file__).parent.parent / ".env",  # backend 目录
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            print(f"[Config] 已加载 .env 文件: {env_path}")
            return True
    
    print("[Config] 警告: 未找到 .env 文件")
    return False

# 在模块导入时自动加载
_load_env_file()


class LLMConfig(BaseSettings):
    """LLM 模型配置"""
    model_config = SettingsConfigDict(env_prefix="LLM_")
    
    default_model: str = "qwen-max"
    fallback_model: str = "glm-4"
    temperature: float = 0.7
    max_tokens: int = 4096


class QwenConfig(BaseSettings):
    """通义千问配置"""
    model_config = SettingsConfigDict(env_prefix="QWEN_")
    
    api_key: str = Field(default="", alias="QWEN_API_KEY")
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class ZhipuConfig(BaseSettings):
    """智谱 AI 配置"""
    model_config = SettingsConfigDict(env_prefix="ZHIPU_")
    
    api_key: str = Field(default="", alias="ZHIPU_API_KEY")
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"


class AmapConfig(BaseSettings):
    """高德地图配置"""
    model_config = SettingsConfigDict(env_prefix="AMAP_")
    
    key: str = Field(default="", alias="AMAP_KEY")
    base_url: str = "https://restapi.amap.com/v3"
    timeout: int = 30


class SearchConfig(BaseSettings):
    """联网搜索配置"""
    model_config = SettingsConfigDict(env_prefix="SEARCH_")
    
    provider: str = "duckduckgo"  # 默认使用 DuckDuckGo（免费，无需API Key）
    api_key: str = Field(default="", alias="BING_SEARCH_KEY")  # 必应API Key（可选）
    timeout: int = 30
    max_results: int = 10
    
    # 备选搜索配置
    serper_key: str = Field(default="", alias="SERPER_API_KEY")
    bing_endpoint: str = "https://api.bing.microsoft.com/v7.0"


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    url: str = Field(
        default="sqlite+aiosqlite:///./data/travel_agent.db",
        alias="DATABASE_URL"
    )


class RedisConfig(BaseSettings):
    """Redis 配置"""
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    password: Optional[str] = None


class Settings(BaseSettings):
    """应用主配置"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    # 应用配置
    app_name: str = "智能旅游助手"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS 配置
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000"
        ],
        alias="CORS_ORIGINS"
    )
    
    # 安全配置
    secret_key: str = Field(default="change-this-secret-key", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 组件开关
    enable_tools: bool = True
    enable_memory: bool = True
    
    # 功能配置
    max_history: int = 20
    request_timeout: int = 60
    max_retries: int = 3

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "Settings":
        """从 YAML 文件加载配置"""
        settings = cls()
        
        if os.path.exists(yaml_path):
            with open(yaml_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
                
            # 应用 YAML 配置
            if yaml_config:
                # 这里可以根据 YAML 结构更新配置
                pass
                
        return settings


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_qwen_config() -> QwenConfig:
    """获取通义千问配置"""
    return QwenConfig()


def get_zhipu_config() -> ZhipuConfig:
    """获取智谱配置"""
    return ZhipuConfig()


def get_amap_config() -> AmapConfig:
    """获取高德地图配置"""
    return AmapConfig()


def get_search_config() -> SearchConfig:
    """获取搜索配置"""
    return SearchConfig()


def get_database_config() -> DatabaseConfig:
    """获取数据库配置"""
    return DatabaseConfig()


def get_redis_config() -> RedisConfig:
    """获取 Redis 配置"""
    return RedisConfig()


@lru_cache()
def get_yaml_config(yaml_path: str = "backend/config/settings.yaml") -> dict:
    """加载 YAML 配置文件（带缓存）"""
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}
