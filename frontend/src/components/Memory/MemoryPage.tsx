/**
 * 记忆管理页面
 * 用户画像、对话历史、档案记忆
 */

import { useState, useEffect } from 'react';
import { Brain, User, MessageSquare, BookOpen, Trash2, Loader2 } from 'lucide-react';
import { memoryApi } from '@/services/api';

interface UserProfile {
  user_id: string;
  name: string;
  learning_style: string;
  weak_topics: string[];
  strong_topics: string[];
}

interface MemoryStats {
  user_id: string;
  has_profile: boolean;
  weak_topics: number;
  strong_topics: number;
  sessions: number;
  total_turns: number;
  archival_entries: number;
}

export default function MemoryPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [newWeakTopic, setNewWeakTopic] = useState('');
  const [newStrongTopic, setNewStrongTopic] = useState('');

  // 加载数据
  const loadData = async () => {
    try {
      setLoading(true);
      const [profileRes, statsRes] = await Promise.all([
        memoryApi.getProfile(),
        memoryApi.getStats(),
      ]);
      setProfile(profileRes);
      setStats(statsRes);
    } catch (error) {
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // 添加薄弱知识点
  const handleAddWeakTopic = async () => {
    if (!newWeakTopic.trim()) return;
    try {
      await memoryApi.addWeakTopic(newWeakTopic.trim());
      setNewWeakTopic('');
      await loadData();
    } catch (error) {
      console.error('添加失败:', error);
    }
  };

  // 添加擅长领域
  const handleAddStrongTopic = async () => {
    if (!newStrongTopic.trim()) return;
    try {
      await memoryApi.addStrongTopic(newStrongTopic.trim());
      setNewStrongTopic('');
      await loadData();
    } catch (error) {
      console.error('添加失败:', error);
    }
  };

  // 清空所有记忆
  const handleClearAll = async () => {
    if (!confirm('确定要清空所有记忆吗？此操作不可恢复。')) return;
    try {
      await memoryApi.clearAll();
      await loadData();
    } catch (error) {
      console.error('清空失败:', error);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center space-x-2">
            <Brain size={20} />
            <span>记忆管理</span>
          </h2>
          <button
            onClick={handleClearAll}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 size={16} />
            <span>清空所有</span>
          </button>
        </div>

        {/* 统计卡片 */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border p-4">
              <div className="flex items-center space-x-2 text-gray-500 mb-2">
                <MessageSquare size={16} />
                <span className="text-sm">对话轮次</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stats.total_turns}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="flex items-center space-x-2 text-gray-500 mb-2">
                <BookOpen size={16} />
                <span className="text-sm">会话数</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stats.sessions}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="flex items-center space-x-2 text-gray-500 mb-2">
                <User size={16} />
                <span className="text-sm">薄弱知识点</span>
              </div>
              <p className="text-2xl font-bold text-orange-600">{stats.weak_topics}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="flex items-center space-x-2 text-gray-500 mb-2">
                <Brain size={16} />
                <span className="text-sm">档案记忆</span>
              </div>
              <p className="text-2xl font-bold text-blue-600">{stats.archival_entries}</p>
            </div>
          </div>
        )}

        {/* 用户画像 */}
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-semibold text-gray-800 mb-4">用户画像</h3>

          <div className="space-y-4">
            {/* 名称 */}
            <div>
              <label className="text-sm text-gray-500">名称</label>
              <p className="text-gray-900">{profile?.name || '未设置'}</p>
            </div>

            {/* 学习风格 */}
            <div>
              <label className="text-sm text-gray-500">学习风格</label>
              <p className="text-gray-900">{profile?.learning_style || '未设置'}</p>
            </div>

            {/* 薄弱知识点 */}
            <div>
              <label className="text-sm text-gray-500 mb-2 block">薄弱知识点</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {profile?.weak_topics?.map((topic, idx) => (
                  <span
                    key={idx}
                    className="text-sm px-3 py-1 bg-orange-100 text-orange-700 rounded-full"
                  >
                    {topic}
                  </span>
                ))}
                {(!profile?.weak_topics || profile.weak_topics.length === 0) && (
                  <span className="text-sm text-gray-400">暂无</span>
                )}
              </div>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newWeakTopic}
                  onChange={e => setNewWeakTopic(e.target.value)}
                  placeholder="添加薄弱知识点..."
                  className="flex-1 px-3 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onKeyDown={e => e.key === 'Enter' && handleAddWeakTopic()}
                />
                <button
                  onClick={handleAddWeakTopic}
                  className="px-3 py-1.5 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 transition-colors"
                >
                  添加
                </button>
              </div>
            </div>

            {/* 擅长领域 */}
            <div>
              <label className="text-sm text-gray-500 mb-2 block">擅长领域</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {profile?.strong_topics?.map((topic, idx) => (
                  <span
                    key={idx}
                    className="text-sm px-3 py-1 bg-green-100 text-green-700 rounded-full"
                  >
                    {topic}
                  </span>
                ))}
                {(!profile?.strong_topics || profile.strong_topics.length === 0) && (
                  <span className="text-sm text-gray-400">暂无</span>
                )}
              </div>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newStrongTopic}
                  onChange={e => setNewStrongTopic(e.target.value)}
                  placeholder="添加擅长领域..."
                  className="flex-1 px-3 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onKeyDown={e => e.key === 'Enter' && handleAddStrongTopic()}
                />
                <button
                  onClick={handleAddStrongTopic}
                  className="px-3 py-1.5 bg-green-500 text-white text-sm rounded-lg hover:bg-green-600 transition-colors"
                >
                  添加
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
