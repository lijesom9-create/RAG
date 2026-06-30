/**
 * 内联文档上传组件
 * 用于右侧面板中的资料上传
 */

import { useState, useCallback } from 'react';
import { documentsApi } from '@/services/api';
import { Upload, Loader2 } from 'lucide-react';

interface DocumentUploaderProps {
  topicId: string;
  onUploadComplete: () => void;
}

export default function DocumentUploader({ topicId, onUploadComplete }: DocumentUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    try {
      setUploading(true);
      for (let i = 0; i < files.length; i++) {
        await documentsApi.upload(topicId, files[i]);
      }
      onUploadComplete();
    } catch (err) {
      console.error('上传失败:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  }, [topicId]);

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer ${
        dragActive
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
      }`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <label className="cursor-pointer">
        <input
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.doc,.docx,.txt"
          onChange={(e) => handleUpload(e.target.files)}
        />
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-blue-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">上传中...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <Upload className="w-5 h-5 text-gray-400" />
            <span className="text-xs text-gray-500">
              拖拽或<span className="text-blue-500">点击上传</span>
            </span>
            <span className="text-[10px] text-gray-400">PDF、Word、TXT</span>
          </div>
        )}
      </label>
    </div>
  );
}
