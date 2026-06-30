# 教育 Agent 实现计划

## 整体架构

```
用户输入
    ↓
┌─────────────────────────────────────────────────────────┐
│                    Agent Router                          │
│  简单请求 → 快速响应                                      │
│  复杂请求 → Agent Loop                                   │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│                    Agent Loop                            │
│  1. LLM 分析请求                                         │
│  2. LLM 选择工具（可多个）                                │
│  3. 执行工具                                             │
│  4. LLM 反思结果                                         │
│  5. 可能继续调用工具                                      │
│  6. 返回最终答案                                         │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│                    Tools (MCP)                           │
│  search_knowledge | generate_question | check_answer    │
│  record_error | grade_homework | get_learning_state     │
│  update_mastery | get_error_notebook | get_review       │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│                    Memory                                │
│  ShortTerm: 对话历史、当前题目、当前主题                   │
│  LongTerm: 掌握度、错误模式、学习历史、复习计划            │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
backend/app/core/
├── agent/
│   ├── __init__.py
│   ├── core.py           # Agent 核心循环
│   ├── router.py         # 请求路由（简单/复杂）
│   └── prompts.py        # 系统提示
├── tools/
│   ├── __init__.py
│   ├── base.py           # Tool 基类 + MCP 协议
│   ├── registry.py       # 工具注册表
│   ├── executor.py       # 工具执行器
│   ├── knowledge.py      # 知识检索工具
│   ├── question.py       # 题目生成工具
│   ├── answer.py         # 答案检查工具
│   ├── error.py          # 错题记录工具
│   ├── homework.py       # 作业批改工具
│   ├── learning.py       # 学习状态工具
│   └── review.py         # 复习计划工具
├── memory/
│   ├── __init__.py
│   ├── short_term.py     # 短期记忆（对话内）
│   ├── long_term.py      # 长期记忆（跨会话）
│   └── manager.py        # 记忆管理器
└── llm/
    ├── __init__.py
    └── service.py        # LLM 服务（支持 Function Calling）
```

## 实现步骤

### Step 1: Tool 基类 + MCP 协议

```python
# tools/base.py
class Tool:
    name: str
    description: str
    input_schema: Dict
    output_schema: Dict

    async def execute(self, input: Dict) -> Dict
    def to_mcp_schema(self) -> Dict  # 转换为 MCP 格式
```

### Step 2: 工具注册表

```python
# tools/registry.py
class ToolRegistry:
    register(tool: Tool)
    get(name: str) -> Tool
    get_all() -> List[Tool]
    get_schemas() -> List[Dict]  # 给 LLM 用
```

### Step 3: 工具实现

将现有功能封装为工具：

```python
# tools/question.py
class GenerateQuestionTool(Tool):
    name = "generate_question"
    description = "生成一道练习题"

    async def execute(self, input):
        topic = input["topic"]
        difficulty = input.get("difficulty", "medium")
        # 调用现有的 generate_question 逻辑
        return await self._generate(topic, difficulty)
```

### Step 4: 记忆系统

```python
# memory/short_term.py
class ShortTermMemory:
    messages: List[Dict]        # 对话历史
    current_topic: str          # 当前主题
    current_question_id: str    # 当前题目
    recent_tools: List[str]     # 最近调用的工具

# memory/long_term.py
class LongTermMemory:
    mastery_level: Dict[str, float]    # 掌握度
    error_patterns: List[Dict]         # 错误模式
    learning_history: List[Dict]       # 学习历史
    review_schedule: Dict              # 复习计划
```

### Step 5: Agent Loop

```python
# agent/core.py
class Agent:
    async def run(self, user_input: str, user_id: str) -> str:
        # 1. 加载记忆
        memory = await self.load_memory(user_id)

        # 2. 构建消息
        messages = self.build_messages(user_input, memory)

        # 3. Agent Loop
        for i in range(MAX_ITERATIONS):
            response = await self.llm.chat(messages, tools=self.tools)

            if response.type == "final_answer":
                return response.content

            if response.type == "tool_call":
                results = await self.execute_tools(response.tool_calls)
                messages.append({"role": "tool", "content": results})

        return "抱歉，我无法完成这个任务。"
```

### Step 6: LLM 服务（支持 Function Calling）

```python
# llm/service.py
class LLMService:
    async def chat(self, messages, tools=None) -> LLMResponse:
        if tools:
            # 使用 Function Calling
            response = await self._call_with_tools(messages, tools)
        else:
            # 普通调用
            response = await self._call(messages)
        return response
```

### Step 7: Agent Router

```python
# agent/router.py
class AgentRouter:
    async def route(self, user_input: str, user_id: str) -> str:
        # 简单请求：问候、简单问答
        if self._is_simple(user_input):
            return await self._quick_response(user_input)

        # 复杂请求：作业批改、学习分析
        return await self.agent.run(user_input, user_id)
```

## 核心流程示例

### 示例 1：出题

```
学生：给我出一道 Python 变量的题目

Agent Loop:
1. LLM 分析：学生想要练习题，主题是变量
2. LLM 选择工具：generate_question(topic="Python变量")
3. 执行工具：生成题目
4. LLM 返回：这是题目...

工具调用：
[
    {
        "name": "generate_question",
        "arguments": {
            "topic": "Python变量",
            "difficulty": "medium"
        }
    }
]
```

### 示例 2：答错后记录

```
学生：答案是 A

Agent Loop:
1. LLM 分析：学生提交答案，需要检查
2. LLM 选择工具：check_answer(question_id="q_123", user_answer="A")
3. 执行工具：返回错误
4. LLM 反思：答错了，需要记录
5. LLM 选择工具：record_error(...)
6. 执行工具：记录成功
7. LLM 返回：答错了，正确答案是 B，已记录到错题本

工具调用：
[
    {"name": "check_answer", "arguments": {"question_id": "q_123", "user_answer": "A"}},
    {"name": "record_error", "arguments": {...}},
    {"name": "update_mastery", "arguments": {"topic": "变量", "correct": false}}
]
```

### 示例 3：学习分析

```
学生：我最近学得怎么样？

Agent Loop:
1. LLM 分析：学生想了解学习情况
2. LLM 选择工具：get_learning_state(user_id)
3. LLM 选择工具：get_error_notebook(user_id)
4. 执行工具：返回学习状态和错题
5. LLM 综合分析，生成报告
6. LLM 返回：学习报告

工具调用：
[
    {"name": "get_learning_state", "arguments": {"user_id": "xxx"}},
    {"name": "get_error_notebook", "arguments": {"user_id": "xxx"}}
]
```

## 与现有代码的整合

### 保留的模块
- `ai_service.py` - LLM 服务（增强支持 Function Calling）
- `database.py` - 数据库（已有）
- `vector_store.py` - 向量检索（已有）
- `context_manager.py` - 上下文管理（改造为记忆系统）

### 重构的模块
- `agent.py` → 拆分为 `agent/core.py` + `tools/*.py`
- `intent/` → 简化为 `agent/router.py`
- `learning_state.py` → 改造为 `memory/long_term.py`

### 新增的模块
- `tools/base.py` - Tool 基类
- `tools/registry.py` - 工具注册表
- `tools/executor.py` - 工具执行器
- `agent/core.py` - Agent Loop
- `memory/manager.py` - 记忆管理器
