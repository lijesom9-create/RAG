# 教育 Agent 设计文档

## 核心理念：Agent = LLM + Harness

- **LLM（大脑）**：所有教学决策由 LLM 完成（难度调整、错误分析、学习路径规划）
- **Harness（骨架）**：提供工具、数据持久化、上下文组装、知识检索

## 目标用户

K-12 学生（小学、初中、高中）

## MVP 功能（第一阶段）

### 1. 错题本自动生成
- 每次答错自动记录到错题本
- 按知识点分类整理
- 支持按知识点、错误类型筛选
- 支持一键重做错题
- 支持导出错题本

### 2. 智能作业批改
- 支持文字输入作业
- 逐题批改，给出分数
- 生成批改报告（总分、错误分布、错误类型、建议）

### 3. 自适应难度
- LLM 决策下一题难度
- 基于掌握度、最近表现、错误模式
- 答对升级、答错降级（由 LLM 判断，不是规则）

## 增强功能（第二阶段）

### 4. 错误模式分析
- LLM 分析错误模式（混淆型、粗心型、概念型、遗忘型）
- 生成针对性讲解和练习

### 5. 间隔重复（SM-2）
- 基于遗忘曲线的复习提醒
- LLM 判断是否需要调整复习计划

### 6. 知识图谱
- 知识点依赖关系管理
- LLM 规划个性化学习路径

### 7. 考试模拟
- 计时考试
- 自动批改和成绩报告

### 8. 学习报告
- 每周自动生成学习报告
- 给家长/老师查看

## 数据模型

### LearningState（增强版）
```python
class LearningState:
    # 基础信息
    user_id: str
    current_topic: str
    current_question_id: str
    
    # 掌握度（保留）
    mastery_level: Dict[str, float]  # topic -> 0.0-1.0
    
    # 错题本（新增）
    error_notebook: List[ErrorEntry]  # 错题记录
    
    # 答题历史（新增）
    performance_history: Dict[str, List[bool]]  # topic -> [True, False, ...]
    
    # 错误模式（新增）
    error_patterns: List[ErrorPattern]  # LLM 分析结果
    
    # 间隔重复（新增）
    review_schedule: Dict[str, ReviewEntry]  # topic -> 复习计划
    
    # 学习路径（新增）
    learning_path: List[str]  # 推荐学习顺序
```

### ErrorEntry（错题记录）
```python
class ErrorEntry:
    question_id: str
    topic: str
    question: str
    user_answer: str
    correct_answer: str
    error_type: str  # 混淆/粗心/概念/遗忘
    timestamp: datetime
    reviewed: bool  # 是否已复习
    review_count: int  # 复习次数
```

### ReviewEntry（复习计划）
```python
class ReviewEntry:
    topic: str
    next_review: datetime
    interval_days: float
    ease_factor: float
    repetitions: int
```

## 架构设计

### 模块划分
```
backend/app/core/
├── agent.py              # Agent 主逻辑（增强）
├── learning_state.py     # 学习状态模型（新增）
├── error_notebook.py     # 错题本模块（新增）
├── homework_grader.py    # 作业批改模块（新增）
├── adaptive_difficulty.py # 自适应难度（新增）
├── spaced_repetition.py  # 间隔重复（新增）
├── knowledge_graph.py    # 知识图谱（新增）
├── context_manager.py    # 上下文管理（增强）
├── ai_service.py         # LLM 服务（保留）
├── database.py           # 数据库（增强）
└── retrieval/            # 知识检索（保留）
```

### Agent = LLM + Harness 分工

| 功能 | Harness 负责 | LLM 负责 |
|------|-------------|---------|
| 自适应难度 | 提供掌握度、答题历史 | 决定下一题难度 |
| 错误模式分析 | 提供错误历史 | 分析错误模式、生成讲解 |
| 间隔重复 | 维护复习计划、提醒 | 判断是否调整复习计划 |
| 知识图谱 | 维护依赖关系 | 规划学习路径 |
| 作业批改 | 解析作业、存储结果 | 批改题目、生成报告 |
| 错题本 | 存储、筛选、导出 | 分析错误类型、生成讲解 |

## 实现优先级

1. **P0**: 增强 LearningState 模型 ✅
2. **P1**: 错题本自动生成 ✅
3. **P1**: 自适应难度 ✅
4. **P2**: 智能作业批改 ✅
5. **P2**: 错误模式分析 ✅
6. **P3**: 间隔重复
7. **P3**: 知识图谱

## 已完成的实现

### 后端模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 学习状态 | `backend/app/core/learning_state.py` | 增强版学习状态模型，支持错题本、错误模式、间隔重复 |
| 错题本 | `backend/app/core/error_notebook.py` | 自动记录错题，按知识点分类，支持筛选和导出 |
| 作业批改 | `backend/app/core/homework_grader.py` | LLM 批改整份作业，生成批改报告 |
| 自适应难度 | `backend/app/core/adaptive_difficulty.py` | LLM 决策下一题难度，不是规则匹配 |

### API 接口

| 接口 | 路径 | 功能 |
|------|------|------|
| 错题本摘要 | `GET /api/error-notebook/summary` | 获取错题本统计 |
| 错题列表 | `GET /api/error-notebook/list` | 按知识点/类型筛选错题 |
| 标记已复习 | `POST /api/error-notebook/review/{id}` | 标记错题已复习 |
| 重做错题 | `GET /api/error-notebook/redo` | 获取可重做的错题 |
| 导出错题本 | `GET /api/error-notebook/export` | 导出错题本文本 |
| 作业批改 | `POST /api/homework/grade` | 批改整份作业 |
| 难度决策 | `POST /api/adaptive/decide` | LLM 决策下一题难度 |

### 前端页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 错题本 | `/error-notebook` | 查看错题、筛选、重做、导出 |
| 作业批改 | `/homework` | 输入作业内容，查看批改报告 |

### Agent = LLM + Harness 体现

| 功能 | Harness 负责 | LLM 负责 |
|------|-------------|---------|
| 自适应难度 | 提供掌握度、答题历史 | 决定下一题难度 |
| 错误模式分析 | 存储错误历史 | 分析错误类型（混淆/粗心/概念/遗忘） |
| 作业批改 | 解析作业、存储结果 | 批改题目、生成报告 |
| 错题本 | 存储、筛选、导出 | 分析错误类型 |
