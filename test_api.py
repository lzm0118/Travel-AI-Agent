#!/usr/bin/env python3
"""测试 API 返回编码"""
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "你好，请介绍一下杭州西湖",
    "session_id": "py-test-001"
}

headers = {"Content-Type": "application/json"}

response = requests.post(url, json=data, headers=headers, timeout=60)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"\nRaw response (first 500 chars):")
print(response.text[:500])

result = response.json()
print(f"\n\nParsed content:")
print(result["message"]["content"][:200])
