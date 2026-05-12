"""
工具包初始化
自动导入所有工具并注册到 ToolRegistry
"""
from .base_tool import BaseTool, ToolRegistry, ToolResult, get_tool, list_available_tools
from .amap_tools import AmapPOISearchTool, AmapWeatherTool, AmapGeocodeTool
from .duckduckgo_search import DuckDuckGoSearchTool, DuckDuckGoInstantTool
from .bing_search_tool import BingSearchTool
from .search_tools import CalculatorTool, DateTimeTool

# 导出所有工具类
__all__ = [
    # 基类
    "BaseTool",
    "ToolRegistry", 
    "ToolResult",
    "get_tool",
    "list_available_tools",
    
    # 高德地图工具
    "AmapPOISearchTool",
    "AmapWeatherTool",
    "AmapGeocodeTool",
    
    # 搜索工具
    "DuckDuckGoSearchTool",  # 默认免费搜索
    "DuckDuckGoInstantTool",
    "BingSearchTool",  # 备选（需要API Key）
    "CalculatorTool",
    "DateTimeTool"
]


def get_all_tools():
    """获取所有可用工具实例"""
    from ..core.config import get_yaml_config
    
    # 从配置中读取工具配置
    yaml_config = get_yaml_config()
    tools_config = yaml_config.get("tools", {})
    
    # 获取所有工具实例
    tools = {}
    for name in ToolRegistry.list_tools().keys():
        config = tools_config.get(name, {})
        tool = ToolRegistry.get_tool(name, config)
        if tool and tool.enabled:
            tools[name] = tool
    
    return tools


def get_tool_schemas() -> list:
    """获取所有工具的模式定义（用于 Function Calling）"""
    tools = get_all_tools()
    return [
        tool.to_openai_function()
        for tool in tools.values()
    ]


def get_langchain_tools():
    """获取 LangChain 格式的工具列表"""
    from langchain.tools import StructuredTool
    
    tools = get_all_tools()
    langchain_tools = []
    
    for name, tool in tools.items():
        lc_tool = StructuredTool.from_function(
            name=tool.name,
            description=tool.description,
            func=tool.run,
            args_schema=None  # 可以从 parameters 生成
        )
        langchain_tools.append(lc_tool)
    
    return langchain_tools
