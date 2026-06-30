# 知识助手 - 架构设计

> 基于 LangGraph 的 RAG 问答系统，支持知识库检索、联网搜索和记忆管理。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│         ChatPage | DocumentsPage | MemoryPage           │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    API Layer (FastAPI)                    │
│    /api/langgraph | /api/documents | /api/memory         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│               LangGraph Agent (核心)                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Agent Loop                                      │    │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐     │    │
│  │  │ agent   │───►│ tools   │───►│reflect  │     │    │
│  │  │ (LLM)   │◄───│ (执行)  │◄───│ (反思)  │     │    │
│  │  └─────────┘    └─────────┘    └─────────┘     │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                              │
│  ┌────────────────────────▼────────────────────────┐    │
│  │  Tools (工具)                                    │    │
│  │  - search_knowledge (RAG 检索)                   │    │
│  │  - web_search (联网搜索)                         │    │
│  │  - get_user_profile (用户画像)                   │    │
│  │  - save_memory / search_memory (记忆管理)        │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                              │
│  ┌────────────────────────▼────────────────────────┐    │
│  │  Checkpoint (SQLite 持久化)                      │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  Services Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ MemoryManager│  │ RAGRetriever│  │ WebSearch   │     │
│  │ (记忆管理)   │  │ (检索适配)  │  │ (Tavily)    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                Storage Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ ChromaDB    │  │  MongoDB    │  │   SQLite    │     │
│  │ (向量存储)   │  │ (文档存储)  │  │ (Checkpoint)│     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. LangGraph Agent

**位置**: `backend/app/langgraph_agent/`

**职责**: 智能决策、工具选择、多步推理

**图结构**:
```
START → agent → should_continue → tools → agent → ... → END
                    ↓
              reflection → agent
```

**特性**:
- 自动选择工具（RAG / Web Search / 记忆）
- 每 3 步反思一次，优化决策
- 支持多轮对话（Checkpoint 持久化）

---

### 2. RAG Pipeline

**位置**: `backend/app/retrieval/`

**流程**:
```
文档上传 → 解析 → 分块 → 向量化 → ChromaDB 存储
                              ↓
用户查询 → 向量检索 + BM25 → RRF 融合 → 结果
```

**组件**:
- `chunker.py` - 智能分块（Markdown 结构化 / 递归分块）
- `chroma_store.py` - ChromaDB 向量存储
- `hybrid_retriever.py` - 混合检索（BM25 + 向量）
- `fusion.py` - RRF 融合算法

---

### 3. 记忆系统

**位置**: `backend/app/memory/`

| 记忆类型 | 作用 | 存储方式 |
|---------|------|---------|
| CoreMemory | 用户画像、Agent 人设 | MongoDB |
| RecallMemory | 对话历史 | SQLite Checkpoint |
| ArchivalMemory | 用户笔记、学习记录 | ChromaDB |

---

### 4. Web Search

**位置**: `backend/app/services/web_search.py`

**API**: Tavily AI Search

**特性**:
- 当知识库无结果时自动触发
- 返回标题、URL、内容摘要
- 结果作为引用来源显示

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/langgraph/chat` | POST | LangGraph Agent 问答 |
| `/api/langgraph/chat/stream` | POST | 流式问答 |
| `/api/documents/` | GET | 文档列表 |
| `/api/documents/upload` | POST | 上传文档 |
| `/api/documents/{id}` | DELETE | 删除文档 |
| `/api/memory/profile` | GET/PUT | 用户画像 |
| `/api/memory/entries` | GET/POST | 档案记忆 |
| `/api/memory/stats` | GET | 记忆统计 |

---

## 前端页面

| 页面 | 路由 | 功能 |
|------|------|------|
| ChatPage | `/` | 智能问答 |
| DocumentsPage | `/documents` | 文档管理 |
| MemoryPage | `/memory` | 记忆管理 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React + TypeScript + Tailwind CSS |
| 后端 | FastAPI + LangGraph |
| 向量库 | ChromaDB (HNSW) |
| 关系库 | MongoDB + SQLite |
| Embedding | BAAI/bge-small-zh-v1.5 (512维) |
| LLM | DeepSeek API |
| Web Search | Tavily API |

---

## 项目结构

```
education-agent/
├── backend/
│   ├── app/
│   │   ├── api/                    # API 端点
│   │   │   ├── langgraph.py        # LangGraph Agent API
│   │   │   ├── documents.py        # 文档管理 API
│   │   │   └── memory.py           # 记忆管理 API
│   │   │
│   │   ├── langgraph_agent/        # LangGraph Agent
│   │   │   ├── agent.py            # Agent 核心逻辑
│   │   │   ├── tools.py            # 工具定义
│   │   │   └── state.py            # 状态定义
│   │   │
│   │   ├── memory/                 # 记忆系统
│   │   │   ├── core_memory.py      # 核心记忆
│   │   │   ├── recall_memory.py    # 回忆记忆
│   │   │   ├── archival_memory.py  # 档案记忆
│   │   │   └── memory_manager.py   # 记忆管理器
│   │   │
│   │   ├── retrieval/              # 检索层
│   │   │   ├── chroma_store.py     # ChromaDB 存储
│   │   │   ├── hybrid_retriever.py # 混合检索
│   │   │   └── fusion.py           # 融合算法
│   │   │
│   │   ├── document/               # 文档处理
│   │   │   ├── parser.py           # 文档解析
│   │   │   ├── chunker.py          # 智能分块
│   │   │   └── uploader.py         # 文档上传
│   │   │
│   │   ├── services/               # 服务层
│   │   │   └── web_search.py       # Web Search
│   │   │
│   │   ├── shared_services.py      # 共享服务（单例）
│   │   └── main.py                 # 应用入口
│   │
│   └── data/
│       ├── chroma_db/              # ChromaDB 数据
│       └── langgraph_checkpoints.db # 会话持久化
│
└── frontend/
    └── src/
        ├── components/
        │   ├── Chat/               # 聊天页面
        │   ├── Documents/          # 文档页面
        │   └── Memory/             # 记忆页面
        └── services/
            └── api.ts              # API 服务
```

---

## 核心流程

### RAG 问答流程

```
用户问题
    ↓
LangGraph Agent
    ↓
┌─────────────────┐
│ search_knowledge │ → ChromaDB 向量检索
└────────┬────────┘
         ↓
┌─────────────────┐
│ web_search      │ → Tavily API（可选）
└────────┬────────┘
         ↓
┌─────────────────┐
│ LLM 生成答案    │ → DeepSeek API
└────────┬────────┘
         ↓
返回答案 + 引用来源
```

### 会话记忆流程

```
用户发送消息
    ↓
Checkpoint (SQLite)
    ↓
加载历史消息
    ↓
Agent 处理（包含历史上下文）
    ↓
保存新消息到 Checkpoint
```

---

## 部署

### 环境变量

```env
# AI 服务
AI_API_KEY=your_deepseek_api_key
AI_MODEL=deepseek-v4-flash

# Web Search
TAVILY_API_KEY=your_tavily_api_key

# 数据库
MONGODB_URI=mongodb://localhost:27017
```

### 启动命令

```bash
# 后端
cd backend
python -m uvicorn main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

---

## 未来优化

| 优先级 | 优化项 |
|--------|--------|
| 高 | 前端适配 LangGraph 流式响应 |
| 中 | 反思机制优化（消息压缩） |
| 中 | 多用户并发优化 |
| 低 | 更多工具集成（飞书、GitHub 等） |
