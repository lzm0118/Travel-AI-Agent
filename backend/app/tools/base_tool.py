"""
工具基类定义
所有工具都必须继承此类并实现相应方法
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from datetime import datetime
import time

from pydantic import BaseModel, Field
from loguru import logger


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolMetadata(BaseModel):
    """工具元数据"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "Travel AI Agent"
    category: str = "general"
    requires_auth: bool = False
    parameters_schema: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """
    工具基类
    
    所有工具必须继承此类并实现：
    - name: 工具名称（唯一标识）
    - description: 工具描述
    - parameters: 参数定义
    - execute: 执行方法
    """
    
    # 工具基本信息 - 子类必须重写
    name: str = "base_tool"
    description: str = "基础工具"
    version: str = "1.0.0"
    
    # 参数定义（JSON Schema 格式）
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # 是否启用
    enabled: bool = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化工具
        
        Args:
            config: 工具配置字典
        """
        self.config = config or {}
        self._validate_config()
        logger.debug(f"工具 {self.name} 初始化完成")
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        pass
    
    def _validate_config(self) -> None:
        """验证工具配置，子类可重写"""
        pass
    
    def _validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证参数是否符合 schema
        
        Args:
            params: 输入参数
            
        Returns:
            验证后的参数
            
        Raises:
            ValueError: 参数验证失败
        """
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        
        # 检查必需参数
        for param in required:
            if param not in params or params[param] is None:
                raise ValueError(f"缺少必需参数: {param}")
        
        # 类型检查（简化版）
        for key, value in params.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    raise ValueError(
                        f"参数 {key} 类型错误，期望 {expected_type}"
                    )
        
        return params
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查值是否符合期望类型"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_mapping.get(expected_type)
        if expected is None:
            return True
        
        return isinstance(value, expected)
    
    async def run(self, **kwargs) -> ToolResult:
        """
        运行工具（带执行时间和错误处理）
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        start_time = time.time()
        
        try:
            # 参数验证
            validated_params = self._validate_params(kwargs)
            
            # 执行工具
            logger.info(f"执行工具 {self.name}, 参数: {validated_params}")
            result = await self.execute(**validated_params)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            logger.info(
                f"工具 {self.name} 执行完成, "
                f"耗时: {execution_time:.2f}s, "
                f"成功: {result.success}"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"工具 {self.name} 执行失败: {str(e)}")
            
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                execution_time=execution_time
            )
    
    def get_metadata(self) -> ToolMetadata:
        """获取工具元数据"""
        return ToolMetadata(
            name=self.name,
            description=self.description,
            version=self.version,
            parameters_schema=self.parameters
        )
    
    def to_openai_function(self) -> Dict[str, Any]:
        """
        转换为 OpenAI Function Calling 格式
        
        Returns:
            OpenAI 函数定义
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def to_langchain_tool(self) -> Dict[str, Any]:
        """
        转换为 LangChain Tool 格式
        
        Returns:
            LangChain 工具定义
        """
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self.parameters,
            "func": self.run
        }


class ToolRegistry:
    """
    工具注册中心
    管理所有可用工具
    """
    
    _tools: Dict[str, Type[BaseTool]] = {}
    _instances: Dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        """
        注册工具类（装饰器方式）
        
        用法:
            @ToolRegistry.register
            class MyTool(BaseTool):
                name = "my_tool"
                ...
        """
        tool_name = tool_class.name
        cls._tools[tool_name] = tool_class
        logger.info(f"注册工具: {tool_name}")
        return tool_class
    
    @classmethod
    def register_manual(cls, name: str, tool_class: Type[BaseTool]) -> None:
        """手动注册工具"""
        cls._tools[name] = tool_class
        logger.info(f"手动注册工具: {name}")
    
    @classmethod
    def get_tool_class(cls, name: str) -> Optional[Type[BaseTool]]:
        """获取工具类"""
        return cls._tools.get(name)
    
    @classmethod
    def get_tool(cls, name: str, config: Optional[Dict] = None) -> Optional[BaseTool]:
        """
        获取工具实例（单例模式）
        
        Args:
            name: 工具名称
            config: 工具配置
            
        Returns:
            工具实例或 None
        """
        # 检查缓存
        cache_key = f"{name}_{hash(str(config))}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # 创建新实例
        tool_class = cls.get_tool_class(name)
        if tool_class is None:
            logger.error(f"未找到工具: {name}")
            return None
        
        instance = tool_class(config)
        cls._instances[cache_key] = instance
        return instance
    
    @classmethod
    def list_tools(cls) -> Dict[str, str]:
        """列出所有已注册工具"""
        return {
            name: tool_class.description 
            for name, tool_class in cls._tools.items()
        }
    
    @classmethod
    def get_all_tools(
        cls, 
        config: Optional[Dict[str, Dict]] = None
    ) -> Dict[str, BaseTool]:
        """
        获取所有工具实例
        
        Args:
            config: 工具配置字典 {tool_name: config_dict}
            
        Returns:
            工具实例字典
        """
        tools = {}
        for name in cls._tools:
            tool_config = config.get(name) if config else None
            tool = cls.get_tool(name, tool_config)
            if tool and tool.enabled:
                tools[name] = tool
        return tools
    
    @classmethod
    def clear_cache(cls) -> None:
        """清除工具实例缓存"""
        cls._instances.clear()
        logger.info("工具实例缓存已清除")


# 便捷函数

def get_tool(name: str, config: Optional[Dict] = None) -> Optional[BaseTool]:
    """获取工具实例的便捷函数"""
    return ToolRegistry.get_tool(name, config)


def list_available_tools() -> Dict[str, str]:
    """列出可用工具的便捷函数"""
    return ToolRegistry.list_tools()
