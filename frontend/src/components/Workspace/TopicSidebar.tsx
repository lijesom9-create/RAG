/**
 * 左侧栏：主题选择 + 会话列表 + 学习统计
 * 合并了原 TopicsPage 和 SessionSidebar 的功能
 */

import { useState, useEffect } from 'react';
import {
  topicsApi,
  teachingApi,
  type Topic,
  type SessionInfo,
  type StateSummary,
} from '@/services/api';
import {
  Plus,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  BookOpen,
  Loader2,
  Brain,
} from 'lucide-react';

interface TopicSidebarProps {
  currentTopicId: string | null;
  currentSessionId: string | null;
  stateSummary: StateSummary | null;
  onTopicSelect: (topicId: string) => void;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
  refreshTrigger?: number;
}

export default function TopicSidebar({
  currentTopicId,
  currentSessionId,
  stateSummary,
  onTopicSelect,
  onSessionSelect,
  onNewSession,
  refreshTrigger,
}: TopicSidebarProps) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [showCreateTopic, setShowCreateTopic] = useState(false);
  const [creating, setCreating] = useState(false);
  const [topicForm, setTopicForm] = useState({ title: '', description: '', level: 'beginner' });
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());

  // 加载主题列表
  useEffect(() => {
    loadTopics();
  }, []);

  // 加载会话列表
  useEffect(() => {
    loadSessions();
  }, [refreshTrigger]);

  const loadTopics = async () => {
    try {
      setLoadingTopics(true);
      const resp = await topicsApi.list();
      const data = resp.data as any;
      const topicList = Array.isArray(data) ? data : (data.topics || []);
      setTopics(topicList);
      // 自动展开当前选中的主题
      if (currentTopicId) {
        setExpandedTopics(new Set([currentTopicId]));
      }
    } catch (err) {
      console.error('加载主题失败:', err);
    } finally {
      setLoadingTopics(false);
    }
  };

  const loadSessions = async () => {
    try {
      setLoadingSessions(true);
      const resp = await teachingApi.listSessions();
      setSessions(resp.data.sessions || []);
    } catch (err) {
      console.error('加载会话失败:', err);
    } finally {
      setLoadingSessions(false);
    }
  };

  // 创建主题
  const handleCreateTopic = async () => {
    if (!topicForm.title.trim()) return;
    try {
      setCreating(true);
      await topicsApi.create(topicForm);
      setShowCreateTopic(false);
      setTopicForm({ title: '', description: '', level: 'beginner' });
      await loadTopics();
    } catch (err) {
      console.error('创建主题失败:', err);
    } finally {
      setCreating(false);
    }
  };

  // 切换主题展开/折叠
  const toggleTopic = (topicId: string) => {
    setExpandedTopics(prev => {
      const next = new Set(prev);
      if (next.has(topicId)) {
        next.delete(topicId);
      } else {
        next.add(topicId);
      }
      return next;
    });
    onTopicSelect(topicId);
  };

  // 格式化时间
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return '刚刚';
      if (diffMins < 60) return `${diffMins}分钟前`;
      if (diffHours < 24) return `${diffHours}小时前`;
      if (diffDays < 7) return `${diffDays}天前`;
      return date.toLocaleDateString('zh-CN');
    } catch {
      return '';
    }
  };

  const levelLabels: Record<string, string> = {
    beginner: '入门',
    intermediate: '进阶',
    advanced: '高级',
  };

  const levelColors: Record<string, string> = {
    beginner: 'bg-green-100 text-green-700',
    intermediate: 'bg-blue-100 text-blue-700',
    advanced: 'bg-purple-100 text-purple-700',
  };

  return (
    <div className="flex flex-col h-full">
      {/* 主题列表 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">学习主题</span>
            <button
              onClick={() => setShowCreateTopic(!showCreateTopic)}
              className="p-1 text-gray-400 hover:text-blue-500 rounded"
              title="新建主题"
            >
              <Plus size={14} />
            </button>
          </div>

          {/* 新建主题表单 */}
          {showCreateTopic && (
            <div className="mb-3 p-3 bg-gray-50 rounded-lg space-y-2">
              <input
                type="text"
                value={topicForm.title}
                onChange={(e) => setTopicForm({ ...topicForm, title: e.target.value })}
                placeholder="主题名称"
                className="w-full px-2 py-1.5 text-sm border rounded focus:ring-1 focus:ring-blue-500"
                autoFocus
              />
              <select
                value={topicForm.level}
                onChange={(e) => setTopicForm({ ...topicForm, level: e.target.value })}
                className="w-full px-2 py-1.5 text-sm border rounded"
              >
                <option value="beginner">入门</option>
                <option value="intermediate">进阶</option>
                <option value="advanced">高级</option>
              </select>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowCreateTopic(false)}
                  className="flex-1 px-2 py-1 text-xs text-gray-600 hover:text-gray-800"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateTopic}
                  disabled={!topicForm.title.trim() || creating}
                  className="flex-1 px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                >
                  {creating ? '创建中...' : '创建'}
                </button>
              </div>
            </div>
          )}

          {/* 主题列表 */}
          {loadingTopics ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 size={16} className="animate-spin text-gray-400" />
            </div>
          ) : topics.length === 0 ? (
            <div className="text-center py-4 text-gray-400 text-xs">
              <BookOpen size={20} className="mx-auto mb-2 opacity-50" />
              还没有学习主题
            </div>
          ) : (
            <div className="space-y-0.5">
              {topics.map((topic) => (
                <div key={topic.topic_id}>
                  {/* 主题标题 */}
                  <button
                    onClick={() => toggleTopic(topic.topic_id)}
                    className={`w-full text-left px-2 py-1.5 rounded text-sm flex items-center gap-2 transition-colors ${
                      currentTopicId === topic.topic_id
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {expandedTopics.has(topic.topic_id) ? (
                      <ChevronDown size={12} className="flex-shrink-0 text-gray-400" />
                    ) : (
                      <ChevronRight size={12} className="flex-shrink-0 text-gray-400" />
                    )}
                    <span className="flex-1 truncate font-medium">{topic.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${levelColors[topic.level] || 'bg-gray-100'}`}>
                      {levelLabels[topic.level] || topic.level}
                    </span>
                  </button>

                  {/* 展开的会话列表 */}
                  {expandedTopics.has(topic.topic_id) && (
                    <div className="ml-5 mt-1 space-y-0.5">
                      {/* 新建对话按钮 */}
                      <button
                        onClick={onNewSession}
                        className="w-full text-left px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded flex items-center gap-1.5"
                      >
                        <Plus size={10} />
                        新建对话
                      </button>

                      {/* 会话列表 */}
                      {loadingSessions ? (
                        <div className="flex items-center justify-center py-2">
                          <Loader2 size={12} className="animate-spin text-gray-400" />
                        </div>
                      ) : sessions.length === 0 ? (
                        <div className="text-center py-2 text-gray-400 text-[10px]">
                          暂无会话
                        </div>
                      ) : (
                        sessions.map((session) => (
                          <button
                            key={session.session_id}
                            onClick={() => onSessionSelect(session.session_id)}
                            className={`w-full text-left px-2 py-1 rounded text-xs flex items-center gap-1.5 transition-colors ${
                              currentSessionId === session.session_id
                                ? 'bg-blue-100 text-blue-700'
                                : 'text-gray-600 hover:bg-gray-50'
                            }`}
                          >
                            <MessageSquare size={10} className="flex-shrink-0" />
                            <span className="flex-1 truncate">{session.title || '新对话'}</span>
                            <span className="text-[10px] text-gray-400 flex-shrink-0">
                              {formatDate(session.updated_at)}
                            </span>
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 学习统计 */}
      {stateSummary && (
        <div className="p-3 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center gap-1 mb-2">
            <Brain size={12} className="text-gray-500" />
            <span className="text-xs font-semibold text-gray-500">学习状态</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="text-center p-2 bg-white rounded">
              <div className="text-sm font-bold text-gray-900">
                {stateSummary.learning?.total_topics || stateSummary.total_topics || 0}
              </div>
              <div className="text-[10px] text-gray-500">知识点</div>
            </div>
            <div className="text-center p-2 bg-white rounded">
              <div className="text-sm font-bold text-gray-900">
                {(stateSummary.learning?.accuracy || stateSummary.accuracy || 0) > 0
                  ? `${Math.round((stateSummary.learning?.accuracy || stateSummary.accuracy || 0) * 100)}%`
                  : '-'}
              </div>
              <div className="text-[10px] text-gray-500">正确率</div>
            </div>
          </div>
          {(stateSummary.goal?.current_topic || stateSummary.current_topic) && (
            <div className="mt-2 p-1.5 bg-blue-50 rounded text-[10px] text-blue-700 text-center">
              当前: {stateSummary.goal?.current_topic || stateSummary.current_topic}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
