# 智能教育 Agent 系统详细设计文档

> 文档版本：v1.0
> 适用范围：教育培训 AI Agent 后端系统
> 代码仓库：`education-agent/backend`

## 目录

1. [系统概述](#1-系统概述)
2. [RAG 检索增强生成系统设计](#2-rag-检索增强生成系统设计)
3. [Agent 架构设计](#3-agent-架构设计)
4. [工具系统设计](#4-工具系统设计)
5. [Skill 技能系统设计](#5-skill-技能系统设计)
6. [系统有效性保障机制](#6-系统有效性保障机制)
7. [附录：关键配置参数与代码示例](#7-附录关键配置参数与代码示例)

---

## 1. 系统概述

### 1.1 项目定位

本系统是一个面向教育培训领域的 AI Agent 平台，以大语言模型（LLM）为核心推理引擎，结合 RAG 检索增强、知识图谱、学生状态建模、教学策略治理等技术，实现个性化、可解释、可观测的智能化教学辅导。

### 1.2 核心能力

| 能力 | 说明 |
|------|------|
| 概念讲解 | 基于检索到的课程知识与教学经验生成概念解释 |
| 智能出题 | 根据学生掌握度生成难度适配的练习题 |
| 答案反馈 | 判断正误并给出针对性讲解与鼓励 |
| 学习路径推荐 | 基于知识图谱前置关系与掌握度生成学习路径 |
| 学习洞察 | 每 10 次交互分析学习趋势，识别薄弱点 |
| 可观测追踪 | 完整记录 Agent 决策链路，支持问题排查 |

### 1.3 技术栈

| 层级 | 技术选型 |
|------|---------|
| Web 框架 | FastAPI |
| 数据库 | MongoDB（motor 异步驱动） |
| 缓存/会话 | 内存 + MongoDB |
| LLM 接入 | OpenAI 兼容 API（DeepSeek 等） |
| 向量检索 | 自研内存 VectorStore + TF-IDF / OpenAI Embedding |
| 认证 | JWT（PyJWT） |
| 日志 | loguru |
| 测试 | pytest + TestClient |

---

## 2. RAG 检索增强生成系统设计

### 2.1 知识源与数据模型

RAG 系统基于三类知识源构建：

#### 2.1.1 课程知识库（Course Knowledge）

定义于 [`app/knowledge/course.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/knowledge/course.py)。

```python
@dataclass
class KnowledgePoint:
    knowledge_id: str      # 知识点唯一标识
    course_id: str         # 所属课程
    chapter: str           # 章节
    topic: str             # 主题
    title: str             # 标题
    content: str           # 详细内容
    key_points: List[str]  # 关键要点
    difficulty: str        # easy/medium/hard
    tags: List[str]
    prerequisites: List[str]   # 前置知识点
    related_topics: List[str]  # 相关知识点
    examples: List[str]        # 示例代码
    common_errors: List[Dict]  # 常见错误
```

#### 2.1.2 教学知识库（Teaching Knowledge）

定义于 [`app/knowledge/teaching.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/knowledge/teaching.py)。

```python
@dataclass
class TeachingExperience:
    experience_id: str
    topic: str
    category: str          # best_practice / common_mistake / analogy / learning_path
    title: str
    content: str
    examples: List[str]
    effectiveness: float   # 0-1，有效性评分
    usage_count: int
    tags: List[str]
```

#### 2.1.3 知识图谱（Knowledge Graph）

定义于 [`app/knowledge/graph.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/knowledge/graph.py)。

```python
@dataclass
class KnowledgeNode:
    node_id: str
    topic: str
    description: str
    difficulty: str        # easy/medium/hard
    category: str
    tags: List[str]

@dataclass
class KnowledgeEdge:
    source_id: str
    target_id: str
    relation_type: str     # prerequisite / related / extends / applies_to
    weight: float
```

### 2.2 文档分块策略

本系统采用**结构化分块 + 业务语义分块**的混合策略，不采用传统的固定大小文本切分，原因如下：

1. 课程知识点本身是天然的高内聚单元（一个 `KnowledgePoint` 即一块）。
2. 教学经验条目（`TeachingExperience`）也是独立语义单元。
3. 知识图谱节点描述保持原子性，避免语义割裂。

#### 分块参数

| 知识源 | 分块单元 | 分块大小 | 重叠度 | 说明 |
|--------|---------|---------|--------|------|
| 课程知识 | `KnowledgePoint` | 单条记录 | 0 | 以知识点为原子单元 |
| 教学经验 | `TeachingExperience` | 单条记录 | 0 | 以经验条目为原子单元 |
| 知识图谱 | `KnowledgeNode.description` | 50-200 字符 | 0 | 节点描述保持完整 |
| 用户笔记 | `UserDocument` | 单条记录 | 0 | 用户上传的独立文档 |

#### 分块实现

```python
# ContextBuilder.build_vector_store 中的索引逻辑
for kp in self.course_knowledge._knowledge_points.values():
    content = f"{kp.title}: {kp.content}"
    self._vector_store.add(
        doc_id=f"kp_{kp.knowledge_id}",
        content=content,
        metadata={"source": "course_knowledge", "title": kp.title, "topic": kp.topic},
    )
```

### 2.3 向量库选型与配置

#### 2.3.1 选型说明

本系统采用**自研内存向量存储 `VectorStore`**，而非 ChromaDB、Milvus 等外部向量数据库。选型依据：

| 维度 | 自研 VectorStore | 外部向量数据库 |
|------|-----------------|---------------|
| 部署复杂度 | 零依赖，随应用启动 | 需额外部署服务 |
| 数据规模 | 适合 <10,000 条记录 | 适合大规模 |
| 查询性能 | O(n×d) 暴力搜索 | 近似最近邻，毫秒级 |
| 成本控制 | 无额外成本 | 可能需要付费服务 |
| 可控性 | 完全可控 | 依赖第三方 |

教学场景知识库规模通常较小（数百至数千条），自研方案在 simplicity 和 cost 上更优。

#### 2.3.2 索引结构

```python
class VectorStore:
    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model
        self._records: Dict[str, VectorRecord] = {}
```

- 内存中以字典形式存储 `VectorRecord`，键为 `doc_id`。
- 每个记录包含：`id`、`vector`、`content`、`metadata`。
- 搜索时全量计算余弦相似度，排序后返回 Top-K。

#### 2.3.3 相似度计算

采用**余弦相似度**：

```python
def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
```

### 2.4 Embedding 模型

定义于 [`app/retrieval/embeddings.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/retrieval/embeddings.py)。

#### 2.4.1 TF-IDF 本地模型（默认）

```python
class TFIDFModel(EmbeddingModel):
    def __init__(self, max_features: int = 5000):
        self.max_features = max_features
        self._vocabulary: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
```

分词策略：

```python
def _tokenize(self, text: str) -> List[str]:
    text = text.lower()
    english_words = re.findall(r'[a-z]+', text)
    chinese_chars = re.findall(r'[一-鿿]', text)
    bigrams = []
    for i in range(len(chinese_chars) - 1):
        bigrams.append(chinese_chars[i] + chinese_chars[i + 1])
    return english_words + chinese_chars + bigrams
```

特点：
- 英文按单词提取
- 中文按单字 + 二元组提取
- 适合关键词匹配，但不理解深层语义

#### 2.4.2 OpenAI 兼容 Embedding（可选）

```python
class OpenAIEmbedding(EmbeddingModel):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small",
                 base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._dimension = 1536
```

工厂函数按配置自动选择：

```python
def create_embedding_model(api_key=None, model_name=None, base_url=None):
    if api_key and model_name:
        return OpenAIEmbedding(api_key=api_key, model=model_name, base_url=base_url)
    return TFIDFModel(max_features=5000)
```

### 2.5 检索机制实现

#### 2.5.1 多层检索流程

RAG 检索在 `ContextBuilder._build_knowledge()` 中实现，流程如下：

```
用户输入
  │
  ├─> 1. 关键词搜索课程知识（course_knowledge.search）
  │
  ├─> 2. 向量语义搜索（vector_store.search, top_k=3, min_score=0.1）
  │
  ├─> 3. 教学知识最佳实践（teaching_knowledge.get_best_practices）
  │
  ├─> 4. 知识图谱相关节点（knowledge_graph.find_node_by_topic）
  │
  └─> 5. 用户笔记搜索（knowledge_base.search_by_keyword）
```

#### 2.5.2 检索增强逻辑

1. **去重**：使用 `seen_titles` 集合避免重复标题内容。
2. **来源融合**：将课程知识、语义相关、教学建议、知识图谱、用户笔记拼接为统一字符串。
3. **长度截断**：每块内容截取前 100 字符，控制 Prompt 长度。

#### 2.5.3 混合检索器

定义于 [`app/retrieval/hybrid_search.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/retrieval/hybrid_search.py)。

```python
class HybridSearchRetriever(BaseRetriever):
    def __init__(self, vector_retrievers=None, graph_retriever=None, reranker=None):
        self.vector_retrievers = vector_retrievers or []
        self.graph_retriever = graph_retriever
        self.reranker = reranker or SimpleReranker()

    async def retrieve(self, query: str, limit: int = 5, filters: Dict = None):
        all_results = []
        # 1. 向量检索
        for retriever in self.vector_retrievers:
            all_results.extend(await retriever.retrieve(query, limit=limit))
        # 2. 图谱检索
        if self.graph_retriever:
            all_results.extend(await self.graph_retriever.retrieve(query, limit=limit))
        # 3. 去重
        unique_results = self._deduplicate(all_results)
        # 4. 重排
        return self.reranker.rerank(query, unique_results, limit)[:limit]
```

#### 2.5.4 重排序策略

定义于 [`app/retrieval/reranker.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/retrieval/reranker.py)。

当前实现 `SimpleReranker`：
- 按 `score` 降序
- 按来源可信度加权（course_knowledge > teaching_knowledge > knowledge_graph）
- 返回前 `limit` 条

预留 `LLMReranker` 接口，未来可接入 LLM 做语义重排。

### 2.6 与生成模块的集成

检索结果通过 `ContextBuilder` 注入 LLM Prompt：

```python
context["knowledge"] = await self._build_knowledge(user_input, state)
```

Skill 调用 `GenerateTextTool` 时，Prompt 中已包含知识上下文：

```python
prompt = f"""
## 检索到的相关知识
{knowledge_context}

## 用户问题
{user_input}

请基于以上知识生成回答。
"""
```

---

## 3. Agent 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                               │
│              FastAPI Routers (auth / teaching / admin)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                           │
│                   TeachingAgent.run()                           │
│  状态加载 → 策略决策 → 意图识别 → Skill 执行 → 评估 → 洞察    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Context      │    │ Policy       │    │ Lifecycle    │
│ Builder      │    │ Engine       │    │ Manager      │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Skill Engine │    │ Student      │    │ Memory       │
│              │    │ State        │    │ Manager      │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Tool System  │    │ Evaluation   │    │ Retrieval    │
│              │    │ & Learning   │    │ Layer        │
└──────────────┘    └──────────────┘    └──────────────┘
        │                                           │
        │                                           ▼
        │                              ┌──────────────┐
        │                              │ RAG / Graph  │
        │                              │ / VectorStore│
        │                              └──────────────┘
        ▼
┌──────────────┐
│ LLM Provider │
│ (DeepSeek)   │
└──────────────┘
```

### 3.2 设计范式

本系统采用 **Tool-use + Skill-orchestration + State-machine** 的混合范式：

| 范式 | 采用方式 | 说明 |
|------|---------|------|
| ReAct | 部分采用 | Skill 内部可通过调用 Tool 进行推理-行动循环 |
| Plan-and-Execute | 未采用 | 教学任务通常较短，不需要复杂规划 |
| Tool-use | 核心 | Skill 调用 Tool 完成原子能力（生成、检索、状态更新） |
| State-machine | 核心 | Agent 生命周期通过 10 状态状态机管理 |
| Policy-based | 核心 | 策略引擎根据学生状态决定难度与策略 |

选择依据：
- 教育场景任务边界清晰（讲解/出题/反馈/复习），适合 Skill 模块化。
- 需要严格追踪学生状态，状态机更适合。
- Tool 抽象使通用能力可复用，Skill 抽象承载业务逻辑。

### 3.3 核心组件

#### 3.3.1 Agent Orchestrator（TeachingAgent）

定义于 [`app/agent/teaching_agent.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/agent/teaching_agent.py)。

核心职责：
- 串联完整教学链路
- 管理知识系统、嵌入模型、上下文构建器
- 处理异常并返回标准化响应
- 持久化可观测日志

完整执行链路：

```
start
  │
  ▼
load_state ──► 加载 StudentState + MemoryManager
  │
  ▼
policy ──► 根据掌握度/情绪决定推荐难度
  │
  ▼
intent ──► 基于关键词匹配选择 Skill
  │
  ▼
skill_execute ──► 调用 Skill.execute(context, user_input)
  │
  ▼
state_update ──► 更新并持久化学生状态
  │
  ▼
memory ──► 存储会话问答与长期记忆
  │
  ▼
evaluation ──► 评估本次交互质量
  │
  ▼
learning ──► 每 10 次交互生成学习洞察
  │
  ▼
optimization ──► 记录配置变更建议
  │
  ▼
completed
```

#### 3.3.2 学生状态模型（StudentState）

定义于 [`app/state/student_state_v2.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/state/student_state_v2.py)。

学生状态由五个子状态组成：

| 子状态 | 职责 | 文件 |
|--------|------|------|
| LearningState | 知识点掌握度、错题记录、学习历史 | `learning_state.py` |
| BehaviorState | 答题行为模式、响应时间、提示使用情况 | `behavior_state.py` |
| EmotionState | 信心水平、挫败感、参与度 | `emotion_state.py` |
| GoalState | 学习目标、进度、成就 | `goal_state.py` |
| SessionState | 当前会话上下文、当前题目 | `session_state.py` |

状态持久化采用**乐观锁**：

```python
class StudentState:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.version = 0  # 乐观锁版本号

    async def save(self, db):
        # CAS 校验：数据库版本必须等于当前版本
        if not await db.save_student_state(self.user_id, self.to_dict(), expected_version=self.version):
            raise ConcurrentUpdateError("状态已被其他请求更新")
        self.version += 1
```

#### 3.3.3 上下文构建器（ContextBuilder）

定义于 [`app/context/builder.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/context/builder.py)。

构建的上下文字段：

```python
context = {
    "system_prompt": "",      # 系统提示 + 技能特定提示
    "student_state": "",      # 学生状态摘要
    "memory": "",             # 会话/长期记忆
    "knowledge": "",          # RAG 检索结果
    "history": "",            # 对话历史
    "teaching_strategy": "",  # 动态教学策略
    "user_input": user_input,
}
```

#### 3.3.4 策略引擎（Policy Engine）

策略引擎根据学生状态决定推荐难度：

```python
def decide_difficulty(state: StudentState) -> str:
    if state.emotion.get_frustration() == "high":
        return "easy"
    if state.should_challenge():
        return "hard"
    mastery = state.get_mastery(state.current_topic or "")
    if mastery < 0.3:
        return "easy"
    elif mastery > 0.8:
        return "hard"
    return "medium"
```

策略配置通过 `VersionedConfig` 管理，支持版本化与回滚。

#### 3.3.5 生命周期管理（Lifecycle）

定义于 [`app/models/lifecycle.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/models/lifecycle.py)。

10 个状态：

```python
class AgentStatus(Enum):
    IDLE = "idle"
    LOADING = "loading"
    POLICY_DECISION = "policy_decision"
    INTENT_RECOGNITION = "intent_recognition"
    EXECUTING = "executing"
    STATE_UPDATING = "state_updating"
    MEMORY_STORING = "memory_storing"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
```

状态转换由 `AgentLifecycle` 类控制，防止非法跳转。

#### 3.3.6 记忆管理（MemoryManager）

定义于 [`app/memory/manager.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/memory/manager.py)。

包含四层记忆：

| 记忆类型 | 作用 | 持久化 |
|----------|------|--------|
| Session Memory | 当前会话的问答历史、当前题目 | 可选持久化 |
| Long-term Memory | 关键概念、错题、学习模式 | MongoDB |
| User Profile | 专业、年级、学习偏好 | MongoDB |
| Knowledge Base | 用户上传的笔记/文档 | MongoDB |

#### 3.3.7 评估与学习洞察

- **Evaluator**：定义于 [`app/evaluation/evaluator.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/evaluation/evaluator.py)，基于学生状态、技能使用情况、响应内容计算交互得分。
- **LearningAnalyzer**：定义于 [`app/learning/analyzer.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/learning/analyzer.py)，每 10 次交互分析薄弱点并生成建议。

---

## 4. 工具系统设计

### 4.1 工具抽象层

定义于 [`app/tools/base.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/tools/base.py)。

```python
class ToolResult:
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {}

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult: pass

    def to_openai_function(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }
```

设计原则：
- Tool 是**原子能力**，与业务无关。
- 统一返回 `ToolResult(success, data, error)`。
- 支持 OpenAI Function Calling 格式转换。

### 4.2 工具注册与管理

定义于 [`app/tools/__init__.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/tools/__init__.py)。

```python
_tool_registry = {}

def register_tool(tool: Tool):
    _tool_registry[tool.name] = tool

def get_tool(name: str) -> Tool:
    return _tool_registry.get(name)

def get_all_tools() -> list:
    return list(_tool_registry.values())
```

所有工具在模块导入时注册：

```python
register_tool(SearchKnowledgeTool())
register_tool(GetTeachingSuggestionTool())
register_tool(GenerateTextTool())
register_tool(GenerateQuestionTool())
register_tool(GetStudentStateTool())
register_tool(UpdateStudentStateTool())
register_tool(SaveMemoryTool())
register_tool(CheckAnswerTool())
register_tool(AnalyzeErrorTool())
```

### 4.3 工具分类

| 类别 | 工具 | 功能 |
|------|------|------|
| 知识 | `SearchKnowledgeTool` | 检索课程/教学知识 |
| 知识 | `GetTeachingSuggestionTool` | 获取教学建议 |
| 生成 | `GenerateTextTool` | 调用 LLM 生成文本 |
| 生成 | `GenerateQuestionTool` | 调用 LLM 生成题目 |
| 状态 | `GetStudentStateTool` | 读取学生状态 |
| 状态 | `UpdateStudentStateTool` | 更新学生状态 |
| 状态 | `SaveMemoryTool` | 保存记忆 |
| 评估 | `CheckAnswerTool` | 判断答案正误 |
| 评估 | `AnalyzeErrorTool` | 分析错误原因 |

### 4.4 工具调用流程

Skill 通过 `get_tool(name)` 获取工具实例并调用：

```python
class ConceptLessonSkill(Skill):
    async def execute(self, context, user_input):
        # 1. 提取概念
        concept = extract_topic(user_input)

        # 2. 检索知识
        search_tool = self.get_tool("search_knowledge")
        search_result = await search_tool.execute(query=concept)

        # 3. 生成讲解
        generate_tool = self.get_tool("generate_text")
        prompt = build_prompt(concept, search_result.data)
        result = await generate_tool.execute(prompt=prompt)

        return SkillResult(content=result.data["text"], skill_name=self.name)
```

### 4.5 参数解析与结果处理

- 参数通过 `**kwargs` 传递，Schema 由 `input_schema` 定义。
- 结果统一包装为 `ToolResult`。
- Skill 需根据 `result.success` 决定后续逻辑，失败时可触发 fallback。

---

## 5. Skill 技能系统设计

### 5.1 Skill 抽象层

定义于 [`app/skills_v2/base.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/skills_v2/base.py)。

```python
class SkillContext:
    def __init__(self, user_id, state, tools=None, metadata=None,
                 memory_manager=None, context_builder=None):
        self.user_id = user_id
        self.state = state
        self.tools = tools or {}
        self.metadata = metadata or {}
        self.memory_manager = memory_manager
        self.context_builder = context_builder

class SkillResult:
    def __init__(self, content: str, skill_name: str,
                 should_continue: bool = False, metadata: Dict = None):
        self.content = content
        self.skill_name = skill_name
        self.should_continue = should_continue
        self.metadata = metadata or {}

class Skill(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    def triggers(self) -> list:
        return []

    @abstractmethod
    async def execute(self, context: SkillContext, user_input: str) -> SkillResult: pass

    def get_tool(self, name: str) -> Optional[Tool]:
        return get_tool(name)
```

设计原则：
- Skill 是**业务任务模块**，完成一个完整教学任务。
- Skill 调用 Tool 完成原子操作。
- Skill 包含触发条件，用于意图识别。

### 5.2 Skill 分类

```
Skill V2
├── 练习辅导
│   ├── PracticeSessionSkill    （出题练习）
│   └── AnswerFeedbackSkill     （答案反馈）
├── 概念讲解
│   ├── ConceptLessonSkill      （系统概念讲解）
│   └── QuickExplainSkill       （快速解释）
├── 复习巩固
│   ├── ReviewSessionSkill      （复习会话）
│   └── SpacedRepetitionSkill   （间隔重复）
└── 学习回顾
    ├── LearningReviewSkill     （学习报告）
    └── QuickSummarySkill       （快速总结）
```

### 5.3 技能触发与选择

定义于 [`app/skills_v2/__init__.py`](file:///d:/my-code-space/projects/claude-learning/education-agent/backend/app/skills_v2/__init__.py)。

意图识别采用**关键词匹配**，按 trigger 长度排序优先匹配更精确的：

```python
def find_skill_by_intent(intent: str) -> Skill:
    intent_lower = intent.lower()
    matches = []
    for skill in _skill_registry.values():
        for trigger in skill.triggers:
            if trigger in intent_lower:
                matches.append((len(trigger), skill))

    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1]
    return None
```

示例触发条件：

```python
class PracticeSessionSkill(Skill):
    @property
    def triggers(self):
        return ["练习", "出题", "做题", "考考", "测试", "给我出", "来一道"]

class ConceptLessonSkill(Skill):
    @property
    def triggers(self):
        return ["什么是", "解释", "讲解", "怎么理解", "是什么意思", "帮我讲讲"]
```

### 5.4 Skill 实现示例

`ConceptLessonSkill` 的核心流程：

```python
class ConceptLessonSkill(Skill):
    @property
    def name(self): return "concept_lesson"

    @property
    def triggers(self):
        return ["什么是", "解释", "讲解", "怎么理解", "是什么意思", "帮我讲讲", "教我"]

    async def execute(self, context, user_input):
        # 1. 提取概念
        concept = extract_topic(user_input) or context.state.current_topic
        if not concept:
            return SkillResult("可以告诉我你想了解哪个概念吗？", self.name)

        # 2. 构建 Prompt 上下文
        prompt_info = await self._build_prompt(context, concept)

        # 3. 调用 LLM 生成讲解
        generate_tool = self.get_tool("generate_text")
        result = await generate_tool.execute(
            prompt=prompt_info["prompt"],
            style="encouraging",
            max_length=800,
        )

        if result.success:
            explanation = result.data.get("text", "")
        else:
            # LLM-free fallback
            explanation = await self._build_fallback_explanation(concept, context)

        return SkillResult(
            content=explanation,
            skill_name=self.name,
            should_continue=True,
            metadata={"concept": concept, "difficulty": prompt_info.get("difficulty")},
        )
```

### 5.5 技能调度机制

当前 Agent 采用**单 Skill 单轮执行**模式：

1. 每轮用户输入只选择一个 Skill 执行。
2. Skill 返回 `should_continue` 标志，指示是否期待用户继续回复。
3. 复杂任务（如出题后等待答案）通过会话记忆中的 `current_question` 跨请求保持上下文。

未来可扩展为**Skill 组合执行**：将多个 Skill 编排为工作流，例如 `概念讲解 → 出题 → 答案反馈`。

---

## 6. 系统有效性保障机制

### 6.1 设计决策依据

| 设计决策 | 依据 | 对比分析 |
|----------|------|---------|
| 自研 VectorStore 而非 ChromaDB | 教学知识库规模小、部署简单、无额外成本 | 大规模场景可迁移至 Milvus/Pinecone |
| TF-IDF 作为默认 Embedding | 无需 API Key、响应快、适合关键词匹配 | 语义理解弱于 OpenAI Embedding |
| Skill-Tool 分层 | 业务逻辑与通用能力解耦，便于扩展 | 比单一 Prompt 工程更可控 |
| 关键词意图识别 | 教学场景意图边界清晰，实现简单可靠 | 复杂开放域建议使用 LLM 分类 |
| 乐观锁状态更新 | 防止并发请求覆盖学生状态 | 替代方案：数据库 CAS 或分布式锁 |
| 版本化策略配置 | 支持 A/B 测试与回滚 | 比硬编码策略更灵活 |

### 6.2 性能优化策略

| 方面 | 策略 |
|------|------|
| 响应速度 | Skill 内缓存 `prompt_info`；`finalize` 避免重复构建 Prompt |
| 检索速度 | 向量库在内存中，TF-IDF 计算本地完成 |
| LLM 成本 | 默认 TF-IDF 不调用 Embedding API；合理设置 `max_length` |
| 数据库 | MongoDB 异步驱动（motor），避免阻塞事件循环 |
| 状态更新 | 乐观锁减少数据库事务开销 |
| 配置缓存 | `VersionedConfig` 缓存当前配置，避免频繁读取 |

### 6.3 容错与恢复机制

#### 6.3.1 LLM 调用失败

- `GenerateTextTool` 捕获异常并返回 `ToolResult(success=False, error=...)`。
- `ConceptLessonSkill` 在 LLM 失败时，基于知识图谱生成兜底回复。
- `PracticeSessionSkill` 在 LLM 失败时返回模板题目。

#### 6.3.2 数据库异常

- `TeachingAgent.run()` 顶层捕获异常，生命周期进入 `FAILED`。
- 即使失败也调用 `obs.persist()` 持久化 trace，便于排查。
- 数据库初始化失败时，知识库加载降级为内存空实例。

#### 6.3.3 状态并发冲突

- `StudentState.save()` 使用乐观锁（`expected_version`）。
- 版本冲突时抛出异常，上层可选择重试或返回提示。

#### 6.3.4 配置回滚

- `RollbackManager` 支持将 `VersionedConfig` 回滚到任意历史版本。
- `ChangeLog` 记录所有变更建议与人工审核状态。

### 6.4 测试保障

| 测试类型 | 数量 | 说明 |
|----------|------|------|
| 单元/集成测试 | 238 | 覆盖状态、记忆、检索、评估、优化等 |
| Mock 端到端测试 | 多个 | 验证完整 HTTP 链路 |
| 真实 LLM 端到端测试 | 1 | 验证真实 LLM 概念讲解与出题 |
| 回归测试 | 10 | 针对关键 bug 修复 |

---

## 7. 附录：关键配置参数与代码示例

### 7.1 关键配置参数

| 参数 | 默认值 | 说明 | 位置 |
|------|--------|------|------|
| `AI_MODEL` | `deepseek-v4-flash` | 主 LLM 模型 | `.env` |
| `AI_API_KEY` | - | LLM API Key | `.env` |
| `AI_BASE_URL` | - | 自定义 API 地址 | `.env` |
| `TF-IDF max_features` | `5000` | 最大词汇表大小 | `embeddings.py` |
| 向量检索 `top_k` | `3` | 每次检索返回数量 | `builder.py` |
| 向量检索 `min_score` | `0.1` | 最低相似度阈值 | `builder.py` |
| 学习洞察触发间隔 | `10` | 每 10 次交互分析 | `teaching_agent.py` |
| 状态乐观锁 | - | CAS 校验 | `student_state_v2.py` |

### 7.2 核心代码示例

#### 7.2.1 构建完整上下文

```python
context = await context_builder.build(
    state=student_state,
    user_input="什么是递归？",
    skill_name="concept_lesson",
)
```

#### 7.2.2 调用 Skill

```python
skill = find_skill_by_intent("什么是递归？")
result = await skill.execute(context, "什么是递归？")
```

#### 7.2.3 向量搜索

```python
results = vector_store.search("递归", top_k=3, min_score=0.1)
for doc_id, score, meta in results:
    print(f"{doc_id}: {score:.3f} - {meta['title']}")
```

#### 7.2.4 学习路径生成

```python
service = LearningPathService(knowledge_graph)
path = service.generate_path("递归", student_state)
print(path.next_recommended.topic)
```

### 7.3 文件索引

| 模块 | 关键文件 |
|------|---------|
| Agent 主循环 | `app/agent/teaching_agent.py` |
| 生命周期 | `app/models/lifecycle.py` |
| 学生状态 | `app/state/student_state_v2.py` |
| 上下文构建 | `app/context/builder.py` |
| Skill 基类 | `app/skills_v2/base.py` |
| Skill 注册 | `app/skills_v2/__init__.py` |
| Tool 基类 | `app/tools/base.py` |
| Tool 注册 | `app/tools/__init__.py` |
| 向量存储 | `app/retrieval/vector_store.py` |
| Embedding | `app/retrieval/embeddings.py` |
| 混合检索 | `app/retrieval/hybrid_search.py` |
| 知识图谱 | `app/knowledge/graph.py` |
| 学习路径服务 | `app/services/learning_path.py` |
| 可观测日志 | `app/agent/teaching_agent.py` 中 `ObservabilityLogger` |

---

## 8. 总结

本智能教育 Agent 系统通过清晰的分层架构、RAG 检索增强、状态驱动的个性化策略、Skill-Tool 分离设计以及完善的可观测性机制，实现了教育场景下的智能化教学辅导。系统设计兼顾了可实施性与可维护性，适合技术团队理解、开发及长期演进。
