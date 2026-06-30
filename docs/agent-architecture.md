# 教育 Agent 真正架构设计

## 核心理念：Agent = LLM + Tools + Memory

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Loop                               │
│                                                                  │
│   用户输入 → LLM 分析 → 选择工具 → 执行 → 反思 → 响应          │
│              ↑                    ↓                              │
│              └────── 可能多轮 ────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## 与当前实现的区别

| 当前实现 | 真正的 Agent |
|----------|-------------|
| 意图分类 → 路由到处理器 | LLM 自主决定做什么 |
| 硬编码流程 | LLM 规划步骤 |
| 单次 LLM 调用 | 多轮工具调用 |
| 没有工具协议 | MCP 标准化工具 |
| 短期记忆 | 短期 + 长期记忆 |

---

## 一、工具定义（Tools）

### 1.1 工具列表

| 工具名 | 功能 | 输入 | 输出 |
|--------|------|------|------|
| `search_knowledge` | 检索知识库 | query, top_k | 知识列表 |
| `generate_question` | 生成题目 | topic, difficulty, type | 题目数据 |
| `check_answer` | 检查答案 | question_id, user_answer | 对错 + 解析 |
| `record_error` | 记录错题 | question_id, topic, ... | 成功/失败 |
| `get_error_notebook` | 获取错题本 | user_id, filter | 错题列表 |
| `grade_homework` | 批改作业 | content/image | 批改报告 |
| `get_learning_state` | 获取学习状态 | user_id | 掌握度、进度 |
| `update_mastery` | 更新掌握度 | topic, correct | 更新结果 |
| `get_review_schedule` | 获取复习计划 | user_id | 待复习列表 |
| `search_question_bank` | 搜索题库 | topic, difficulty | 题目列表 |

### 1.2 MCP 工具协议

每个工具遵循统一格式：

```python
class Tool:
    name: str                    # 工具名
    description: str             # 工具描述（给 LLM 看）
    input_schema: Dict           # 输入 JSON Schema
    output_schema: Dict          # 输出 JSON Schema

    async def execute(self, input: Dict) -> Dict:
        """执行工具"""
        pass
```

示例：

```python
class GenerateQuestionTool(Tool):
    name = "generate_question"
    description = "生成一道练习题。指定主题、难度、题型。"
    input_schema = {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "知识点主题"},
            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
            "question_type": {"type": "string", "enum": ["选择题", "填空题", "简答题"]}
        },
        "required": ["topic"]
    }
```

---

## 二、Agent Loop

### 2.1 核心循环

```python
class Agent:
    async def run(self, user_input: str) -> str:
        # 1. 加载记忆
        memory = await self.load_memory()

        # 2. 构建消息
        messages = self.build_messages(user_input, memory)

        # 3. Agent Loop（最多 N 轮）
        for i in range(MAX_ITERATIONS):
            # 3.1 LLM 决定下一步
            response = await self.llm.chat(messages, tools=self.tools)

            # 3.2 如果是最终答案，返回
            if response.type == "final_answer":
                return response.content

            # 3.3 如果是工具调用，执行
            if response.type == "tool_call":
                results = await self.execute_tools(response.tool_calls)
                messages.append(response)
                messages.append({"role": "tool", "content": results})

            # 3.4 如果是反思，继续
            if response.type == "reflection":
                messages.append(response)

        # 4. 超过最大轮次，返回当前结果
        return "抱歉，我无法完成这个任务。"
```

### 2.2 LLM 系统提示

```
你是一个教育助手 Agent。你可以使用工具来帮助学生学习。

可用工具：
- search_knowledge: 检索知识库
- generate_question: 生成练习题
- check_answer: 检查答案
- record_error: 记录错题
- get_error_notebook: 查看错题本
- grade_homework: 批改作业
- get_learning_state: 查看学习状态
- update_mastery: 更新掌握度

工作流程：
1. 理解学生的需求
2. 决定需要使用哪些工具
3. 调用工具获取信息
4. 综合信息，给出回答

重要：
- 你可以一次调用多个工具
- 如果工具返回错误，尝试其他方法
- 如果信息不足，继续调用工具
- 最终给出清晰、有帮助的回答
```

---

## 三、记忆系统（Memory）

### 3.1 短期记忆（对话内）

```python
class ShortTermMemory:
    """当前对话的记忆"""
    messages: List[Dict]           # 对话历史
    current_topic: str             # 当前主题
    current_question_id: str       # 当前题目
    recent_tools: List[str]        # 最近调用的工具
```

### 3.2 长期记忆（跨会话）

```python
class LongTermMemory:
    """跨会话的长期记忆"""
    user_id: str
    mastery_level: Dict[str, float]    # 知识点掌握度
    error_patterns: List[Dict]         # 错误模式
    learning_history: List[Dict]       # 学习历史
    preferences: Dict                  # 学习偏好
    review_schedule: Dict              # 复习计划
```

### 3.3 记忆注入

每次 LLM 调用时，自动注入记忆：

```python
def build_messages(self, user_input, memory):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"[学习状态]\n{memory.to_prompt()}"},
        {"role": "system", "content": f"[最近对话]\n{memory.recent_summary()}"},
        {"role": "user", "content": user_input}
    ]
    return messages
```

