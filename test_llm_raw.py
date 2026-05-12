#!/usr/bin/env python3
"""直接测试 LLM 返回编码"""
import sys
import asyncio
sys.path.insert(0, 'backend')

async def test():
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    from app.core.config import get_qwen_config
    
    config = get_qwen_config()
    print(f"Base URL: {config.base_url}")
    print(f"API Key: {config.api_key[:10]}..." if config.api_key else "No API key")
    
    llm = ChatOpenAI(
        model="qwen-max",
        api_key=config.api_key,
        base_url=config.base_url,
        temperature=0.7,
    )
    
    messages = [HumanMessage(content="你好，请用中文介绍杭州西湖")]
    response = await llm.ainvoke(messages)
    
    print(f"\nResponse type: {type(response)}")
    print(f"Response content type: {type(response.content)}")
    print(f"Response content repr: {repr(response.content)[:300]}")
    print(f"Response content: {response.content[:200]}")

if __name__ == "__main__":
    asyncio.run(test())
