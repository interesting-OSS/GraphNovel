# LangNovel Studio（GraphNovel）

AI 驱动的小说创作工作室 —— 基于 LangGraph 多智能体协作，支持大纲规划、角色工坊、章节生成、伏笔管理、记忆检索。

## 🏗️ 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 19 + TypeScript + Vite + Ant Design 5 + xyflow |
| 后端 | Python 3.12 + FastAPI + LangGraph + LangChain |
| 数据库 | PostgreSQL 16 + pgvector（向量检索） |
| 缓存 / 队列 | Redis 7 + Celery（异步任务） |
| 向量存储 | ChromaDB（故事记忆嵌入） |
| AI 模型 | DeepSeek / Qwen / Kimi / Claude / Gemini（可切换） |
| 部署 | Docker Compose |

## 📦 环境要求

- **Docker** ≥ 24.x（含 Docker Compose v2）
- Windows 用户推荐使用 WSL2 + Docker Desktop

> 无需安装 Python、Node.js 或 PostgreSQL —— 全部在容器中运行。

## 🚀 快速启动

```bash
# 1. 进入项目目录
cd GraphNovel

# 2. 启动所有服务（首次启动会自动构建镜像，约需 5-10 分钟）
docker compose up -d --build

# 3. 查看运行状态
docker compose ps
```

启动后访问：

| 服务 | 地址 |
|------|------|
| **前端界面** | http://localhost:3000 |
| **API 文档 (Swagger)** | http://localhost:8000/docs |
| **API 备用** | http://localhost:8000 |

## ⚙️ 配置说明

在项目根目录的 `.env` 文件中配置 AI 模型和连接信息：

```bash
# ── 数据库（Docker 容器内自动连接，无需修改）──
DATABASE_URL=postgresql+asyncpg://langnovel:langnovel123@localhost:5432/langnovel_db

# ── AI 提供商 ──
OPENAI_API_KEY=sk-xxx          # DeepSeek（兼容 OpenAI 格式）
OPENAI_BASE_URL=https://api.deepseek.com/v1
QWEN_API_KEY=sk-xxx            # 通义千问（多模态：文+图）
KIMI_API_KEY=sk-xxx            # Moonshot/Kimi
ANTHROPIC_API_KEY=             # Claude（可选）
GOOGLE_API_KEY=                # Gemini（可选）

# ── 默认模型 ──
DEFAULT_AI_MODEL=deepseek-chat
DEFAULT_TEMPERATURE=0.7
```

> ⚠️ `.env` 默认已提供 DeepSeek / Qwen / Kimi 的 API Key，可直接使用。

## 🗄️ 数据库迁移

项目使用 Alembic 管理数据库版本，容器启动时自动执行迁移. 如需手动操作：

```bash
# 进入 backend 容器
docker exec -it graphnovel-backend-1 bash

# 生成迁移（模型变更后）
cd /app && alembic revision --autogenerate -m "描述"

# 升级到最新
alembic upgrade head

# 回退一个版本
alembic downgrade -1
```

详细说明见 [backend/alembic/README.md](backend/alembic/README.md)。

## 📁 项目结构

```
GraphNovel/
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── components/           # 组件（GraphViewer, CharacterGraph, FlowMonitor...）
│   │   ├── pages/                # 页面（ProjectList, CharacterWorkshop, Settings...）
│   │   ├── utils/                # 工具（SSE 流式客户端）
│   │   └── theme/                # 主题配置
│   └── package.json
├── backend/                      # Python 后端
│   ├── app/
│   │   ├── agents/               # AI 智能体（writer, editor, reviewer, analyst...）
│   │   ├── graphs/               # LangGraph 工作流
│   │   │   └── subgraphs/        # 子图（world_build, char_create, review, foreshadow...）
│   │   ├── models/               # SQLAlchemy 数据模型（19 个）
│   │   ├── api/                  # FastAPI 路由
│   │   ├── schemas/              # Pydantic 响应模型
│   │   ├── memory/               # 记忆管理器
│   │   ├── mcp/                  # MCP 插件系统
│   │   └── skills/               # AI Skill 定义（故事长写/短写/分析/扫描/去冗余）
│   ├── alembic/                  # 数据库迁移
│   ├── scripts/
│   │   └── entrypoint.sh         # 容器入口脚本
│   └── requirements.txt
├── docker-compose.yml            # 服务编排
├── Dockerfile                    # 多阶段构建
└── .env                          # 环境配置
```

## 🔧 常用命令

```bash
# 查看所有容器状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 查看前端日志
docker compose logs -f frontend

# 重启单个服务
docker compose restart backend

# 重启所有服务
docker compose restart

# 停止所有服务
docker compose down

# 停止并清空数据卷（⚠️ 会删除数据库）
docker compose down -v

# 重新构建并启动
docker compose up -d --build
```

## 🛠️ 本地开发（不使用 Docker）

如果需要热重载等开发体验，可以在宿主机直接运行：

```bash
# 启动基础设施（数据库 + Redis）
docker compose up -d db redis

# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install --legacy-peer-deps
npm run dev          # Vite 热重载 → http://localhost:5173
```

## 🐛 常见问题

### 容器启动失败

```bash
# 清理重建
docker compose down -v
docker compose up -d --build
```

### 数据库表不存在

容器启动时会自动执行 `alembic upgrade head`。如果跳过该步骤：

```bash
docker exec -it graphnovel-backend-1 bash
cd /app && alembic upgrade head
```

### API Key 失效

修改 `.env` 后重启后端即可：

```bash
docker compose restart backend celery_worker
```
