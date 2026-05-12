# 智能旅游助手 (Travel AI Agent)

这是一款面向个人游客的智能旅游助手，适合新手入门，提供全流程、个性化、高效便捷的旅游服务。基于 LangChain 1.0、LangGraph、MCP 协议和 A2A 协议构建，集成记忆系统，实现"一站式旅游陪伴"。

## 核心功能

### 1. 智能行程规划
- 根据用户偏好（预算、时间、兴趣）自动生成个性化行程
- 支持自由行和跟团游两种模式
- 实时调整行程，灵活应对变化

### 2. 目的地探索
- 高德地图 POI 搜索：景点、餐厅、酒店、购物等
- 智能推荐热门景点和隐藏 gems
- 实时天气查询与出行建议

### 3. 实时旅游助手
- 联网搜索最新旅游资讯
- 路线规划与导航辅助
- 紧急情况应对建议

### 4. 记忆系统
- 记住用户偏好和历史行程
- 持续学习优化推荐
- 多轮对话上下文保持

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   聊天界面   │  │  行程展示   │  │    地图/POI 展示     │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API 层 (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   对话接口   │  │  工具调用   │  │    MCP/A2A 协议     │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent 层 (LangGraph)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │  意图识别    │  │  任务规划   │  │    工具执行/结果汇总 │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      工具层 (Tools)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │ 高德POI搜索  │  │ 高德天气    │  │    联网搜索         │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      模型层 (LLM)                            │
│  ┌─────────────┐  ┌─────────────┐                            │
│  │  Qwen 系列   │  │   智谱      │                            │
│  └─────────────┘  └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

## 项目结构

```
travel-ai-agent/
├── README.md                    # 项目说明文档
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量示例
├── backend/                     # 后端代码
│   ├── app/
│   │   ├── agents/             # Agent 实现
│   │   │   ├── travel_agent.py # 旅游助手主 Agent
│   │   │   ├── itinerary_planner.py  # 行程规划 Agent
│   │   │   └── emergency_handler.py  # 应急处理 Agent
│   │   ├── api/                # API 接口
│   │   │   ├── routes.py       # 路由定义
│   │   │   └── websocket.py    # WebSocket 实时通信
│   │   ├── core/               # 核心组件
│   │   │   ├── config.py       # 配置管理
│   │   │   ├── mcp_server.py   # MCP 协议服务
│   │   │   └── a2a_server.py   # A2A 协议服务
│   │   ├── memory/             # 记忆系统
│   │   │   ├── conversation_memory.py  # 对话记忆
│   │   │   ├── user_profile.py # 用户画像
│   │   │   └── vector_store.py # 向量存储
│   │   ├── models/             # 数据模型
│   │   │   ├── schemas.py      # Pydantic 模型
│   │   │   └── llm_config.py   # LLM 配置
│   │   └── tools/              # 工具集
│   │       ├── amap_tools.py   # 高德地图工具
│   │       ├── search_tools.py   # 联网搜索工具
│   │       └── base_tool.py    # 工具基类
│   ├── config/                 # 配置文件
│   │   └── settings.yaml       # 应用配置
│   └── tests/                  # 测试代码
├── frontend/                    # 前端代码 (Vue 3)
│   ├── src/
│   │   ├── components/         # 组件
│   │   │   ├── Chat.vue        # 聊天组件
│   │   │   ├── Itinerary.vue   # 行程展示
│   │   │   └── Map.vue         # 地图组件
│   │   ├── views/              # 视图页面
│   │   │   ├── Home.vue        # 首页
│   │   │   └── ChatView.vue    # 对话页面
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── api/                # API 调用
│   │   └── utils/              # 工具函数
│   ├── package.json
│   └── vite.config.js
└── docs/                       # 文档
    └── api.md                  # API 文档
```

## 快速开始

### 环境要求

- Python 3.13.12
- Node.js 18+
- Conda (推荐)

### 后端部署

#### 1. 创建 Conda 虚拟环境

```bash
# 创建虚拟环境
conda create -n travel-agent python=3.13.12 -y

# 激活虚拟环境
conda activate travel-agent

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，填写必要的 API 密钥
# 必填项：
# - QWEN_API_KEY: 通义千问 API 密钥
# - ZHIPU_API_KEY: 智谱 AI API 密钥
# - AMAP_KEY: 高德地图 API 密钥
# - BING_SEARCH_KEY: 必应搜索 API 密钥（可选，DuckDuckGo免费搜索作为默认）
```

#### 3. 启动后端服务

```bash
# 进入后端目录
cd backend

# 启动服务
python -m app.main
```

服务将启动在 `http://localhost:8000`

### 前端部署

#### 1. 安装依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

#### 2. 启动开发服务器

```bash
npm run dev
```

前端将启动在 `http://localhost:5173`

### Docker 部署（可选）

```bash
# 构建并启动所有服务
docker-compose up -d
```

## 使用指南

### 基本对话

1. 打开前端页面 `http://localhost:5173`
2. 在输入框中输入您的旅游相关问题
3. 例如：
   - "我想去杭州玩3天，帮我规划一下行程"
   - "杭州有什么好吃的推荐？"
   - "明天北京的天气怎么样？"

### 工具调用示例

助手会自动调用相应工具来回答您的问题：

- **POI 搜索**: "杭州西湖附近有什么酒店？"
- **天气查询**: "查询上海未来3天的天气"
- **联网搜索**: "2024年杭州有什么新开的景点？"

### 记忆功能

助手会记住：
- 您的旅游偏好（预算、出行方式、兴趣点）
- 历史对话内容
- 已规划的行程

## API 文档

### REST API

- `POST /api/chat` - 发送对话消息
- `GET /api/itinerary/{id}` - 获取行程详情
- `POST /api/tools/execute` - 执行工具调用

### WebSocket

- `ws://localhost:8000/ws/chat` - 实时对话流

详细 API 文档请参考 [docs/api.md](docs/api.md)

## 配置说明

### 模型配置 (backend/config/settings.yaml)

```yaml
llm:
  default_model: "qwen-max"  # 默认模型
  fallback_model: "glm-4"    # 备用模型
  temperature: 0.7
  max_tokens: 4096

models:
  qwen:
    api_key: "${QWEN_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/api/v1"
  
  zhipu:
    api_key: "${ZHIPU_API_KEY}"
    base_url: "https://open.bigmodel.cn/api/paas/v4"
```

### 工具配置

```yaml
tools:
  amap:
    key: "${AMAP_KEY}"
    base_url: "https://restapi.amap.com/v3"
  
  search:
    provider: "bing"  # bing(国内可访问), serper(需要翻墙)
    timeout: 30
    max_results: 10
```

## 开发计划

- [x] 基础架构搭建
- [x] 核心 Agent 实现
- [x] 工具集成（高德、搜索）
- [x] 记忆系统
- [x] MCP/A2A 协议支持
- [x] 前端界面
- [ ] 语音交互
- [ ] 多语言支持
- [ ] 移动端适配优化



## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 [Apache 2.0](LICENSE) 许可证

## 致谢

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat)
- [Qwen](https://github.com/QwenLM/Qwen)
- [智谱 AI](https://github.com/THUDM/ChatGLM-6B)

## 联系我们

- 邮箱：1035597381qq.com

---

**让每一次旅行都成为难忘的回忆！** ✈️ 🌍 🎒
