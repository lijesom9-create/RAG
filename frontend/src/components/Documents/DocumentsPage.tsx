/**
 * 文档管理页面
 * 上传、列表、删除文档
 */

import { useState, useEffect, useRef } from 'react';
import { FileText, Trash2, Loader2, File, FileUp } from 'lucide-react';
import { documentsApiNew } from '@/services/api';

interface Document {
  document_id: string;
  filename: string;
  title: string;
  status: string;
  chunk_count: number;
  char_count: number;
  created_at: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载文档列表
  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await documentsApiNew.list();
      setDocuments(response.documents || []);
    } catch (error) {
      console.error('加载文档失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  // 上传文档
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await documentsApiNew.upload(file);
      await loadDocuments();
    } catch (error) {
      console.error('上传失败:', error);
      alert('上传失败，请重试');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // 删除文档
  const handleDelete = async (documentId: string) => {
    if (!confirm('确定要删除这个文档吗？')) return;

    try {
      await documentsApiNew.delete(documentId);
      await loadDocuments();
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败，请重试');
    }
  };

  // 状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'processing':
        return 'bg-yellow-100 text-yellow-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  // 状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'processing':
        return '处理中';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-white">
        <h2 className="text-lg font-semibold text-gray-800">文档管理</h2>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          {uploading ? (
            <Loader2 className="animate-spin" size={18} />
          ) : (
            <FileUp size={18} />
          )}
          <span>{uploading ? '上传中...' : '上传文档'}</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={handleUpload}
          className="hidden"
        />
      </div>

      {/* 文档列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="animate-spin text-gray-400" size={32} />
          </div>
        ) : documents.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <FileText size={48} className="mx-auto mb-4 opacity-50" />
              <p className="text-lg mb-2">还没有文档</p>
              <p className="text-sm">上传 PDF、Word、TXT 或 Markdown 文件</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-4">
            {documents.map(doc => (
              <div
                key={doc.document_id}
                className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <File className="text-blue-500 mt-1" size={20} />
                    <div>
                      <h3 className="font-medium text-gray-900">{doc.title || doc.filename}</h3>
                      <div className="flex items-center space-x-3 mt-1 text-sm text-gray-500">
                        <span>{doc.filename}</span>
                        <span>•</span>
                        <span>{doc.chunk_count} 个分块</span>
                        <span>•</span>
                        <span>{(doc.char_count / 1000).toFixed(1)}k 字符</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(doc.status)}`}>
                      {getStatusText(doc.status)}
                    </span>
                    <button
                      onClick={() => handleDelete(doc.document_id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 底部统计 */}
      <div className="border-t bg-white px-6 py-3">
        <p className="text-sm text-gray-500">
          共 {documents.length} 个文档
        </p>
      </div>
    </div>
  );
}
