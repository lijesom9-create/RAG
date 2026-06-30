/**
 * 博客写作页面
 * 三栏布局：左侧任务进度 + 中间内容编辑 + 右侧预览
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  FileText,
  Wand2,
  Loader2,
  Check,
  Eye,
  Download,
  Copy,
} from 'lucide-react';
import { blogApi } from '@/services/api';
import OutlineEditor from './OutlineEditor';
import ContentPreview from './ContentPreview';

type Step = 'input' | 'outline' | 'content' | 'done';

export default function BlogWriterPage() {
  const [step, setStep] = useState<Step>('input');
  const [topic, setTopic] = useState('');
  const [articleType, setArticleType] = useState('博客');
  const [requirements, setRequirements] = useState('');
  const [urls, setUrls] = useState('');
  const [outline, setOutline] = useState('');
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // 生成博客
  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError('请输入主题');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // 生成大纲
      const outlineResponse = await blogApi.generateOutline({
        topic,
        article_type: articleType,
      });

      setOutline(outlineResponse.data.outline);
      setStep('outline');
    } catch (err: any) {
      setError(err.response?.data?.detail || '生成失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  // 生成内容
  const handleGenerateContent = async () => {
    setIsLoading(true);
    setError('');

    try {
      const response = await blogApi.generateContent({
        topic,
        outline,
        style: 'technical',
      });

      setContent(response.data.content);
      setStep('content');
    } catch (err: any) {
      setError(err.response?.data?.detail || '内容生成失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  // 完成
  const handleDone = () => {
    setStep('done');
  };

  // 复制内容
  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    alert('已复制到剪贴板');
  };

  // 下载 Markdown
  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${topic}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 重新开始
  const handleRestart = () => {
    setStep('input');
    setTopic('');
    setOutline('');
    setContent('');
    setError('');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 左侧：任务进度 */}
      <div className="w-64 bg-white border-r border-gray-200 p-4">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5" />
          博客写作
        </h2>

        {/* 步骤指示器 */}
        <div className="space-y-2">
          <StepItem
            step={1}
            title="输入主题"
            current={step === 'input'}
            completed={step !== 'input'}
          />
          <StepItem
            step={2}
            title="确认大纲"
            current={step === 'outline'}
            completed={step === 'content' || step === 'done'}
          />
          <StepItem
            step={3}
            title="生成内容"
            current={step === 'content'}
            completed={step === 'done'}
          />
          <StepItem
            step={4}
            title="完成"
            current={step === 'done'}
            completed={false}
          />
        </div>

        {/* 操作按钮 */}
        <div className="mt-6 space-y-2">
          {step === 'done' && (
            <>
              <button
                onClick={handleCopy}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                <Copy className="w-4 h-4" />
                复制内容
              </button>
              <button
                onClick={handleDownload}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
              >
                <Download className="w-4 h-4" />
                下载 Markdown
              </button>
              <button
                onClick={handleRestart}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
              >
                重新开始
              </button>
            </>
          )}
        </div>
      </div>

      {/* 中间：内容区域 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部标题栏 */}
        <div className="bg-white border-b border-gray-200 px-6 py-3">
          <h1 className="text-xl font-semibold">
            {step === 'input' && '输入博客信息'}
            {step === 'outline' && '确认文章大纲'}
            {step === 'content' && '编辑文章内容'}
            {step === 'done' && '博客生成完成'}
          </h1>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-auto p-6">
          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {/* 步骤 1：输入主题 */}
          {step === 'input' && (
            <div className="max-w-2xl mx-auto space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  博客主题 *
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="例如：LangChain Agent 入门指南"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  文章类型
                </label>
                <select
                  value={articleType}
                  onChange={(e) => setArticleType(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="博客">博客</option>
                  <option value="教程">教程</option>
                  <option value="技术文档">技术文档</option>
                  <option value="报告">报告</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  特殊要求（可选）
                </label>
                <textarea
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  placeholder="例如：需要包含代码示例，面向初学者"
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  参考 URL（可选，每行一个）
                </label>
                <textarea
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  placeholder="https://example.com/docs&#10;https://example.com/blog"
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={isLoading || !topic.trim()}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-5 h-5" />
                    生成大纲
                  </>
                )}
              </button>
            </div>
          )}

          {/* 步骤 2：确认大纲 */}
          {step === 'outline' && (
            <OutlineEditor
              outline={outline}
              onOutlineChange={setOutline}
              onConfirm={handleGenerateContent}
              onBack={() => setStep('input')}
              isLoading={isLoading}
            />
          )}

          {/* 步骤 3：编辑内容 */}
          {step === 'content' && (
            <ContentPreview
              content={content}
              onContentChange={setContent}
              onConfirm={handleDone}
              onBack={() => setStep('outline')}
            />
          )}

          {/* 步骤 4：完成 */}
          {step === 'done' && (
            <div className="max-w-4xl mx-auto">
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Check className="w-6 h-6 text-green-500" />
                  <h2 className="text-xl font-semibold">博客生成完成</h2>
                </div>
                <p className="text-gray-600 mb-4">
                  共 {content.length} 字，已准备好导出。
                </p>
                <div className="prose max-w-none">
                  <ReactMarkdown>{content}</ReactMarkdown>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 右侧：实时预览 */}
      {step !== 'input' && step !== 'done' && (
        <div className="w-96 bg-white border-l border-gray-200 overflow-auto">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold flex items-center gap-2">
              <Eye className="w-4 h-4" />
              实时预览
            </h3>
          </div>
          <div className="p-4 prose prose-sm max-w-none">
            <ReactMarkdown>{step === 'outline' ? outline : content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

// 步骤指示器组件
function StepItem({
  step,
  title,
  current,
  completed,
}: {
  step: number;
  title: string;
  current: boolean;
  completed: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-3 p-2 rounded-lg ${
        current
          ? 'bg-blue-50 text-blue-700'
          : completed
          ? 'text-green-600'
          : 'text-gray-400'
      }`}
    >
      <div
        className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
          current
            ? 'bg-blue-500 text-white'
            : completed
            ? 'bg-green-500 text-white'
            : 'bg-gray-200 text-gray-500'
        }`}
      >
        {completed ? <Check className="w-4 h-4" /> : step}
      </div>
      <span className="text-sm font-medium">{title}</span>
    </div>
  );
}
