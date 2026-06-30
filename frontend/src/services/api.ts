/**
 * API服务
 * 知识助手 - RAG 问答 + 文档管理 + 记忆系统
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import type {
  User,
  Token,
  LoginRequest,
  RegisterRequest,
} from '@/types';

// 创建axios实例
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 120000,  // Teaching Agent 可能需要较长时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 认证API
export const authApi = {
  register: (data: RegisterRequest): Promise<AxiosResponse<Token>> =>
    api.post('/auth/register', data),

  login: (data: LoginRequest): Promise<AxiosResponse<Token>> =>
    api.post('/auth/login', data),

  getMe: (): Promise<AxiosResponse<User>> =>
    api.get('/auth/me'),

  verifyToken: (): Promise<AxiosResponse<{ valid: boolean; user: User }>> =>
    api.get('/auth/verify'),
};

// Teaching Agent API
export interface TeachingResponse {
  response: string;
  skill_used: string;
  session_id: string;
  metadata?: Record<string, any>;
  state_summary?: StateSummary;
  lifecycle?: LifecycleInfo;
  observability?: ObservabilityInfo;
  learning_report?: LearningReport;
}

export interface StateSummary {
  user_id: string;
  profile?: {
    major?: string;
    year?: string;
    learning_style?: string;
  };
  learning?: {
    total_topics: number;
    weak_topics_count: number;
    strong_topics_count: number;
    accuracy: number;
    total_questions: number;
    error_count: number;
    unreviewed_errors: number;
  };
  behavior?: {
    preferred_style: string;
    prefers_examples: boolean;
    likes_encouragement: boolean;
  };
  emotion?: {
    confidence: string;
    frustration: string;
    engagement: string;
    emotion_summary: string;
  };
  goal?: {
    active_goals: number;
    current_topic?: string;
  };
  session?: {
    is_in_session: boolean;
    current_session_id?: string;
    total_sessions: number;
  };
  // 兼容旧格式
  current_topic?: string;
  total_topics: number;
  weak_topics_count: number;
  strong_topics_count: number;
  accuracy: number;
  total_questions: number;
  error_count: number;
}

export interface LifecycleInfo {
  agent_id: string;
  status: string;
  waiting_reason?: string;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface ObservabilityInfo {
  trace: TraceStep[];
  summary: string;
}

export interface TraceStep {
  timestamp: string;
  stage: string;
  data: Record<string, any>;
}

export interface LearningReport {
  user_id: string;
  insights: LearningInsight[];
  summary: string;
  recommendations: string[];
  metrics_snapshot?: Record<string, any>;
  generated_at: string;
}

export interface LearningInsight {
  id: string;
  eval_ids: string[];
  user_id: string;
  category: string;
  finding: string;
  suggestion: string;
  confidence: number;
}

// 会话相关类型
export interface SessionInfo {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface MessageInfo {
  role: 'user' | 'assistant';
  content: string;
  skill_used?: string;
  timestamp: string;
}

export const teachingApi = {
  chat: (message: string, sessionId?: string): Promise<AxiosResponse<TeachingResponse>> =>
    api.post('/teaching/chat', { message, session_id: sessionId }),

  getState: (): Promise<AxiosResponse<StateSummary>> =>
    api.get('/teaching/state'),

  resetContext: (): Promise<AxiosResponse<{ message: string }>> =>
    api.post('/teaching/reset'),

  // 会话管理
  createSession: (title?: string): Promise<AxiosResponse<{ session_id: string; title: string }>> =>
    api.post('/teaching/sessions', { title: title || '新对话' }),

  listSessions: (): Promise<AxiosResponse<{ sessions: SessionInfo[] }>> =>
    api.get('/teaching/sessions'),

  getSessionMessages: (sessionId: string, limit?: number): Promise<AxiosResponse<{ messages: MessageInfo[] }>> =>
    api.get(`/teaching/sessions/${sessionId}/messages`, { params: { limit: limit || 50 } }),
};

/**
 * SSE 流式聊天
 * 使用 fetch + ReadableStream 消费 Server-Sent Events
 */
export interface StreamCallbacks {
  onStart?: (data: { skill: string; session_id: string }) => void;
  onChunk?: (content: string) => void;
  onDone?: (metadata: Record<string, any>) => void;
  onError?: (message: string) => void;
}

