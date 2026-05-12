#!/usr/bin/env python3
"""测试 Agent 输出"""
import sys
import asyncio
sys.path.insert(0, 'backend')

async def test():
    from app.agents import get_travel_agent
    agent = get_travel_agent()
    result = await agent.chat('你好，请介绍一下杭州西湖', 'test-py')
    print('=== Result ===')
    print(f"Success: {result.get('success')}")
    msg = result.get('message', '')
    print(f"Message type: {type(msg)}")
    print(f"Message repr: {repr(msg)[:300]}")
    if msg:
        print(f"First 100 chars: {msg[:100]}")

if __name__ == "__main__":
    asyncio.run(test())
