/**
 * 内容预览
 * 支持编辑、确认、返回
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ArrowLeft, Check, Edit3, Eye } from 'lucide-react';

interface ContentPreviewProps {
  content: string;
  onContentChange: (content: string) => void;
  onConfirm: () => void;
  onBack: () => void;
}

export default function ContentPreview({
  content,
  onContentChange,
  onConfirm,
  onBack,
}: ContentPreviewProps) {
  const [isEditing, setIsEditing] = useState(false);

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* 提示信息 */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <p className="text-green-700 text-sm">
          文章已生成完成！你可以编辑内容或直接确认导出。
        </p>
      </div>

      {/* 工具栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
              isEditing
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {isEditing ? (
              <>
                <Eye className="w-4 h-4" />
                预览模式
              </>
            ) : (
              <>
                <Edit3 className="w-4 h-4" />
                编辑模式
              </>
            )}
          </button>
          <span className="text-sm text-gray-500">
            共 {content.length} 字
          </span>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        {isEditing ? (
          <textarea
            value={content}
            onChange={(e) => onContentChange(e.target.value)}
            rows={30}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          />
        ) : (
          <div className="prose max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          <ArrowLeft className="w-4 h-4" />
          返回大纲
        </button>

        <button
          onClick={onConfirm}
          className="flex items-center gap-2 px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          <Check className="w-4 h-4" />
          确认完成
        </button>
      </div>
    </div>
  );
}
