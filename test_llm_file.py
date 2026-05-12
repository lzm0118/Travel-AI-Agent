#!/usr/bin/env python3
"""测试 LLM 返回编码并写入文件"""
import sys
import asyncio
sys.path.insert(0, 'backend')

async def test():
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    from app.core.config import get_qwen_config
    
    config = get_qwen_config()
    
    llm = ChatOpenAI(
        model="qwen-max",
        api_key=config.api_key,
        base_url=config.base_url,
        temperature=0.7,
    )
    
    messages = [HumanMessage(content="你好，请用中文介绍杭州西湖，100字以内")]
    response = await llm.ainvoke(messages)
    
    # 写入文件
    with open("d:\\AITest\\cursor_travel-agent\\llm_output.txt", "w", encoding="utf-8") as f:
        f.write(f"Type: {type(response.content)}\n")
        f.write(f"Repr: {repr(response.content)}\n\n")
        f.write(f"Content:\n{response.content}\n")
    
    print("Output written to llm_output.txt")

if __name__ == "__main__":
    asyncio.run(test())
