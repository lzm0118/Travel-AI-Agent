#!/usr/bin/env python3
"""
智能旅游助手 - 启动脚本
一键启动前后端服务
"""
import subprocess
import sys
import os
import argparse
import time
import signal
from pathlib import Path

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    """打印启动横幅"""
    banner = f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                    智能旅游助手启动器                        ║
║                   Travel AI Agent Launcher                  ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}
"""
    print(banner)


def check_python_version():
    """检查 Python 版本"""
    if sys.version_info < (3, 13):
        print(f"{Colors.WARNING}警告: 推荐使用 Python 3.13+，当前版本: {sys.version}{Colors.ENDC}")
        return False
    print(f"{Colors.OKGREEN}✓ Python 版本检查通过: {sys.version}{Colors.ENDC}")
    return True


def check_conda_env():
    """检查是否在 conda 环境中"""
    conda_prefix = os.environ.get('CONDA_PREFIX')
    if conda_prefix:
        env_name = os.path.basename(conda_prefix)
        print(f"{Colors.OKGREEN}✓ 当前 Conda 环境: {env_name}{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.WARNING}⚠ 未检测到 Conda 环境，建议激活环境后运行{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  提示: conda activate travel-agent{Colors.ENDC}")
        return False


def start_backend(port=8000, reload=False):
    """启动后端服务"""
    print(f"\n{Colors.OKBLUE}▶ 启动后端服务 (端口: {port})...{Colors.ENDC}")
    
    backend_dir = Path(__file__).parent / "backend"
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 等待服务启动
        for line in iter(process.stdout.readline, ''):
            print(f"{Colors.OKCYAN}[后端] {line.strip()}{Colors.ENDC}")
            if "Application startup complete" in line or "Uvicorn running" in line:
                print(f"{Colors.OKGREEN}✓ 后端服务启动成功: http://localhost:{port}{Colors.ENDC}")
                break
        
        return process
        
    except Exception as e:
        print(f"{Colors.FAIL}✗ 后端启动失败: {e}{Colors.ENDC}")
        return None


def start_frontend(port=5173):
    """启动前端服务"""
    print(f"\n{Colors.OKBLUE}▶ 启动前端服务 (端口: {port})...{Colors.ENDC}")
    
    frontend_dir = Path(__file__).parent / "frontend"
    
    # 检查是否需要安装依赖
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print(f"{Colors.WARNING}⚠ 未检测到 node_modules，正在安装依赖...{Colors.ENDC}")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True
            )
            print(f"{Colors.OKGREEN}✓ 前端依赖安装完成{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}✗ 依赖安装失败: {e}{Colors.ENDC}")
            return None
    
    cmd = ["npm", "run", "dev", "--", "--port", str(port)]
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 等待服务启动
        for line in iter(process.stdout.readline, ''):
            print(f"{Colors.OKCYAN}[前端] {line.strip()}{Colors.ENDC}")
            if "Local:" in line or "VITE" in line:
                print(f"{Colors.OKGREEN}✓ 前端服务启动成功: http://localhost:{port}{Colors.ENDC}")
                break
        
        return process
        
    except Exception as e:
        print(f"{Colors.FAIL}✗ 前端启动失败: {e}{Colors.ENDC}")
        return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能旅游助手启动脚本")
    parser.add_argument("--backend-only", action="store_true", help="仅启动后端")
    parser.add_argument("--frontend-only", action="store_true", help="仅启动前端")
    parser.add_argument("--backend-port", type=int, default=8000, help="后端端口")
    parser.add_argument("--frontend-port", type=int, default=5173, help="前端端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")
    
    args = parser.parse_args()
    
    print_banner()
    
    # 环境检查
    check_python_version()
    check_conda_env()
    
    processes = []
    
    try:
        # 启动后端
        if not args.frontend_only:
            backend_process = start_backend(args.backend_port, args.reload)
            if backend_process:
                processes.append(backend_process)
                time.sleep(2)
        
        # 启动前端
        if not args.backend_only:
            frontend_process = start_frontend(args.frontend_port)
            if frontend_process:
                processes.append(frontend_process)
        
        # 打印访问信息
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}")
        print("=" * 60)
        print("  服务已启动!")
        if not args.frontend_only:
            print(f"  后端 API: http://localhost:{args.backend_port}")
            print(f"  API 文档: http://localhost:{args.backend_port}/docs")
        if not args.backend_only:
            print(f"  前端页面: http://localhost:{args.frontend_port}")
        print("=" * 60)
        print(f"{Colors.ENDC}\n")
        
        print(f"{Colors.WARNING}按 Ctrl+C 停止服务{Colors.ENDC}")
        
        # 等待进程
        while True:
            for process in processes:
                ret = process.poll()
                if ret is not None:
                    print(f"\n{Colors.FAIL}服务进程已退出 (返回码: {ret}){Colors.ENDC}")
                    return
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}正在停止服务...{Colors.ENDC}")
        for process in processes:
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()
        print(f"{Colors.OKGREEN}✓ 服务已停止{Colors.ENDC}")


if __name__ == "__main__":
    main()
