/**
 * 大纲编辑器
 * 支持编辑、确认、返回
 */

import { Loader2, ArrowLeft, ArrowRight } from 'lucide-react';

interface OutlineEditorProps {
  outline: string;
  onOutlineChange: (outline: string) => void;
  onConfirm: () => void;
  onBack: () => void;
  isLoading: boolean;
}

export default function OutlineEditor({
  outline,
  onOutlineChange,
  onConfirm,
  onBack,
  isLoading,
}: OutlineEditorProps) {
  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* 提示信息 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-blue-700 text-sm">
          以下是根据你的主题生成的文章大纲。你可以直接编辑大纲内容，确认后将生成完整文章。
        </p>
      </div>

      {/* 编辑区域 */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <textarea
          value={outline}
          onChange={(e) => onOutlineChange(e.target.value)}
          rows={20}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="大纲内容..."
        />
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          <ArrowLeft className="w-4 h-4" />
          返回修改
        </button>

        <button
          onClick={onConfirm}
          disabled={isLoading || !outline.trim()}
          className="flex items-center gap-2 px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              生成中...
            </>
          ) : (
            <>
              确认大纲，生成文章
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
