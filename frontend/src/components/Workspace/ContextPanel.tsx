/**
 * 右侧面板：资料、计划、回顾
 * Tab 切换三个功能区域
 */

import { useState, useEffect } from 'react';
import {
  documentsApi,
  studyPlansApi,
  evaluationApi,
  type Document,
  type StudyPlan,
  type EvaluationSummary,
  type LearningReport,
} from '@/services/api';
import {
  FileText,
  Calendar,
  BarChart3,
  Trash2,
  Sparkles,
  Loader2,
  CheckCircle2,
  Clock,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Lightbulb,
  Play,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import DocumentUploader from './DocumentUploader';

interface ContextPanelProps {
  topicId: string | null;
  onSendMessage?: (message: string) => void;
}

type TabType = 'documents' | 'plans' | 'review';

export default function ContextPanel({ topicId, onSendMessage }: ContextPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('documents');

  return (
    <div className="flex flex-col h-full">
      {/* Tab 头 */}
      <div className="flex border-b border-gray-200 bg-gray-50">
        {[
          { key: 'documents' as TabType, label: '资料', icon: FileText },
          { key: 'plans' as TabType, label: '计划', icon: Calendar },
          { key: 'review' as TabType, label: '回顾', icon: BarChart3 },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? 'text-blue-600 border-b-2 border-blue-600 bg-white'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <tab.icon size={14} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div className="flex-1 overflow-y-auto">
        {topicId ? (
          <>
            {activeTab === 'documents' && <DocumentsTab topicId={topicId} />}
            {activeTab === 'plans' && <PlansTab topicId={topicId} onSendMessage={onSendMessage} />}
            {activeTab === 'review' && <ReviewTab />}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm">
            <FileText size={24} className="mb-2 opacity-50" />
            <span>请先选择一个学习主题</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ========== 资料 Tab ==========

function DocumentsTab({ topicId }: { topicId: string }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocuments();
  }, [topicId]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const resp = await documentsApi.list(topicId);
      const data = resp.data as any;
      setDocuments(Array.isArray(data) ? data : (data.documents || []));
    } catch (err) {
      console.error('加载文档失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('确定删除这个资料吗？')) return;
    try {
      await documentsApi.delete(topicId, documentId);
      await loadDocuments();
    } catch (err) {
      console.error('删除失败:', err);
    }
  };

  const statusIcons: Record<string, any> = {
    completed: <CheckCircle2 className="w-3 h-3 text-green-500" />,
    processing: <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />,
    pending: <Clock className="w-3 h-3 text-yellow-500" />,
    failed: <AlertCircle className="w-3 h-3 text-red-500" />,
  };

  const fileIcons: Record<string, string> = {
    pdf: '📄',
    docx: '📝',
    doc: '📝',
    txt: '📃',
  };

  return (
    <div className="p-3 space-y-3">
      {/* 上传区域 */}
      <DocumentUploader topicId={topicId} onUploadComplete={loadDocuments} />

      {/* 文档列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 size={16} className="animate-spin text-gray-400" />
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-4 text-gray-400 text-xs">
          还没有学习资料
        </div>
      ) : (
        <div className="space-y-1.5">
          {documents.map((doc) => (
            <div
              key={doc.document_id}
              className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg group"
            >
              <span className="text-sm flex-shrink-0">
                {fileIcons[doc.doc_type] || '📄'}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-gray-900 truncate">
                  {doc.filename}
                </div>
                <div className="flex items-center gap-2 text-[10px] text-gray-500">
                  <span className="uppercase">{doc.doc_type}</span>
                  {doc.chunk_count > 0 && <span>{doc.chunk_count}块</span>}
                </div>
              </div>
              <div className="flex items-center gap-1">
                {statusIcons[doc.status]}
                <button
                  onClick={() => handleDelete(doc.document_id)}
                  className="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ========== 计划 Tab ==========

function PlansTab({ topicId, onSendMessage }: { topicId: string; onSendMessage?: (msg: string) => void }) {
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expandedPlan, setExpandedPlan] = useState<string | null>(null);

  useEffect(() => {
    loadPlans();
  }, [topicId]);

  const loadPlans = async () => {
    try {
      setLoading(true);
      const resp = await studyPlansApi.list(topicId);
      const data = resp.data as any;
      setPlans(Array.isArray(data) ? data : (data.plans || []));
    } catch (err) {
      console.error('加载计划失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      await studyPlansApi.generate(topicId);
      await loadPlans();
    } catch (err) {
      console.error('生成计划失败:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (planId: string) => {
    if (!confirm('确定删除这个学习计划吗？')) return;
    try {
      await studyPlansApi.delete(planId);
      await loadPlans();
    } catch (err) {
      console.error('删除失败:', err);
    }
  };

  const taskTypeLabels: Record<string, string> = {
    read: '阅读',
    practice: '练习',
    review: '复习',
    project: '项目',
  };

  const taskTypeColors: Record<string, string> = {
    read: 'bg-blue-100 text-blue-700',
    practice: 'bg-green-100 text-green-700',
    review: 'bg-yellow-100 text-yellow-700',
    project: 'bg-purple-100 text-purple-700',
  };

  return (
    <div className="p-3 space-y-3">
      {/* 生成按钮 */}
      <button
        onClick={handleGenerate}
        disabled={generating}
        className="w-full flex items-center justify-center gap-2 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 text-sm"
      >
        {generating ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Sparkles size={14} />
        )}
        {generating ? '生成中...' : 'AI 生成计划'}
      </button>

      {/* 计划列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 size={16} className="animate-spin text-gray-400" />
        </div>
      ) : plans.length === 0 ? (
        <div className="text-center py-4 text-gray-400 text-xs">
          <Calendar size={20} className="mx-auto mb-2 opacity-50" />
          还没有学习计划
        </div>
      ) : (
        <div className="space-y-2">
          {plans.map((plan) => (
            <div key={plan.plan_id} className="border rounded-lg overflow-hidden">
              {/* 计划头部 */}
              <div
                className="p-2.5 flex items-center gap-2 cursor-pointer hover:bg-gray-50"
                onClick={() => setExpandedPlan(expandedPlan === plan.plan_id ? null : plan.plan_id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-gray-900 truncate">{plan.title}</div>
                  <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
                    <span>{plan.total_days}天</span>
                    <span>{plan.phases.length}阶段</span>
                    <span>{plan.total_tasks}任务</span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSendMessage?.(`开始学习：${plan.title}`);
                    }}
                    className="p-1 text-blue-500 hover:text-blue-600"
                    title="开始学习"
                  >
                    <Play size={12} />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(plan.plan_id);
                    }}
                    className="p-1 text-gray-400 hover:text-red-500"
                    title="删除"
                  >
                    <Trash2 size={12} />
                  </button>
                  {expandedPlan === plan.plan_id ? (
                    <ChevronDown size={12} className="text-gray-400" />
                  ) : (
                    <ChevronRight size={12} className="text-gray-400" />
                  )}
                </div>
              </div>

              {/* 阶段详情 */}
              {expandedPlan === plan.plan_id && (
                <div className="border-t">
                  {plan.phases.map((phase, idx) => (
                    <div key={idx} className="p-2.5 border-b last:border-b-0 bg-gray-50">
                      <div className="flex items-center gap-2 mb-1.5">
                        <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-[10px] font-semibold">
                          {idx + 1}
                        </div>
                        <span className="text-xs font-medium text-gray-900">{phase.title}</span>
                        <span className="text-[10px] text-gray-500">{phase.duration_days}天</span>
                      </div>
                      <div className="ml-7 space-y-1">
                        {phase.tasks.map((task, taskIdx) => (
                          <div key={taskIdx} className="flex items-center gap-2">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${taskTypeColors[task.type] || 'bg-gray-100'}`}>
                              {taskTypeLabels[task.type] || task.type}
                            </span>
                            <span className="text-[11px] text-gray-700 truncate flex-1">{task.title}</span>
                            <span className="text-[10px] text-gray-400">{task.estimated_minutes}分</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ========== 回顾 Tab ==========

function ReviewTab() {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [report, setReport] = useState<LearningReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [summaryResp, reportResp] = await Promise.all([
        evaluationApi.summary(),
        evaluationApi.report(),
      ]);
      setSummary(summaryResp.data);
      setReport(reportResp.data);
    } catch (err) {
      console.error('加载学习数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const trendIcons: Record<string, any> = {
    improving: <TrendingUp className="w-4 h-4 text-green-500" />,
    declining: <TrendingDown className="w-4 h-4 text-red-500" />,
    stable: <Minus className="w-4 h-4 text-gray-500" />,
  };

  const trendLabels: Record<string, string> = {
    improving: '进步中',
    declining: '需要关注',
    stable: '保持稳定',
    no_data: '暂无数据',
    insufficient_data: '数据不足',
  };

  const trendColors: Record<string, string> = {
    improving: 'text-green-600 bg-green-50',
    declining: 'text-red-600 bg-red-50',
    stable: 'text-gray-600 bg-gray-50',
    no_data: 'text-gray-500 bg-gray-50',
    insufficient_data: 'text-yellow-600 bg-yellow-50',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 size={16} className="animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="p-3 space-y-3">
      {/* 概览卡片 */}
      {summary && (
        <div className="grid grid-cols-3 gap-2">
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">{summary.total_evaluations}</div>
            <div className="text-[10px] text-gray-500">评估次数</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">
              {summary.average_score > 0 ? `${(summary.average_score * 100).toFixed(0)}%` : '--'}
            </div>
            <div className="text-[10px] text-gray-500">平均分数</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-center gap-1">
              {trendIcons[summary.improvement_trend] || <Minus className="w-4 h-4 text-gray-400" />}
            </div>
            <div className={`text-[10px] mt-0.5 ${trendColors[summary.improvement_trend]?.split(' ')[0] || 'text-gray-500'}`}>
              {trendLabels[summary.improvement_trend] || '未知'}
            </div>
          </div>
        </div>
      )}

      {/* 学习摘要 */}
      {report?.summary && report.summary !== '暂无学习数据，开始学习后将自动生成报告。' && (
        <div className="p-2.5 bg-blue-50 rounded-lg">
          <div className="text-xs text-blue-800">{report.summary}</div>
        </div>
      )}

      {/* 学习洞察 */}
      {report?.insights && report.insights.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs font-medium text-gray-700">学习洞察</div>
          {report.insights.slice(0, 3).map((insight, idx) => (
            <div key={idx} className="p-2 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-1.5 mb-1">
                <Lightbulb size={10} className="text-yellow-500" />
                <span className="text-[10px] font-medium text-gray-700">{insight.finding}</span>
              </div>
              {insight.suggestion && (
                <div className="text-[10px] text-blue-600 ml-4">{insight.suggestion}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 改进建议 */}
      {report?.recommendations && report.recommendations.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs font-medium text-gray-700">改进建议</div>
          {report.recommendations.slice(0, 3).map((rec, idx) => (
            <div key={idx} className="flex items-start gap-1.5 p-2 bg-gray-50 rounded-lg">
              <CheckCircle2 size={10} className="text-green-500 mt-0.5 flex-shrink-0" />
              <span className="text-[10px] text-gray-600">{rec}</span>
            </div>
          ))}
        </div>
      )}

      {/* 空状态 */}
      {(!report || report.summary === '暂无学习数据，开始学习后将自动生成报告。') && (
        <div className="text-center py-4 text-gray-400 text-xs">
          <BarChart3 size={20} className="mx-auto mb-2 opacity-50" />
          开始学习后将自动生成报告
        </div>
      )}
    </div>
  );
}