---

## 四、工具实现

### 4.1 工具注册表

```python
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_all(self) -> List[Tool]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict]:
        """获取所有工具的 schema（给 LLM 用）"""
        return [tool.to_schema() for tool in self._tools.values()]
```

### 4.2 工具执行器

```python
class ToolExecutor:
    """工具执行器"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(self, tool_calls: List[Dict]) -> List[Dict]:
        """执行多个工具调用"""
        results = []
        for call in tool_calls:
            tool = self.registry.get(call["name"])
            if tool:
                try:
                    result = await tool.execute(call["arguments"])
                    results.append({
                        "tool": call["name"],
                        "result": result,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "tool": call["name"],
                        "error": str(e),
                        "success": False
                    })
        return results
```

---

## 五、示例场景

### 场景 1：学生请求出题

```
学生：给我出一道 Python 变量的题目

Agent 思考：
1. 学生想要练习题
2. 主题是 Python 变量
3. 需要先检查学习状态，决定难度
4. 然后生成题目

Agent 执行：
1. 调用 get_learning_state(user_id) → 掌握度 50%
2. 调用 generate_question(topic="Python变量", difficulty="medium")
3. 返回题目给学生
```

### 场景 2：学生答错后

```
学生：答案是 A

Agent 思考：
1. 学生提交了答案
2. 需要检查是否正确
3. 如果错误，记录到错题本

Agent 执行：
1. 调用 check_answer(question_id="q_123", user_answer="A")
2. 返回：错误，正确答案是 B
3. 调用 record_error(question_id="q_123", ...)
4. 调用 update_mastery(topic="变量", correct=False)
5. 返回反馈 + 已记录到错题本
```

### 场景 3：学生说"帮我看看作业"

```
学生：帮我看看这道题：什么是变量？我的答案是：变量是用来存数据的

Agent 思考：
1. 学生提交了作业内容
2. 需要批改这道题
3. 如果错误，记录到错题本

Agent 执行：
1. 调用 grade_homework(content="什么是变量？学生答案：变量是用来存数据的")
2. 返回：基本正确，但可以更准确
3. 如果错误，调用 record_error(...)
```

### 场景 4：复杂请求

```
学生：我最近学得怎么样？有什么建议？

Agent 思考：
1. 学生想了解学习情况
2. 需要获取学习状态
3. 需要获取错题本
4. 综合分析，给出建议

Agent 执行：
1. 调用 get_learning_state(user_id)
2. 调用 get_error_notebook(user_id)
3. 综合分析，生成报告
4. 返回学习报告 + 建议
```

---

## 六、实现计划

### Phase 1：工具系统（核心）✅
1. 定义 Tool 基类 ✅
2. 实现 ToolRegistry ✅
3. 实现 ToolExecutor ✅
4. 将现有功能封装为工具 ✅

### Phase 2：Agent Loop ✅
1. 实现 Agent 核心循环 ✅
2. 实现 LLM 工具调用解析 ✅
3. 实现多轮工具调用 ✅

### Phase 3：记忆系统 ✅
1. 实现 ShortTermMemory ✅
2. 实现 LongTermMemory ✅
3. 实现记忆注入 ✅

### Phase 4：增强功能
1. 多模态支持（图片识别）
2. RAG 题库
3. 间隔重复

## 已实现的文件

```
backend/app/core/
├── agent/
│   ├── __init__.py
│   ├── core.py           # Agent 核心循环 ✅
│   └── router.py         # 请求路由 ✅
├── tools/
│   ├── __init__.py       # 工具注册 ✅
│   ├── base.py           # Tool 基类 ✅
│   ├── registry.py       # 工具注册表 ✅
│   ├── executor.py       # 工具执行器 ✅
│   ├── knowledge.py      # 知识检索工具 ✅
│   ├── question.py       # 题目生成工具 ✅
│   ├── answer.py         # 答案检查工具 ✅
│   ├── error.py          # 错题记录工具 ✅
│   ├── homework.py       # 作业批改工具 ✅
│   ├── learning.py       # 学习状态工具 ✅
│   └── review.py         # 复习计划工具 ✅
├── memory/
│   ├── __init__.py
│   ├── short_term.py     # 短期记忆 ✅
│   ├── long_term.py      # 长期记忆 ✅
│   └── manager.py        # 记忆管理器 ✅
└── llm/
    └── service.py        # LLM 服务（已有）
```

---

## 七、与 Claude Code 架构的对比

| Claude Component | 教育 Agent 对应 |
|------------------|----------------|
| Tool Use | ToolRegistry + ToolExecutor |
| Planning | Agent Loop（多轮决策） |
| Memory | ShortTermMemory + LongTermMemory |
| Context Management | 记忆注入 + 对话压缩 |
| Permission System | 工具权限控制 |

---

## 八、关键技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| LLM | OpenAI / Claude | 支持 Function Calling |
| 工具协议 | 自定义 MCP | 简化版，适合教育场景 |
| 记忆存储 | MongoDB | 已有，复用 |
| 向量库 | ChromaDB | 已有，复用 |
| 多模态 | GPT-4V / Qwen-VL | 图片识别 |
