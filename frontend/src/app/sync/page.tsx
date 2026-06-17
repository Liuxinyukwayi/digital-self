'use client';

import { useEffect, useRef, useState } from 'react';
import { apiGet, apiPost } from '@/lib/api';

type SyncSource = {
  name: string;
  type: string;
  enabled: boolean;
  mode: string;
};

type SyncStatus = {
  source: string;
  status: string;
  last_sync: string | null;
  items_synced: number;
};

const sourceIcons: Record<string, string> = {
  wechat: '💬',
  qq: '🐧',
  feishu: '📄',
  github: '⚡',
  email: '✉',
};

export default function SyncPage() {
  const [sources, setSources] = useState<SyncSource[]>([]);
  const [statuses, setStatuses] = useState<SyncStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [importing, setImporting] = useState<string | null>(null);
  const [result, setResult] = useState<string>('');
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    async function load() {
      try {
        const [srcData, statusData] = await Promise.all([
          apiGet<{ sources: SyncSource[] }>('/sync/sources'),
          apiGet<{ statuses: SyncStatus[] }>('/sync/status'),
        ]);
        setSources(srcData.sources);
        setStatuses(statusData.statuses);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleFileImport(sourceType: string, file: File) {
    setImporting(sourceType);
    setError('');
    setResult('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const data = await apiPost<{ status: string; filename: string; imported?: number }>(
        `/sync/import/${sourceType}`,
        formData,
      );
      setResult(`${sourceType}: 导入成功${data.imported ? `，共 ${data.imported} 条` : ''}`);
      const statusData = await apiGet<{ statuses: SyncStatus[] }>('/sync/status');
      setStatuses(statusData.statuses);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${sourceType} 导入失败`);
    } finally {
      setImporting(null);
      if (fileRefs.current[sourceType]) fileRefs.current[sourceType]!.value = '';
    }
  }

  function getStatusForSource(type: string): SyncStatus | undefined {
    return statuses.find((s) => s.source === type);
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">数据同步</h1>
        <p className="page-subtitle">导入聊天记录和文档，自动进入 RAG 检索系统</p>
      </div>

      {error && (
        <div className="alert-error mb-4">
          {error}
          <button onClick={() => setError('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      {result && (
        <div className="alert-success mb-4">
          {result}
          <button onClick={() => setResult('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          {loading ? (
            <div className="panel panel-pad text-sm text-slate-500">加载中...</div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {sources.map((source) => {
                const status = getStatusForSource(source.type);
                const busy = importing === source.type;
                return (
                  <div key={source.type} className="panel panel-pad panel-hover animate-fade-in">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-xl">
                        {sourceIcons[source.type] || '📁'}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-bold text-slate-900">{source.name}</h3>
                        <p className="text-xs text-slate-500">
                          {status?.items_synced ? `已同步 ${status.items_synced} 条` : '尚未同步'}
                        </p>
                      </div>
                    </div>
                    <label className={`btn-primary mt-4 block w-full cursor-pointer text-center text-xs ${busy ? 'opacity-50' : ''}`}>
                      {busy ? '导入中...' : '选择文件导入'}
                      <input
                        ref={(el) => { fileRefs.current[source.type] = el; }}
                        type="file"
                        className="hidden"
                        accept=".json,.jsonl,.txt,.csv,.md"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileImport(source.type, file);
                        }}
                        disabled={busy}
                      />
                    </label>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="panel panel-pad">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">同步状态</h2>
            {statuses.length === 0 ? (
              <p className="text-xs text-slate-400">暂无同步记录</p>
            ) : (
              <div className="space-y-2">
                {statuses.map((status) => (
                  <div key={status.source} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div>
                      <span className="text-sm font-semibold text-slate-800">{status.source}</span>
                      <p className="text-xs text-slate-400">
                        {status.last_sync ? `上次: ${status.last_sync}` : '未同步'}
                      </p>
                    </div>
                    <span className="chip">{status.items_synced}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel panel-pad">
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">接入说明</h2>
            <ul className="space-y-2 text-xs leading-5 text-slate-600">
              <li>• 微信/QQ：导出 JSON 聊天记录后上传</li>
              <li>• 飞书：导出文档后上传</li>
              <li>• GitHub：导出活动记录后上传</li>
              <li>• 邮件：导出邮件后上传</li>
              <li>• QQ/WX Webhook 接口已预留</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
