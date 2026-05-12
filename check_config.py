#!/usr/bin/env python3
"""
配置检查脚本
用于排查 API Key 配置问题
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))


def check_env_file():
    """检查 .env 文件"""
    print("=" * 60)
    print("检查 .env 文件")
    print("=" * 60)
    
    env_path = Path(".env")
    if not env_path.exists():
        print("[X] .env 文件不存在！")
        print("   请复制 .env.example 为 .env 并配置")
        return False
    
    print(f"[OK] .env 文件存在: {env_path.absolute()}")
    
    # 读取并显示配置（隐藏部分密钥）
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("\n.env 文件内容预览：")
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            if 'KEY' in line or 'SECRET' in line:
                # 隐藏密钥的大部分内容
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    if value and not value.startswith('your_'):
                        masked = value[:8] + '****' if len(value) > 8 else '****'
                        print(f"  {key}={masked}")
                    else:
                        print(f"  [X] {key}=未配置（仍是示例值）")
            else:
                print(f"  {line}")
    
    return True


def check_pydantic_config():
    """检查 Pydantic 配置读取"""
    print("\n" + "=" * 60)
    print("检查 Pydantic 配置读取")
    print("=" * 60)
    
    try:
        from app.core.config import get_amap_config, get_search_config, get_qwen_config
        
        # 检查高德配置
        print("\n高德地图配置:")
        amap_config = get_amap_config()
        if amap_config.key:
            masked = amap_config.key[:8] + '****' if len(amap_config.key) > 8 else '****'
            print(f"  [OK] AMAP_KEY: {masked}")
        else:
            print(f"  [X] AMAP_KEY: 未读取到")
        print(f"  - Base URL: {amap_config.base_url}")
        
        # 检查搜索配置
        print("\n搜索配置:")
        search_config = get_search_config()
        print(f"  - Provider: {search_config.provider}")
        if search_config.api_key:
            masked = search_config.api_key[:8] + '****' if len(search_config.api_key) > 8 else '****'
            print(f"  [OK] BING_SEARCH_KEY: {masked}")
        else:
            print(f"  [INFO] BING_SEARCH_KEY: 未配置（使用 DuckDuckGo 免费搜索）")
        
        # 检查 Qwen 配置
        print("\n通义千问配置:")
        qwen_config = get_qwen_config()
        if qwen_config.api_key:
            masked = qwen_config.api_key[:8] + '****' if len(qwen_config.api_key) > 8 else '****'
            print(f"  [OK] QWEN_API_KEY: {masked}")
        else:
            print(f"  [X] QWEN_API_KEY: 未读取到")
            
    except Exception as e:
        print(f"[X] 配置读取失败: {e}")
        import traceback
        traceback.print_exc()


def check_tools():
    """检查工具初始化"""
    print("\n" + "=" * 60)
    print("检查工具初始化状态")
    print("=" * 60)
    
    try:
        from app.tools import get_all_tools
        
        tools = get_all_tools()
        
        print(f"\n已加载 {len(tools)} 个工具：")
        for name, tool in tools.items():
            status = "[OK] 已启用" if tool.enabled else "[X] 未启用"
            print(f"  {name}: {status}")
            if not tool.enabled:
                print(f"    提示: {tool.name} 需要配置 API Key")
                
    except Exception as e:
        print(f"[X] 工具检查失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("\n智能旅游助手 - 配置检查工具\n")
    
    # 检查当前目录
    print(f"当前工作目录: {Path.cwd()}")
    print(f"项目根目录: {Path(__file__).parent.absolute()}")
    
    # 执行检查
    check_env_file()
    check_pydantic_config()
    check_tools()
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)
    print("\n提示:")
    print("1. 如果 .env 文件中的值仍是 'your_xxx_here'，请替换为实际 API Key")
    print("2. 确保 .env 文件在项目根目录（与 README.md 同级）")
    print("3. 修改 .env 后需要重启服务")
    print("4. DuckDuckGo 搜索无需 API Key，是默认选项")


if __name__ == "__main__":
    main()
