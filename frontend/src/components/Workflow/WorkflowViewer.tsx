/**
 * 工作流可视化组件
 * 展示工作流执行进度和状态
 */

import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  ChevronDown,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';

interface TaskState {
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

interface WorkflowState {
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

interface WorkflowViewerProps {
  workflow: WorkflowState;
  onRefresh?: () => void;
}

export default function WorkflowViewer({ workflow, onRefresh }: WorkflowViewerProps) {
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

  const toggleTask = (taskId: string) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 border-green-200';
      case 'failed':
        return 'bg-red-50 border-red-200';
      case 'running':
        return 'bg-blue-50 border-blue-200';
      case 'pending':
        return 'bg-gray-50 border-gray-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getOverallStatusIcon = () => {
    switch (workflow.status) {
      case 'completed':
        return <CheckCircle className="w-6 h-6 text-green-500" />;
      case 'failed':
        return <XCircle className="w-6 h-6 text-red-500" />;
      case 'running':
        return <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-6 h-6 text-gray-400" />;
    }
  };

  const tasks = Object.values(workflow.tasks);
  const progressPercent = Math.round(workflow.progress.progress * 100);

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* 头部 */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getOverallStatusIcon()}
          <div>
            <h3 className="font-semibold text-gray-900">工作流执行状态</h3>
            <p className="text-sm text-gray-500">ID: {workflow.workflow_id}</p>
          </div>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* 进度条 */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            进度: {workflow.progress.completed}/{workflow.progress.total}
          </span>
          <span className="text-sm text-gray-500">{progressPercent}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              workflow.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-green-500" />
            完成: {workflow.progress.completed}
          </span>
          <span className="flex items-center gap-1">
            <Loader2 className="w-3 h-3 text-blue-500" />
            运行中: {workflow.progress.running}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-gray-400" />
            等待: {workflow.progress.pending}
          </span>
          {workflow.progress.failed > 0 && (
            <span className="flex items-center gap-1">
              <XCircle className="w-3 h-3 text-red-500" />
              失败: {workflow.progress.failed}
            </span>
          )}
        </div>
      </div>

      {/* 任务列表 */}
      <div className="divide-y divide-gray-100">
        {tasks.map((task) => (
          <div key={task.task_id} className={getStatusColor(task.status)}>
            {/* 任务头部 */}
            <button
              onClick={() => toggleTask(task.task_id)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-opacity-80"
            >
              <div className="flex items-center gap-3">
                {getStatusIcon(task.status)}
                <div className="text-left">
                  <p className="font-medium text-gray-900">{task.task_name}</p>
                  <p className="text-xs text-gray-500">
                    {task.task_type}
                    {task.duration && ` · ${task.duration.toFixed(1)}s`}
                  </p>
                </div>
              </div>
              {expandedTasks.has(task.task_id) ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )}
            </button>

            {/* 任务详情 */}
            {expandedTasks.has(task.task_id) && (
              <div className="px-4 pb-3 pt-1">
                {task.result && (
                  <div className="mt-2 p-2 bg-white rounded border border-gray-200">
                    <p className="text-xs font-medium text-gray-500 mb-1">结果:</p>
                    <p className="text-sm text-gray-700">{task.result}</p>
                  </div>
                )}
                {task.error && (
                  <div className="mt-2 p-2 bg-red-50 rounded border border-red-200">
                    <p className="text-xs font-medium text-red-500 mb-1">错误:</p>
                    <p className="text-sm text-red-700">{task.error}</p>
                  </div>
                )}
                {task.started_at && (
                  <p className="text-xs text-gray-500 mt-2">
                    开始时间: {new Date(task.started_at).toLocaleString()}
                  </p>
                )}
                {task.completed_at && (
                  <p className="text-xs text-gray-500">
                    完成时间: {new Date(task.completed_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 底部信息 */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
        创建时间: {new Date(workflow.created_at).toLocaleString()}
      </div>
    </div>
  );
}
