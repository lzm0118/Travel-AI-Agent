#!/usr/bin/env python3
"""测试 API 返回编码并写入文件"""
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "你好，请用中文介绍杭州西湖，50字以内",
    "session_id": "api-file-test"
}

headers = {"Content-Type": "application/json"}

response = requests.post(url, json=data, headers=headers, timeout=60)

# 原始响应写入文件
with open("d:\\AITest\\cursor_travel-agent\\api_response_raw.txt", "wb") as f:
    f.write(response.content)

# 解析后的内容
result = response.json()
with open("d:\\AITest\\cursor_travel-agent\\api_response_parsed.txt", "w", encoding="utf-8") as f:
    f.write(f"Status: {response.status_code}\n")
    f.write(f"Content-Type: {response.headers.get('content-type')}\n\n")
    f.write(f"Raw (first 500 bytes):\n{response.content[:500]}\n\n")
    f.write(f"Parsed content:\n{result['message']['content']}\n")

print("API responses written to files")
