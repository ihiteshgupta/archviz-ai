'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, File, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  accept?: string;
  maxSize?: number;
  disabled?: boolean;
  compact?: boolean;
}

export default function FileUpload({
  onUpload,
  accept = '.dwg,.dxf',
  maxSize = 50 * 1024 * 1024, // 50MB
  disabled = false,
  compact = false,
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setDragOver(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const validateFile = (file: File): string | null => {
    const ext = file.name.toLowerCase().split('.').pop();
    if (!ext || !['dwg', 'dxf'].includes(ext)) {
      return 'Invalid file type. Only .dwg and .dxf files are supported.';
    }
    if (file.size > maxSize) {
      return `File too large. Maximum size is ${Math.round(maxSize / 1024 / 1024)}MB.`;
    }
    return null;
  };

  const processFile = async (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setUploadStatus('error');
      return;
    }

    setSelectedFile(file);
    setError(null);
    setUploading(true);
    setUploadStatus('idle');

    try {
      await onUpload(file);
      setUploadStatus('success');
      // Reset after success in compact mode
      if (compact) {
        setTimeout(() => {
          handleClear();
        }, 2000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploadStatus('error');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file) {
        processFile(file);
      }
    },
    [disabled, onUpload, maxSize]
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleClick = () => {
    if (!disabled && !uploading) {
      inputRef.current?.click();
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setUploadStatus('idle');
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  // Compact version for quick upload zone
  if (compact) {
    return (
      <div
        className={cn(
          'relative',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled || uploading}
        />

        <button
          type="button"
          onClick={handleClick}
          disabled={disabled || uploading}
          className={cn(
            'px-4 py-2 rounded-lg font-medium text-sm transition-all',
            'bg-primary-600 text-white hover:bg-primary-700',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            dragOver && 'ring-2 ring-primary-300 ring-offset-2',
            uploadStatus === 'success' && 'bg-emerald-600 hover:bg-emerald-700',
            uploadStatus === 'error' && 'bg-red-600 hover:bg-red-700'
          )}
        >
          {uploading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading...
            </span>
          ) : uploadStatus === 'success' ? (
            <span className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Uploaded!
            </span>
          ) : uploadStatus === 'error' ? (
            <span className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Failed
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Browse Files
            </span>
          )}
        </button>

        {error && (
          <p className="absolute top-full mt-1 text-xs text-red-600 whitespace-nowrap">
            {error}
          </p>
        )}
      </div>
    );
  }

  // Full dropzone version
  return (
    <div className="w-full">
      <div
        className={cn(
          'dropzone cursor-pointer',
          dragOver && 'drag-over',
          disabled && 'opacity-50 cursor-not-allowed',
          uploadStatus === 'success' && 'border-emerald-500 bg-emerald-50',
          uploadStatus === 'error' && 'border-red-500 bg-red-50'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled || uploading}
        />

        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
            <p className="text-gray-600">Uploading and parsing...</p>
          </div>
        ) : selectedFile ? (
          <div className="flex flex-col items-center gap-3">
            {uploadStatus === 'success' ? (
              <CheckCircle className="w-12 h-12 text-emerald-500" />
            ) : uploadStatus === 'error' ? (
              <AlertCircle className="w-12 h-12 text-red-500" />
            ) : (
              <File className="w-12 h-12 text-primary-500" />
            )}
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900">{selectedFile.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
                className="p-1 hover:bg-gray-200 rounded"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            {uploadStatus === 'success' && (
              <p className="text-emerald-600 text-sm">File uploaded and parsed successfully!</p>
            )}
            {error && <p className="text-red-600 text-sm">{error}</p>}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-xl bg-primary-100 flex items-center justify-center">
              <Upload className="w-7 h-7 text-primary-600" />
            </div>
            <div className="text-center">
              <p className="text-gray-600">
                <span className="font-medium text-primary-600">Click to upload</span> or drag and
                drop
              </p>
              <p className="text-gray-400 text-sm mt-1">DWG or DXF files up to 50MB</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