export async function chatStream(
  message: string,
  sessionId: string | undefined,
  callbacks: StreamCallbacks,
): Promise<void> {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/teaching/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;

        try {
          const data = JSON.parse(trimmed.slice(6));
          switch (data.type) {
            case 'start':
              callbacks.onStart?.(data);
              break;
            case 'chunk':
              callbacks.onChunk?.(data.content);
              break;
            case 'done':
              callbacks.onDone?.(data.metadata);
              break;
            case 'error':
              callbacks.onError?.(data.message);
              break;
          }
        } catch {
          // 忽略解析错误
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * V2 SSE 流式聊天（Agent-Centric 架构）
 * LLM 为中心，自主决策调用工具
 */
export async function chatStreamV2(
  message: string,
  sessionId: string | undefined,
  callbacks: StreamCallbacks,
): Promise<void> {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/teaching/v2/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;

        try {
          const data = JSON.parse(trimmed.slice(6));
          switch (data.type) {
            case 'start':
              callbacks.onStart?.(data);
              break;
            case 'chunk':
              callbacks.onChunk?.(data.content);
              break;
            case 'done':
              callbacks.onDone?.(data.metadata);
              break;
            case 'error':
              callbacks.onError?.(data.message);
              break;
          }
        } catch {
          // 忽略解析错误
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ========== 学习主题 API ==========

export interface Topic {
  topic_id: string;
  title: string;
  description?: string;
  level: string;
  daily_minutes: number;
  status: string;
  target_date?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTopicRequest {
  title: string;
  description?: string;
  level?: string;
  daily_minutes?: number;
  target_date?: string;
}

export const topicsApi = {
  list: (status?: string): Promise<AxiosResponse<Topic[]>> =>
    api.get('/topics', { params: status ? { status } : {} }),

  get: (topicId: string): Promise<AxiosResponse<Topic>> =>
    api.get(`/topics/${topicId}`),

  create: (data: CreateTopicRequest): Promise<AxiosResponse<Topic>> =>
    api.post('/topics', data),

  update: (topicId: string, data: Partial<CreateTopicRequest>): Promise<AxiosResponse<Topic>> =>
    api.put(`/topics/${topicId}`, data),

  delete: (topicId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/topics/${topicId}`),

  archive: (topicId: string): Promise<AxiosResponse<void>> =>
    api.post(`/topics/${topicId}/archive`),

  activate: (topicId: string): Promise<AxiosResponse<void>> =>
    api.post(`/topics/${topicId}/activate`),
};

// ========== 学习资料 API ==========

export interface Document {
  document_id: string;
  filename: string;
  doc_type: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export const documentsApi = {
  list: (topicId: string): Promise<AxiosResponse<Document[]>> =>
    api.get(`/topics/${topicId}/documents`),

  upload: (topicId: string, file: File): Promise<AxiosResponse<Document>> => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/topics/${topicId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  status: (documentId: string): Promise<AxiosResponse<Document>> =>
    api.get(`/documents/${documentId}/status`),

  delete: (topicId: string, documentId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/topics/${topicId}/documents/${documentId}`),
};

// ========== 学习计划 API ==========

export interface StudyPlan {
  plan_id: string;
  title: string;
  description?: string;
  level: string;
  daily_minutes: number;
  status: string;
  phases: PlanPhase[];
  total_days: number;
  total_tasks: number;
  created_at: string;
}

export interface PlanPhase {
  title: string;
  description?: string;
  duration_days: number;
  tasks: PlanTask[];
}

export interface PlanTask {
  title: string;
  description?: string;
  estimated_minutes: number;
  type: string;
}

export const studyPlansApi = {
  list: (topicId: string): Promise<AxiosResponse<StudyPlan[]>> =>
    api.get(`/topics/${topicId}/plans`),

  generate: (topicId: string): Promise<AxiosResponse<StudyPlan>> =>
    api.post(`/topics/${topicId}/plans/generate`),

  get: (planId: string): Promise<AxiosResponse<StudyPlan>> =>
    api.get(`/plans/${planId}`),

  delete: (planId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/plans/${planId}`),
};

// ========== 评估/学习报告 API ==========

export interface EvaluationSummary {
  total_evaluations: number;
  average_score: number;
  latest_score: number | null;
  improvement_trend: string;
}

export interface LearningInsight {
  category: string;
  finding: string;
  suggestion: string;
  confidence: number;
}

export interface LearningReport {
  user_id: string;
  summary: string;
  insights: LearningInsight[];
  recommendations: string[];
  metrics_snapshot?: Record<string, any>;
}

export const evaluationApi = {
  summary: (): Promise<AxiosResponse<EvaluationSummary>> =>
    api.get('/evaluation/summary'),

  report: (): Promise<AxiosResponse<LearningReport>> =>
    api.get('/evaluation/report'),

  history: (limit?: number): Promise<AxiosResponse<{ total: number; history: any[] }>> =>
    api.get('/evaluation/history', { params: limit ? { limit } : {} }),
};

// ========== 飞书集成 API ==========

export interface FeishuConfig {
  webhook_url: string | null;
  has_secret: boolean;
  user_open_id: string | null;
  cli_available: boolean;
}

export const feishuApi = {
  getConfig: (): Promise<AxiosResponse<FeishuConfig>> =>
    api.get('/users/me/feishu'),

  updateConfig: (data: Partial<FeishuConfig>): Promise<AxiosResponse<FeishuConfig>> =>
    api.put('/users/me/feishu', data),

  sendTest: (message: string, sendTo?: string): Promise<AxiosResponse<any>> =>
    api.post('/feishu/test', { message, send_to: sendTo || 'personal' }),

  createReminder: (data: {
    topic: string;
    task: string;
    reminder_hour?: number;
    recurrence?: string;
  }): Promise<AxiosResponse<any>> =>
    api.post('/feishu/calendar/reminder', data),

  generateSummary: (summaryType: string): Promise<AxiosResponse<any>> =>
    api.post('/feishu/summary/generate', { summary_type: summaryType }),
};

// ========== 知识库 API ==========

export interface KnowledgeDocument {
  id: string;
  title: string;
  content: string;
  type: string;
  source: string;
  metadata: Record<string, any>;
  chunks: string[];
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSearchRequest {
  query: string;
  type_filter?: string[];
  limit?: number;
}

export const knowledgeApi = {
  list: (type?: string): Promise<AxiosResponse<KnowledgeDocument[]>> =>
    api.get('/knowledge/documents', { params: type ? { type } : {} }),

  get: (docId: string): Promise<AxiosResponse<KnowledgeDocument>> =>
    api.get(`/knowledge/documents/${docId}`),

  create: (data: {
    title: string;
    content: string;
    type?: string;
    source?: string;
    metadata?: Record<string, any>;
  }): Promise<AxiosResponse<KnowledgeDocument>> =>
    api.post('/knowledge/documents', data),

  update: (docId: string, data: {
    title?: string;
    content?: string;
    metadata?: Record<string, any>;
  }): Promise<AxiosResponse<KnowledgeDocument>> =>
    api.put(`/knowledge/documents/${docId}`, data),

  delete: (docId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/knowledge/documents/${docId}`),

  search: (data: KnowledgeSearchRequest): Promise<AxiosResponse<{ results: KnowledgeDocument[]; total: number }>> =>
    api.post('/knowledge/search', data),

  statistics: (): Promise<AxiosResponse<{ total: number; by_type: Record<string, number> }>> =>
    api.get('/knowledge/statistics'),
};

// 博客生成API
export interface BlogGenerateRequest {
  topic: string;
  article_type?: string;
  requirements?: string;
  urls?: string[];
}

export interface OutlineRequest {
  topic: string;
  article_type?: string;
  knowledge_context?: string;
}

export interface OutlineApproveRequest {
  outline: string;
  approved: boolean;
  adjustments?: string;
}

export interface ContentGenerateRequest {
  topic: string;
  outline: string;
  knowledge_context?: string;
  style?: string;
}

export interface BlogGenerateResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface OutlineResponse {
  topic: string;
  article_type: string;
  outline: string;
  knowledge_context?: string;
}

export interface ContentResponse {
  topic: string;
  content: string;
  word_count: number;
}

export const blogApi = {
  generate: (data: BlogGenerateRequest): Promise<AxiosResponse<BlogGenerateResponse>> =>
    api.post('/blog/generate', data),

  generateOutline: (data: OutlineRequest): Promise<AxiosResponse<OutlineResponse>> =>
    api.post('/blog/outline', data),

  generateContent: (data: ContentGenerateRequest): Promise<AxiosResponse<ContentResponse>> =>
    api.post('/blog/content', data),

  approveOutline: (data: OutlineApproveRequest): Promise<AxiosResponse<{ status: string; message: string; outline: string }>> =>
    api.post('/blog/outline/approve', data),

  generateWithWorkflow: (data: WorkflowGenerateRequest): Promise<AxiosResponse<WorkflowGenerateResponse>> =>
    api.post('/blog/workflow/generate', data),
};

// 工作流API
export interface WorkflowGenerateRequest {
  topic: string;
  article_type?: string;
  requirements?: string;
  urls?: string[];
  use_workflow?: boolean;
}

export interface TaskState {
  task_id: string;
  task_name: string;
  task_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  result?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
}

export interface WorkflowState {
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
  tasks: Record<string, TaskState>;
  progress: {
    total: number;
    completed: number;
    failed: number;
    running: number;
    pending: number;
    progress: number;
  };
  errors: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface WorkflowGenerateResponse {
  workflow_id: string;
  status: string;
  progress: {
    total: number;
    completed: number;
    failed: number;
  };
  result?: {
    topic: string;
    outline: string;
    content: string;
    word_count: number;
  };
  trace: Array<{
    event_type: string;
    timestamp: string;
    task_id?: string;
    task_name?: string;
    duration?: number;
    error?: string;
  }>;
}

export const workflowApi = {
  generate: (data: WorkflowGenerateRequest): Promise<AxiosResponse<WorkflowGenerateResponse>> =>
    api.post('/blog/workflow/generate', data),

  getState: (workflowId: string): Promise<AxiosResponse<WorkflowState>> =>
    api.get(`/workflow/${workflowId}`),

  listWorkflows: (params?: { status?: string; limit?: number }): Promise<AxiosResponse<{ workflows: WorkflowState[] }>> =>
    api.get('/workflow', { params }),
};

// ========== RAG 问答 API ==========

export interface ChatRequest {
  message: string;
  session_id?: string;
  use_memory?: boolean;
  use_rag?: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: Array<{ title: string; content: string }>;
  session_id: string;
  metadata: Record<string, any>;
}

export interface HistoryMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export const chatApi = {
  sendMessage: (message: string, sessionId?: string, useWebSearch?: boolean): Promise<ChatResponse> =>
    api.post('/langgraph/chat', { message, session_id: sessionId, use_web_search: useWebSearch || false }).then(res => ({
      answer: res.data.content,
      sources: res.data.citations || [],
      session_id: res.data.session_id || sessionId || 'default',
      metadata: { tools_used: res.data.tools_used, step_count: res.data.step_count },
    })),

  getHistory: (sessionId?: string, limit?: number): Promise<{ session_id: string; messages: HistoryMessage[]; total: number }> =>
    api.get('/chat/history', { params: { session_id: sessionId, limit: limit || 20 } }).then(res => res.data),

  clearHistory: (sessionId?: string): Promise<{ message: string }> =>
    api.delete('/chat/history', { params: { session_id: sessionId } }).then(res => res.data),

  getSessions: (): Promise<{ sessions: Array<{ session_id: string; created_at: string; updated_at: string; turn_count: number }> }> =>
    api.get('/chat/sessions').then(res => res.data),
};

// ========== 文档管理 API (新版) ==========

export interface DocumentInfo {
  document_id: string;
  filename: string;
  title: string;
  status: string;
  chunk_count: number;
  char_count: number;
  created_at: string;
}

export const documentsApiNew = {
  list: (): Promise<{ documents: DocumentInfo[]; total: number }> =>
    api.get('/documents/').then(res => res.data),

  upload: (file: File): Promise<{ document_id: string; filename: string; status: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },

  delete: (documentId: string): Promise<{ message: string }> =>
    api.delete(`/documents/${documentId}`).then(res => res.data),

  getStatus: (documentId: string): Promise<DocumentInfo> =>
    api.get(`/documents/${documentId}/status`).then(res => res.data),
};

// ========== 记忆管理 API ==========

export interface UserProfile {
  user_id: string;
  name: string;
  learning_style: string;
  weak_topics: string[];
  strong_topics: string[];
  preferences: Record<string, any>;
}

export interface MemoryStats {
  user_id: string;
  has_profile: boolean;
  weak_topics: number;
  strong_topics: number;
  sessions: number;
  total_turns: number;
  archival_entries: number;
}

export const memoryApi = {
  getProfile: (): Promise<UserProfile> =>
    api.get('/memory/profile').then(res => res.data),

  updateProfile: (data: { name?: string; learning_style?: string; preferences?: Record<string, any> }): Promise<{ message: string }> =>
    api.put('/memory/profile', data).then(res => res.data),

  addWeakTopic: (topic: string): Promise<{ message: string }> =>
    api.post('/memory/profile/weak-topic', null, { params: { topic } }).then(res => res.data),

  addStrongTopic: (topic: string): Promise<{ message: string }> =>
    api.post('/memory/profile/strong-topic', null, { params: { topic } }).then(res => res.data),

  addMemory: (content: string, category?: string, tags?: string[]): Promise<{ message: string; entry_id: string }> =>
    api.post('/memory/entries', { content, category: category || 'note', tags: tags || [] }).then(res => res.data),

  searchMemory: (query: string, category?: string, limit?: number): Promise<{ entries: Array<{ id: string; content: string; category: string; tags: string[]; created_at: string }>; total: number }> =>
    api.get('/memory/entries', { params: { query, category, limit: limit || 10 } }).then(res => res.data),

  getStats: (): Promise<MemoryStats> =>
    api.get('/memory/stats').then(res => res.data),

  clearAll: (): Promise<{ message: string; stats: Record<string, number> }> =>
    api.delete('/memory/clear').then(res => res.data),
};

export default api;
