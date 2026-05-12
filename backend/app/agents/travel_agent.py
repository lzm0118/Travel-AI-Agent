"""
旅游助手 Agent 实现
基于 LangGraph 的 ReAct 风格 Agent
"""
from typing import Any, Dict, List, Optional, TypedDict, Annotated, Sequence, Union
from datetime import datetime
import json

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
import inspect

from ..models.llm_config import LLMFactory, create_system_message, LLMProvider
from ..models.schemas import ChatMessage, MessageRole
from ..tools import get_all_tools, get_tool_schemas
from ..memory import get_session_memory, get_user_profile_manager


# 定义 Agent 状态
class AgentState(TypedDict):
    """Agent 状态定义"""
    messages: Annotated[Sequence[BaseMessage], "对话消息列表"]
    session_id: str
    user_id: Optional[str]
    tools_used: Annotated[List[str], "已使用的工具"]
    iteration_count: int
    should_continue: bool


class TravelAgent:
    """
    旅游助手 Agent
    基于 LangGraph 实现，支持工具调用和多轮对话
    """
    
    def __init__(
        self,
        model_provider: str = LLMProvider.QWEN,
        model_name: Optional[str] = None,
        max_iterations: int = 5  # 减少迭代次数以加快响应速度
    ):
        """
        初始化旅游助手 Agent
        
        Args:
            model_provider: 模型提供商
            model_name: 模型名称
            max_iterations: 最大迭代次数
        """
        self.model_provider = model_provider
        self.model_name = model_name or ("qwen-max" if model_provider == LLMProvider.QWEN else "glm-4")
        self.max_iterations = max_iterations
        
        # 初始化 LLM
        self.llm = LLMFactory.create(
            provider=model_provider,
            model_name=self.model_name,
            temperature=0.7
        )
        
        # 初始化工具（转换为 LangChain 格式）
        self.custom_tools = get_all_tools()
        self.tools = self._convert_to_langchain_tools(self.custom_tools)
        self.tools_map = {tool.name: tool for tool in self.custom_tools.values()}
        
        # 构建 Agent 图
        self.workflow = self._build_workflow()
        
        logger.info(f"旅游助手 Agent 初始化完成: {model_provider}/{self.model_name}")
    
    def _convert_to_langchain_tools(self, custom_tools: Dict[str, Any]) -> List[StructuredTool]:
        """
        将自定义工具转换为 LangChain 格式
        
        Args:
            custom_tools: 自定义工具字典
            
        Returns:
            LangChain 格式的工具列表
        """
        lc_tools = []
        
        for name, tool in custom_tools.items():
            try:
                # 创建包装函数
                def make_run_fn(t):
                    async def run_fn(**kwargs):
                        result = await t.run(**kwargs)
                        return result.data if result.success else f"错误: {result.error}"
                    return run_fn
                
                # 提取参数定义
                parameters = getattr(tool, 'parameters', {})
                properties = parameters.get('properties', {})
                required = parameters.get('required', [])
                
                # 构建参数 schema
                args_schema = None
                if properties:
                    # 创建动态 Pydantic 模型
                    from pydantic import create_model
                    fields = {}
                    for param_name, param_info in properties.items():
                        param_type = str
                        default = ... if param_name in required else None
                        if param_info.get('type') == 'integer':
                            param_type = int
                        elif param_info.get('type') == 'number':
                            param_type = float
                        elif param_info.get('type') == 'boolean':
                            param_type = bool
                        fields[param_name] = (param_type, default)
                    
                    if fields:
                        args_schema = create_model(f'{name}_args', **fields)
                
                # 创建 LangChain 工具
                lc_tool = StructuredTool.from_function(
                    name=name,
                    func=make_run_fn(tool),
                    description=tool.description,
                    args_schema=args_schema,
                    coroutine=make_run_fn(tool)
                )
                lc_tools.append(lc_tool)
                logger.debug(f"工具 {name} 已转换为 LangChain 格式")
                
            except Exception as e:
                logger.error(f"工具 {name} 转换失败: {e}")
        
        logger.info(f"成功转换 {len(lc_tools)} 个工具到 LangChain 格式")
        return lc_tools
    
    def _build_workflow(self) -> StateGraph:
        """
        构建 LangGraph 工作流
        
        流程: call_model -> (tool_node) -> should_continue -> END
        """
        # 定义状态图
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("call_model", self._call_model)
        workflow.add_node("tool_node", self._tool_node)
        
        # 添加边
        workflow.set_entry_point("call_model")
        
        # 条件边：根据是否需要调用工具决定下一步
        workflow.add_conditional_edges(
            "call_model",
            self._should_call_tools,
            {
                "continue": "tool_node",
                "end": END
            }
        )
        
        # 工具节点后返回模型调用
        workflow.add_edge("tool_node", "call_model")
        
        return workflow.compile()
    
    async def _call_model(self, state: AgentState) -> Dict:
        """
        调用 LLM 模型（异步）
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        messages = list(state["messages"])
        
        # 绑定工具到模型
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 调用模型
        try:
            response = await llm_with_tools.ainvoke(messages)
            
            # 调试：记录原始响应
            logger.debug(f"模型原始响应: {repr(response.content)[:200] if hasattr(response, 'content') else 'N/A'}")
            
            # 更新状态
            return {
                "messages": messages + [response],
                "iteration_count": state["iteration_count"] + 1
            }
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            error_msg = AIMessage(content=f"抱歉，处理您的请求时出现了错误: {str(e)}")
            return {
                "messages": messages + [error_msg],
                "should_continue": False
            }
    
    async def _tool_node(self, state: AgentState) -> Dict:
        """
        工具执行节点（异步）
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        messages = list(state["messages"])
        last_message = messages[-1]
        
        # 检查最后一条消息是否是 AI 的工具调用
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"messages": messages}
        
        # 执行工具调用
        tool_messages = []
        tools_used = list(state.get("tools_used", []))
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")
            
            logger.info(f"执行工具: {tool_name}, 参数: {tool_args}")
            
            # 查找工具
            tool = self.tools_map.get(tool_name)
            
            if tool:
                try:
                    # 执行工具（异步）
                    result = await tool.run(**tool_args)
                    
                    # 构建工具消息
                    content = json.dumps(result.data, ensure_ascii=False) if result.success else result.error
                    
                    tool_msg = ToolMessage(
                        content=content,
                        name=tool_name,
                        tool_call_id=tool_id
                    )
                    
                    tool_messages.append(tool_msg)
                    tools_used.append(tool_name)
                    
                    logger.info(f"工具 {tool_name} 执行成功")
                    
                except Exception as e:
                    logger.error(f"工具 {tool_name} 执行失败: {e}")
                    error_msg = ToolMessage(
                        content=f"工具执行失败: {str(e)}",
                        name=tool_name,
                        tool_call_id=tool_id
                    )
                    tool_messages.append(error_msg)
            else:
                logger.warning(f"未找到工具: {tool_name}")
                error_msg = ToolMessage(
                    content=f"未知工具: {tool_name}",
                    name=tool_name,
                    tool_call_id=tool_id
                )
                tool_messages.append(error_msg)
        
        return {
            "messages": messages + tool_messages,
            "tools_used": list(set(tools_used))
        }
    
    def _should_call_tools(self, state: AgentState) -> str:
        """
        决定是否需要调用工具
        
        Args:
            state: 当前状态
            
        Returns:
            "continue" 继续调用工具，"end" 结束
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        # 检查迭代次数
        if state["iteration_count"] >= self.max_iterations:
            logger.warning(f"达到最大迭代次数: {self.max_iterations}")
            return "end"
        
        # 检查最后一条消息是否是 AI 的工具调用请求
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"
        
        return "end"
    
    async def chat(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            message: 用户消息
            session_id: 会话ID
            user_id: 用户ID
            stream: 是否流式响应
            
        Returns:
            响应结果
        """
        # 获取会话记忆
        session_memory = get_session_memory(session_id)
        
        # 获取用户画像
        user_profile_text = ""
        if user_id:
            user_profile_mgr = get_user_profile_manager()
            user_profile = await user_profile_mgr.get_profile(user_id)
            user_profile_text = user_profile_mgr.get_profile_summary(user_id)
        
        # 构建系统消息
        system_msg = create_system_message(
            agent_type="travel_assistant",
            user_profile=user_profile_text,
            memory_summary=session_memory.get_summary()
        )
        
        # 获取历史消息
        history = session_memory.get_context_messages(context_window=10)
        
        # 构建消息列表
        messages = [system_msg]
        
        # 添加历史（转换为 LangChain 消息格式）
        for h in history:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                messages.append(AIMessage(content=h["content"]))
        
        # 添加当前用户消息
        messages.append(HumanMessage(content=message))
        
        # 添加到记忆
        session_memory.add_user_message(message)
        
        # 准备初始状态
        initial_state = AgentState(
            messages=messages,
            session_id=session_id,
            user_id=user_id,
            tools_used=[],
            iteration_count=0,
            should_continue=True
        )
        
        # 执行 Agent 图（异步）
        try:
            result = await self.workflow.ainvoke(initial_state)
            
            # 获取最终响应
            final_messages = result["messages"]
            last_message = final_messages[-1]
            
            # 提取响应内容
            if isinstance(last_message, AIMessage):
                response_content = last_message.content
            else:
                response_content = str(last_message.content)
            
            # 调试：记录提取的内容
            logger.info(f"Agent 最终响应内容: {repr(response_content)[:200]}")
            
            # 添加到记忆
            tools_used = result.get("tools_used", [])
            session_memory.add_assistant_message(
                response_content,
                tools_used=tools_used
            )
            
            # 更新用户画像
            if user_id:
                await user_profile_mgr.update_from_conversation(
                    user_id, message, response_content
                )
            
            return {
                "success": True,
                "session_id": session_id,
                "message": response_content,
                "tools_used": tools_used,
                "iteration_count": result["iteration_count"]
            }
            
        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "message": f"抱歉，处理您的请求时出现了错误: {str(e)}",
                "tools_used": [],
                "error": str(e)
            }
    
    async def stream_chat(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None
    ):
        """
        流式处理用户消息，带思考过程展示
        
        Args:
            message: 用户消息
            session_id: 会话ID
            user_id: 用户ID
            
        Yields:
            流式响应块
        """
        import asyncio
        
        # 思考阶段记录
        thinking_steps = []
        tools_used = []
        
        # 阶段1：分析需求
        thinking_steps.append("正在分析您的旅游需求...")
        yield {
            "session_id": session_id,
            "type": "thinking",
            "thinking_steps": thinking_steps,
            "current_step": 0,
            "is_finished": False
        }
        await asyncio.sleep(0.5)
        
        # 获取会话记忆
        from ..memory import get_session_memory, get_user_profile_manager
        session_memory = get_session_memory(session_id)
        
        # 阶段2：检索记忆
        if len(session_memory.get_messages()) > 0:
            thinking_steps.append("正在检索对话历史...")
            yield {
                "session_id": session_id,
                "type": "thinking",
                "thinking_steps": thinking_steps,
                "current_step": 1,
                "is_finished": False
            }
            await asyncio.sleep(0.3)
        
        # 添加用户消息到记忆
        session_memory.add_user_message(message)
        
        # 阶段3：准备上下文
        thinking_steps.append("正在准备系统指令...")
        yield {
            "session_id": session_id,
            "type": "thinking",
            "thinking_steps": thinking_steps,
            "current_step": len(thinking_steps) - 1,
            "is_finished": False
        }
        
        # 获取用户画像
        user_profile_text = ""
        if user_id:
            user_profile_mgr = get_user_profile_manager()
            user_profile = await user_profile_mgr.get_profile(user_id)
            user_profile_text = user_profile_mgr.get_profile_summary(user_id)
        
        # 构建系统消息
        system_msg = create_system_message(
            agent_type="travel_assistant",
            user_profile=user_profile_text,
            memory_summary=session_memory.get_summary()
        )
        
        # 获取历史消息
        history = session_memory.get_context_messages(context_window=10)
        
        # 构建消息列表
        messages = [system_msg]
        for h in history:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                messages.append(AIMessage(content=h["content"]))
        
        await asyncio.sleep(0.3)
        
        # 阶段4：调用模型思考
        thinking_steps.append("正在思考最佳回复方案...")
        yield {
            "session_id": session_id,
            "type": "thinking",
            "thinking_steps": thinking_steps,
            "current_step": len(thinking_steps) - 1,
            "is_finished": False
        }
        
        # 绑定工具
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 首次调用模型
        try:
            response = await llm_with_tools.ainvoke(messages)
        except Exception as e:
            yield {
                "session_id": session_id,
                "type": "error",
                "chunk": f"模型调用失败: {str(e)}",
                "is_finished": True
            }
            return
        
        # 检查是否需要工具调用
        max_tool_iterations = 3
        current_iteration = 0
        all_messages = messages + [response]
        
        while hasattr(response, 'tool_calls') and response.tool_calls and current_iteration < max_tool_iterations:
            current_iteration += 1
            
            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name', 'unknown')
                tool_args = tool_call.get('args', {})
                
                # 添加工具执行思考步骤
                step_desc = f"正在使用工具: {self._get_tool_display_name(tool_name)}"
                if 'query' in tool_args:
                    step_desc += f" (查询: {tool_args['query']})"
                elif 'location' in tool_args:
                    step_desc += f" (位置: {tool_args['location']})"
                elif 'city' in tool_args:
                    step_desc += f" (城市: {tool_args['city']})"
                
                thinking_steps.append(step_desc)
                yield {
                    "session_id": session_id,
                    "type": "thinking",
                    "thinking_steps": thinking_steps,
                    "current_step": len(thinking_steps) - 1,
                    "tool_name": tool_name,
                    "is_finished": False
                }
                
                # 执行工具
                if tool_name in self.tools_map:
                    tool = self.tools_map[tool_name]
                    try:
                        result = await tool.run(**tool_args)
                        tools_used.append(tool_name)
                        
                        # 更新思考状态为完成
                        thinking_steps[-1] = f"✓ {thinking_steps[-1]}"
                        yield {
                            "session_id": session_id,
                            "type": "thinking",
                            "thinking_steps": thinking_steps,
                            "current_step": len(thinking_steps) - 1,
                            "is_finished": False
                        }
                        
                        # 添加工具结果到消息
                        tool_msg = ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call.get('id', ''),
                            name=tool_name
                        )
                        all_messages.append(tool_msg)
                    except Exception as e:
                        error_msg = f"工具执行失败: {str(e)}"
                        thinking_steps[-1] = f"✗ {thinking_steps[-1]} - {error_msg}"
                        yield {
                            "session_id": session_id,
                            "type": "thinking",
                            "thinking_steps": thinking_steps,
                            "current_step": len(thinking_steps) - 1,
                            "is_finished": False
                        }
            
            # 再次调用模型获取最终回复
            thinking_steps.append("正在综合所有信息生成回复...")
            yield {
                "session_id": session_id,
                "type": "thinking",
                "thinking_steps": thinking_steps,
                "current_step": len(thinking_steps) - 1,
                "is_finished": False
            }
            
            response = await llm_with_tools.ainvoke(all_messages)
            all_messages.append(response)
        
        # 思考完成，开始输出内容
        thinking_steps.append("思考完成，正在生成回复...")
        yield {
            "session_id": session_id,
            "type": "thinking_complete",
            "thinking_steps": thinking_steps,
            "total_thoughts": len(thinking_steps),
            "is_finished": False
        }
        await asyncio.sleep(0.3)
        
        # 输出最终内容（流式）
        final_content = response.content if hasattr(response, 'content') else str(response)
        chunk_size = 8
        
        for i in range(0, len(final_content), chunk_size):
            chunk = final_content[i:i + chunk_size]
            yield {
                "session_id": session_id,
                "type": "content",
                "chunk": chunk,
                "is_finished": i + chunk_size >= len(final_content),
                "tools_used": list(set(tools_used)) if tools_used else []
            }
            await asyncio.sleep(0.02)
        
        # 保存到记忆
        session_memory.add_assistant_message(final_content, tools_used=list(set(tools_used)))
        
        # 发送完成标记
        yield {
            "session_id": session_id,
            "type": "complete",
            "chunk": "",
            "is_finished": True,
            "tools_used": list(set(tools_used)) if tools_used else []
        }
    
    def _get_tool_display_name(self, tool_name: str) -> str:
        """获取工具显示名称"""
        display_names = {
            'amap_poi_search': '高德地图POI搜索',
            'amap_weather': '高德天气查询',
            'amap_geocode': '地理编码',
            'web_search': '网络搜索',
            'instant_answer': '即时问答',
            'bing_search': '必应搜索',
            'calculator': '计算器',
            'datetime': '日期时间'
        }
        return display_names.get(tool_name, tool_name)


# 全局 Agent 实例
_default_agent: Optional[TravelAgent] = None


def get_travel_agent(
    provider: Optional[str] = None,
    model_name: Optional[str] = None
) -> TravelAgent:
    """
    获取旅游助手 Agent 实例（单例）
    
    Args:
        provider: 模型提供商
        model_name: 模型名称
        
    Returns:
        TravelAgent: Agent 实例
    """
    global _default_agent
    
    if _default_agent is None:
        provider = provider or LLMProvider.QWEN
        _default_agent = TravelAgent(
            model_provider=provider,
            model_name=model_name
        )
    
    return _default_agent


async def chat_with_agent(
    message: str,
    session_id: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    与 Agent 对话的便捷函数
    
    Args:
        message: 用户消息
        session_id: 会话ID
        user_id: 用户ID
        
    Returns:
        对话结果
    """
    agent = get_travel_agent()
    return await agent.chat(message, session_id, user_id)
