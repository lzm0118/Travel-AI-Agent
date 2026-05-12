"""
智能旅游助手 - 主入口
FastAPI 应用启动文件
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 添加项目根目录到路径
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import JSONResponse as StarletteJSONResponse
from loguru import logger
import uvicorn

from .core.config import get_settings, get_yaml_config
from .api import router, handle_websocket
from .tools import get_all_tools


# 配置日志
def setup_logging():
    """配置日志"""
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "travel_agent.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        encoding="utf-8"
    )
    
    logger.add(
        sys.stdout,
        level="DEBUG" if get_settings().debug else "INFO"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时执行初始化，关闭时执行清理
    """
    # 启动事件
    logger.info("=" * 50)
    logger.info("智能旅游助手服务启动中...")
    logger.info("=" * 50)
    
    # 加载配置
    settings = get_settings()
    yaml_config = get_yaml_config()
    
    logger.info(f"应用名称: {settings.app_name}")
    logger.info(f"版本: {settings.app_version}")
    logger.info(f"调试模式: {settings.debug}")
    
    # 初始化工具
    try:
        tools = get_all_tools()
        logger.info(f"已加载 {len(tools)} 个工具")
        for name in tools.keys():
            logger.info(f"  - {name}")
    except Exception as e:
        logger.error(f"工具加载失败: {e}")
    
    # 创建数据目录
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    
    logger.info("服务启动完成，等待请求...")
    logger.info(f"API 文档: http://{settings.host}:{settings.port}/docs")
    
    yield
    
    # 关闭事件
    logger.info("=" * 50)
    logger.info("智能旅游助手服务关闭中...")
    logger.info("=" * 50)
    
    # 持久化数据
    try:
        from .memory import get_user_profile_manager
        profile_mgr = get_user_profile_manager()
        await profile_mgr.persist()
        logger.info("用户画像数据已持久化")
    except Exception as e:
        logger.error(f"数据持久化失败: {e}")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        FastAPI: 应用实例
    """
    settings = get_settings()
    
    # 自定义 JSONResponse，支持中文编码
    class CustomJSONResponse(StarletteJSONResponse):
        media_type = "application/json"
        
        def render(self, content) -> bytes:
            import json
            return json.dumps(content, ensure_ascii=False, indent=None, separators=(",", ":")).encode("utf-8")
    
    app = FastAPI(
        title=settings.app_name,
        description="基于 LangChain 和 LangGraph 的一站式旅游陪伴智能体",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        default_response_class=CustomJSONResponse
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(router)
    
    # WebSocket 端点
    @app.websocket("/ws/chat/{session_id}")
    async def websocket_endpoint(
        websocket: WebSocket,
        session_id: str,
        user_id: str = None
    ):
        """WebSocket 聊天端点"""
        await handle_websocket(websocket, session_id, user_id)
    
    # 根路径
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """根路径 - 返回简单的 HTML 欢迎页面"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{settings.app_name}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                }}
                .container {{
                    background: rgba(255,255,255,0.1);
                    padding: 40px;
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }}
                h1 {{
                    margin-bottom: 20px;
                }}
                .links {{
                    margin-top: 30px;
                }}
                .links a {{
                    display: inline-block;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    padding: 12px 24px;
                    margin: 10px 10px 0 0;
                    border-radius: 8px;
                    text-decoration: none;
                    transition: background 0.3s;
                }}
                .links a:hover {{
                    background: rgba(255,255,255,0.3);
                }}
                .version {{
                    opacity: 0.8;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✈️ {settings.app_name}</h1>
                <p class="version">版本: {settings.app_version}</p>
                <p>基于 LangChain 1.0 + LangGraph 的一站式旅游陪伴智能体</p>
                
                <div class="links">
                    <a href="/docs">📚 API 文档 (Swagger)</a>
                    <a href="/redoc">📖 API 文档 (ReDoc)</a>
                    <a href="/api/health">🏥 健康检查</a>
                </div>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                    <h3>核心功能</h3>
                    <ul>
                        <li>🗺️ 智能行程规划</li>
                        <li>🔍 高德地图 POI 搜索</li>
                        <li>🌤️ 实时天气查询</li>
                        <li>🌐 联网搜索最新资讯</li>
                        <li>🧠 记忆系统 & 用户画像</li>
                        <li>🔌 MCP/A2A 协议支持</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
    
    # MCP SSE 端点
    @app.get("/mcp/sse")
    async def mcp_sse():
        """MCP Server-Sent Events 端点"""
        from fastapi.responses import StreamingResponse
        from .core import get_mcp_sse_handler
        import asyncio
        import uuid
        
        handler = get_mcp_sse_handler()
        client_id = str(uuid.uuid4())
        
        async def event_stream():
            async for event in handler.handle_connect(client_id):
                yield event
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream"
        )
    
    return app


def main():
    """
    主入口函数
    用于命令行启动
    """
    setup_logging()
    
    settings = get_settings()
    
    # 创建应用
    app = create_app()
    
    # 启动服务
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else None,
        log_level=settings.log_level.lower()
    )


# 应用实例（用于 Gunicorn/Uvicorn 直接导入）
app = create_app()


if __name__ == "__main__":
    main()
