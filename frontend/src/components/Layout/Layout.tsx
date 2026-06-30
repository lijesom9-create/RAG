/**
 * 布局组件
 * 知识助手 - 顶部导航 + 主内容区
 */

import { Outlet, useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { LogOut, User, MessageSquare, FileText, Brain } from 'lucide-react';

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // 导航链接
  const navLinks = [
    { path: '/', label: '问答', icon: MessageSquare },
    { path: '/documents', label: '文档', icon: FileText },
    { path: '/memory', label: '记忆', icon: Brain },
  ];

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部导航栏 */}
      <header className="bg-white shadow-sm border-b border-gray-200 flex-shrink-0">
        <div className="px-4 sm:px-6">
          <div className="flex justify-between items-center h-12">
            {/* Logo + 导航 */}
            <div className="flex items-center space-x-6">
              <h1 className="text-lg font-bold text-blue-600">
                🧠 知识助手
              </h1>

              {/* 导航链接 */}
              <nav className="hidden sm:flex items-center space-x-1">
                {navLinks.map(({ path, label, icon: Icon }) => {
                  const isActive = location.pathname === path;
                  return (
                    <Link
                      key={path}
                      to={path}
                      className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                        isActive
                          ? 'bg-blue-50 text-blue-600'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      <Icon size={16} />
                      <span>{label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* 用户菜单 */}
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 text-gray-700">
                <User size={16} />
                <span className="text-sm font-medium hidden sm:inline">{user?.username}</span>
              </div>

              <button
                onClick={handleLogout}
                className="flex items-center space-x-1 px-2 py-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <LogOut size={16} />
                <span className="text-xs hidden sm:inline">退出</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
