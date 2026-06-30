/**
 * 会话侧边栏
 * 管理会话列表、新建/切换会话
 */

import { useState, useEffect } from 'react';
import { teachingApi, type SessionInfo } from '@/services/api';
import { Plus, MessageSquare, Loader2 } from 'lucide-react';

interface SessionSidebarProps {
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
  refreshTrigger?: number; // 用于外部触发刷新
}

export default function SessionSidebar({
  currentSessionId,
  onSessionSelect,
  onNewSession,
  refreshTrigger,
}: SessionSidebarProps) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadSessions();
  }, [refreshTrigger]);

  const loadSessions = async () => {
    setIsLoading(true);
    try {
      const response = await teachingApi.listSessions();
      setSessions(response.data.sessions || []);
    } catch (error) {
      console.error('加载会话列表失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

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

  return (
    <div className="flex flex-col h-full">
      {/* 新建按钮 */}
      <button
        onClick={onNewSession}
        className="flex items-center justify-center space-x-2 p-3 mb-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
      >
        <Plus size={18} />
        <span className="text-sm font-medium">新建对话</span>
      </button>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto space-y-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="animate-spin text-gray-400" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            暂无会话
          </div>
        ) : (
          sessions.map((session) => (
            <button
              key={session.session_id}
              onClick={() => onSessionSelect(session.session_id)}
              className={`w-full text-left p-3 rounded-lg transition-colors group ${
                currentSessionId === session.session_id
                  ? 'bg-blue-50 border border-blue-200'
                  : 'hover:bg-gray-50 border border-transparent'
              }`}
            >
              <div className="flex items-start space-x-2">
                <MessageSquare
                  size={16}
                  className={`mt-0.5 flex-shrink-0 ${
                    currentSessionId === session.session_id
                      ? 'text-blue-500'
                      : 'text-gray-400 group-hover:text-gray-600'
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div
                    className={`text-sm truncate ${
                      currentSessionId === session.session_id
                        ? 'text-blue-700 font-medium'
                        : 'text-gray-700'
                    }`}
                  >
                    {session.title || '新对话'}
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {formatDate(session.updated_at)}
                  </div>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
