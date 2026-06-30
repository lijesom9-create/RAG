/**
 * Teaching Agent 聊天页面
 * 三栏布局：左侧主题栏 + 中间聊天 + 右侧上下文面板
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  teachingApi,
  chatStreamV2,
  type StateSummary,
  type LifecycleInfo,
  type ObservabilityInfo,
  type LearningReport,
  type MessageInfo,
} from '@/services/api';
import { Send, Loader2, Brain, BookOpen, Target, TrendingUp, BarChart3, Lightbulb, PanelLeftClose, PanelRightClose, PanelLeft, PanelRight } from 'lucide-react';
import TopicSidebar from '@/components/Workspace/TopicSidebar';
import ContextPanel from '@/components/Workspace/ContextPanel';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  skill_used?: string;
  lifecycle?: LifecycleInfo;
  observability?: ObservabilityInfo;
  learning_report?: LearningReport;
  timestamp: Date;
}

export default function TeachingChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stateSummary, setStateSummary] = useState<StateSummary | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentTopicId, setCurrentTopicId] = useState<string | null>(null);
  const [sessionRefreshTrigger, setSessionRefreshTrigger] = useState(0);
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const msgIdCounter = useRef(0);

  const nextMsgId = useCallback(() => {
    msgIdCounter.current += 1;
    return `msg_${msgIdCounter.current}`;
  }, []);

  // 加载学生状态
  useEffect(() => {
    loadState();
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadState = async () => {
    try {
      const response = await teachingApi.getState();
      setStateSummary(response.data);
    } catch (error) {
      console.error('加载状态失败:', error);
    }
  };

  // 加载会话消息历史
  const loadSessionMessages = async (sessionId: string) => {
    try {
      const response = await teachingApi.getSessionMessages(sessionId);
      const dbMessages: Message[] = response.data.messages.map((msg: MessageInfo, idx: number) => ({
        id: `history_${idx}`,
        role: msg.role,
        content: msg.content,
        skill_used: msg.skill_used,
        timestamp: new Date(msg.timestamp),
      }));
      setMessages(dbMessages);
    } catch (error) {
      console.error('加载消息历史失败:', error);
      setMessages([]);
    }
  };

  // 新建会话
  const handleNewSession = async () => {
    try {
      const response = await teachingApi.createSession('新对话');
      const { session_id } = response.data;
      setCurrentSessionId(session_id);
      setMessages([]);
      setSessionRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error('创建会话失败:', error);
    }
  };

  // 切换会话
  const handleSessionSelect = async (sessionId: string) => {
    setCurrentSessionId(sessionId);
    await loadSessionMessages(sessionId);
  };

  // 切换主题
  const handleTopicSelect = (topicId: string) => {
    setCurrentTopicId(topicId);
  };

  // 发送消息（SSE 流式）
  const handleSend = async (messageText?: string) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;

    const userMessage: Message = {
      id: nextMsgId(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // 重置输入框高度
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    // 创建空的 assistant message，流式更新
    const assistantId = nextMsgId();
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      await chatStreamV2(text, currentSessionId || undefined, {
        onStart: (data) => {
          // 更新 session_id
          if (!currentSessionId || currentSessionId !== data.session_id) {
            setCurrentSessionId(data.session_id);
            setSessionRefreshTrigger(prev => prev + 1);
          }
          // 更新 skill_used
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, skill_used: data.skill } : m
          ));
        },
        onChunk: (content) => {
          // 追加文本片段
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, content: m.content + content } : m
          ));
        },
        onDone: (metadata) => {
          // 更新完整 metadata
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? {
              ...m,
              lifecycle: metadata.lifecycle,
              observability: metadata.observability,
              learning_report: metadata.learning_report,
            } : m
          ));
          // 更新状态
          if (metadata.state_summary) {
            setStateSummary(metadata.state_summary);
          }
        },
        onError: (_message) => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, content: m.content || '抱歉，出现了错误。请稍后再试。' } : m
          ));
        },
      });
    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages(prev => prev.map(m =>
        m.id === assistantId ? { ...m, content: m.content || '抱歉，出现了错误。请稍后再试。' } : m
      ));
    } finally {
      setIsLoading(false);
    }
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 自动调整输入框高度
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  };

  // 获取技能显示名称
  const getSkillDisplayName = (skill?: string) => {
    const skillNames: Record<string, string> = {
      quick_explain: '快速解释',
      concept_lesson: '概念讲解',
      practice_session: '练习辅导',
      answer_feedback: '答案反馈',
      review_session: '复习巩固',
      spaced_repetition: '间隔重复',
      learning_review: '学习回顾',
      quick_summary: '快速总结',
    };
    return skill ? skillNames[skill] || skill : '';
  };

  // 获取技能图标
  const getSkillIcon = (skill?: string) => {
    switch (skill) {
      case 'quick_explain':
      case 'concept_lesson':
        return <BookOpen size={12} />;
      case 'practice_session':
        return <Target size={12} />;
      case 'answer_feedback':
        return <TrendingUp size={12} />;
      case 'review_session':
      case 'spaced_repetition':
        return <Brain size={12} />;
      case 'learning_review':
      case 'quick_summary':
        return <BarChart3 size={12} />;
      default:
        return null;
    }
  };

  // 获取生命周期状态显示
  const getLifecycleStatusDisplay = (status?: string) => {
    const statusMap: Record<string, { label: string; color: string }> = {
      completed: { label: '完成', color: 'text-green-600 bg-green-50' },
      failed: { label: '失败', color: 'text-red-600 bg-red-50' },
      executing: { label: '执行中', color: 'text-blue-600 bg-blue-50' },
      planning: { label: '规划中', color: 'text-yellow-600 bg-yellow-50' },
    };
    return status ? statusMap[status] || { label: status, color: 'text-gray-600 bg-gray-50' } : null;
  };

  return (
    <div className="h-full flex">
      {/* 左侧栏 */}
      {leftSidebarOpen && (
        <div className="w-60 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
          <TopicSidebar
            currentTopicId={currentTopicId}
            currentSessionId={currentSessionId}
            stateSummary={stateSummary}
            onTopicSelect={handleTopicSelect}
            onSessionSelect={handleSessionSelect}
            onNewSession={handleNewSession}
            refreshTrigger={sessionRefreshTrigger}
          />
        </div>
      )}

      {/* 中间聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 聊天头部 */}
        <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title={leftSidebarOpen ? '隐藏侧栏' : '显示侧栏'}
            >
              {leftSidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeft size={16} />}
            </button>
            <span className="text-sm font-medium text-gray-700">
              {currentSessionId ? '对话中' : '教育助手'}
            </span>
          </div>
          <button
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title={rightPanelOpen ? '隐藏面板' : '显示面板'}
          >
            {rightPanelOpen ? <PanelRightClose size={16} /> : <PanelRight size={16} />}
          </button>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-5xl mb-3">🎓</div>
              <h3 className="text-lg font-medium mb-2">你好！我是你的学习助手</h3>
              <p className="text-center max-w-md mb-5 text-sm">
                我会根据你的学习状态，为你提供个性化的教学。
                你可以问我问题、请求练习、或者查看学习报告。
              </p>

              {/* 快捷问题 */}
              <div className="grid grid-cols-2 gap-2 max-w-md">
                {[
                  { text: '什么是Python变量？', icon: '📖' },
                  { text: '给我出一道练习题', icon: '✏️' },
                  { text: '我学得怎么样？', icon: '📊' },
                  { text: '复习一下薄弱知识点', icon: '🔄' },
                ].map((item) => (
                  <button
                    key={item.text}
                    onClick={() => {
                      setInput(item.text);
                      inputRef.current?.focus();
                    }}
                    className="p-2.5 text-xs text-left bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors flex items-center space-x-2"
                  >
                    <span>{item.icon}</span>
                    <span>{item.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex items-start space-x-3 ${
                    message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                  }`}
                >
                  {/* 头像 */}
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-sm flex-shrink-0 ${
                      message.role === 'user'
                        ? 'bg-blue-100'
                        : 'bg-green-100'
                    }`}
                  >
                    {message.role === 'user' ? '👤' : '🎓'}
                  </div>

                  {/* 消息内容 */}
                  <div className="flex-1 min-w-0">
                    {/* 技能标签和生命周期状态 */}
                    {message.role === 'assistant' && (
                      <div className="flex items-center space-x-2 mb-1">
                        {message.skill_used && (
                          <div className="flex items-center space-x-1">
                            {getSkillIcon(message.skill_used)}
                            <span className="text-[10px] text-gray-500">
                              {getSkillDisplayName(message.skill_used)}
                            </span>
                          </div>
                        )}
                        {message.lifecycle && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${getLifecycleStatusDisplay(message.lifecycle.status)?.color}`}>
                            {getLifecycleStatusDisplay(message.lifecycle.status)?.label}
                          </span>
                        )}
                        {message.observability && (
                          <span className="text-[10px] text-gray-400" title={message.observability.summary}>
                            {message.observability.trace.length} 步
                          </span>
                        )}
                      </div>
                    )}

                    {/* 消息气泡 */}
                    <div
                      className={`p-3 rounded-xl ${
                        message.role === 'user'
                          ? 'bg-blue-500 text-white ml-auto max-w-[80%]'
                          : 'bg-gray-100 text-gray-900 max-w-[90%]'
                      }`}
                    >
                      {message.role === 'user' ? (
                        <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                      ) : (
                        <div className="prose prose-sm max-w-none prose-p:my-1 prose-pre:bg-gray-800 prose-pre:text-gray-100 prose-code:text-pink-600 prose-code:bg-pink-50 prose-code:px-1 prose-code:rounded">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      )}
                    </div>

                    {/* 学习洞察（如果有） */}
                    {message.learning_report && message.learning_report.insights.length > 0 && (
                      <div className="mt-2 p-2.5 bg-yellow-50 rounded-lg border border-yellow-200">
                        <div className="flex items-center space-x-1 mb-1.5">
                          <Lightbulb size={12} className="text-yellow-600" />
                          <span className="text-xs font-medium text-yellow-800">学习洞察</span>
                        </div>
                        {message.learning_report.insights.map((insight, idx) => (
                          <div key={idx} className="text-xs text-yellow-700 mb-0.5">
                            • {insight.finding}
                            {insight.suggestion && (
                              <span className="text-yellow-600"> → {insight.suggestion}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* 链路详情（可展开） */}
                    {message.observability && message.observability.trace.length > 0 && (
                      <details className="mt-1.5">
                        <summary className="text-[10px] text-gray-400 cursor-pointer hover:text-gray-600">
                          查看链路详情
                        </summary>
                        <div className="mt-1 p-2 bg-gray-50 rounded text-[10px] font-mono text-gray-600">
                          {message.observability.summary}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              ))}

              {/* 加载状态 */}
              {isLoading && (
                <div className="flex items-start space-x-3">
                  <div className="w-7 h-7 rounded-full bg-green-100 flex items-center justify-center text-sm">
                    🎓
                  </div>
                  <div className="bg-gray-100 rounded-xl p-3">
                    <Loader2 size={16} className="animate-spin text-gray-500" />
                  </div>
                </div>
              )}
            </>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="px-4 py-3 bg-white border-t border-gray-200">
          <div className="flex items-end space-x-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题... (Shift+Enter 换行)"
              className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm text-gray-900 placeholder-gray-400 max-h-[160px]"
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="p-2.5 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              {isLoading ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Send size={18} />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 右侧面板 */}
      {rightPanelOpen && (
        <div className="w-72 flex-shrink-0 bg-white border-l border-gray-200 flex flex-col">
          <ContextPanel
            topicId={currentTopicId}
            onSendMessage={handleSend}
          />
        </div>
      )}
    </div>
  );
}
