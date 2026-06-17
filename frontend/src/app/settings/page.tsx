'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import Link from 'next/link';

type SettingsData = {
  app_name: string;
  app_version: string;
  active_provider: string;
  mimo_model: string;
  mimo_configured: boolean;
  mimo_key_masked: string;
  deepseek_model: string;
  deepseek_configured: boolean;
  deepseek_key_masked: string;
  openai_model: string;
  openai_configured: boolean;
  openai_key_masked: string;
  custom_model: string;
  custom_api_base: string;
  custom_configured: boolean;
  custom_key_masked: string;
  qdrant_enabled: boolean;
  lightrag_enabled: boolean;
  embedding_mode: string;
  ollama_base_url: string;
  short_term_memory_limit: number;
  memory_importance_threshold: number;
  distill_schedule: string;
};

const PROVIDER_OPTIONS = [
  { id: 'mimo', name: 'MiMo', color: 'bg-teal-500' },
  { id: 'deepseek', name: 'DeepSeek', color: 'bg-blue-500' },
  { id: 'openai', name: 'ChatGPT', color: 'bg-green-600' },
  { id: 'custom', name: '自定义', color: 'bg-purple-500' },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const [activeProvider, setActiveProvider] = useState('mimo');
  const [apiKey, setApiKey] = useState('');
  const [customApiBase, setCustomApiBase] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [embeddingMode, setEmbeddingMode] = useState('lite');
  const [ollamaStatus, setOllamaStatus] = useState<{ status: string; message: string } | null>(null);
  const [checkingOllama, setCheckingOllama] = useState(false);
  const [shortLimit, setShortLimit] = useState(20);
  const [importanceThreshold, setImportanceThreshold] = useState(5);
  const [distillSchedule, setDistillSchedule] = useState('weekly');

  async function loadSettings() {
    try {
      const data = await apiGet<SettingsData>('/settings/');
      setSettings(data);
      setActiveProvider(data.active_provider);
      setEmbeddingMode(data.embedding_mode || 'lite');
      setShortLimit(data.short_term_memory_limit);
      setImportanceThreshold(data.memory_importance_threshold);
      setDistillSchedule(data.distill_schedule);
      setCustomApiBase(data.custom_api_base || '');
      setCustomModel(data.custom_model || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    }
  }

  useEffect(() => {
    loadSettings().finally(() => setLoading(false));
  }, []);

  function getConfig(providerId: string) {
    if (!settings) return { configured: false, model: '', masked: '' };
    switch (providerId) {
      case 'mimo': return { configured: settings.mimo_configured, model: settings.mimo_model, masked: settings.mimo_key_masked };
      case 'deepseek': return { configured: settings.deepseek_configured, model: settings.deepseek_model, masked: settings.deepseek_key_masked };
      case 'openai': return { configured: settings.openai_configured, model: settings.openai_model, masked: settings.openai_key_masked };
      case 'custom': return { configured: settings.custom_configured, model: settings.custom_model || customModel, masked: settings.custom_key_masked };
      default: return { configured: false, model: '', masked: '' };
    }
  }

  const currentOption = PROVIDER_OPTIONS.find(p => p.id === activeProvider) || PROVIDER_OPTIONS[0];
  const currentConfig = getConfig(activeProvider);
  const keyPlaceholder = currentConfig.masked || '请输入 API Key';
  const keyHasValue = apiKey.length > 0;
  const isCustom = activeProvider === 'custom';

  function handleProviderChange(providerId: string) {
    setActiveProvider(providerId);
    setApiKey('');
  }

  async function handleSave() {
    setError('');
    try {
      const payload: Record<string, unknown> = {
        active_provider: activeProvider,
        embedding_mode: embeddingMode,
        short_term_memory_limit: shortLimit,
        memory_importance_threshold: importanceThreshold,
        distill_schedule: distillSchedule,
      };
      if (apiKey.trim()) {
        payload[`${activeProvider}_api_key`] = apiKey.trim();
      }
      if (isCustom) {
        if (customApiBase.trim()) payload['custom_api_base'] = customApiBase.trim();
        if (customModel.trim()) payload['custom_model'] = customModel.trim();
      }
      await apiPost('/settings/', payload);
      setSaved(true);
      setApiKey('');
      await loadSettings();
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    }
  }

  async function handleDistill() {
    setError('');
    try {
      const data = await apiPost<{ status: string; count: number }>('/memory/distill');
      alert(`蒸馏完成，处理了 ${data.count} 条记忆`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '蒸馏失败');
    }
  }

  async function handleCheckOllama() {
    setCheckingOllama(true);
    setOllamaStatus(null);
    try {
      const data = await apiPost<{ status: string; ollama_found: boolean; model_found: boolean; model_pulled: boolean; error: string | null }>('/settings/check-ollama');
      if (data.status === 'ready') {
        setOllamaStatus({ status: 'ready', message: 'Ollama + bge-m3 就绪' });
      } else {
        setOllamaStatus({ status: 'error', message: data.error || 'Ollama 不可用' });
      }
    } catch (err) {
      setOllamaStatus({ status: 'error', message: err instanceof Error ? err.message : '检查失败' });
    } finally {
      setCheckingOllama(false);
    }
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="panel panel-pad text-sm text-slate-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">系统设置</h1>
        <p className="page-subtitle">配置模型、检索和蒸馏参数</p>
      </div>

      {error && (
        <div className="alert-error mb-4">
          {error}
          <button onClick={() => setError('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      {saved && (
        <div className="alert-success mb-4">
          设置已保存
          <button onClick={() => setSaved(false)} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">

          <div className="panel panel-pad">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">模型提供商</h2>
            <div className="space-y-4">
              <div>
                <label className="label">当前模型</label>
                <select
                  value={activeProvider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="field"
                >
                  {PROVIDER_OPTIONS.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className={`h-3 w-3 rounded-full ${currentOption.color}`} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-bold text-slate-900">{currentOption.name}</span>
                  <span className="ml-2 text-xs text-slate-500">{currentConfig.model}</span>
                </div>
                {currentConfig.configured ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-mono text-slate-500">{currentConfig.masked}</span>
                    <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs font-medium text-teal-700">已配置</span>
                  </div>
                ) : (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-600">未配置</span>
                )}
              </div>
            </div>
          </div>

          <div className="panel panel-pad">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                {currentOption.name} API 密钥
              </h2>
              {currentConfig.configured && !keyHasValue && (
                <span className="chip-teal">已配置</span>
              )}
              {keyHasValue && (
                <span className="chip" style={{ background: '#fef3c7', color: '#92400e' }}>待保存</span>
              )}
            </div>
            <div className="space-y-3">
              {isCustom && (
                <>
                  <div>
                    <label className="label">API Base URL</label>
                    <input
                      value={customApiBase}
                      onChange={(e) => setCustomApiBase(e.target.value)}
                      className="field"
                      placeholder="https://api.example.com/v1"
                    />
                    <p className="mt-1 text-xs text-slate-400">兼容 OpenAI 格式的 API 地址</p>
                  </div>
                  <div>
                    <label className="label">模型名称</label>
                    <input
                      value={customModel}
                      onChange={(e) => setCustomModel(e.target.value)}
                      className="field"
                      placeholder="gpt-4o / deepseek-chat / ..."
                    />
                  </div>
                </>
              )}
              <div>
                <label className="label">API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={keyPlaceholder}
                  className="field"
                />
                <p className="mt-1 text-xs text-slate-400">
                  {currentConfig.configured
                    ? keyHasValue
                      ? '将更新为新的 API Key'
                      : '留空则保持当前配置不变'
                    : '请输入 API Key'}
                </p>
              </div>
              <button onClick={handleSave} className="btn-primary">
                保存设置
              </button>
            </div>
          </div>

          <div className="panel panel-pad">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">记忆配置</h2>
            <div className="space-y-4">
              <div>
                <label className="label">短期记忆轮数</label>
                <input type="number" value={shortLimit} onChange={(e) => setShortLimit(Number(e.target.value))} className="field" min={1} max={100} />
                <p className="mt-1 text-xs text-slate-400">对话时携带的历史消息轮数</p>
              </div>
              <div>
                <label className="label">记忆重要性阈值: {importanceThreshold}</label>
                <input type="range" min={1} max={10} value={importanceThreshold} onChange={(e) => setImportanceThreshold(Number(e.target.value))} className="field" />
                <p className="mt-1 text-xs text-slate-400">低于此阈值的记忆在检索时权重较低</p>
              </div>
            </div>
          </div>

          <div className="panel panel-pad">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">蒸馏配置</h2>
            <div className="space-y-4">
              <div>
                <label className="label">蒸馏频率</label>
                <select value={distillSchedule} onChange={(e) => setDistillSchedule(e.target.value)} className="field">
                  <option value="daily">每天</option>
                  <option value="weekly">每周</option>
                  <option value="monthly">每月</option>
                </select>
              </div>
              <button onClick={handleDistill} className="btn-secondary">立即蒸馏</button>
            </div>
          </div>

          <div className="panel panel-pad">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">检索模式</h2>
            <div className="space-y-4">
              <div>
                <label className="label">语义检索引擎</label>
                <select
                  value={embeddingMode}
                  onChange={(e) => setEmbeddingMode(e.target.value)}
                  className="field"
                >
                  <option value="lite">Lite — TF-IDF（无需额外依赖）</option>
                  <option value="full">Full — Ollama + bge-m3（向量检索）</option>
                </select>
                <p className="mt-1 text-xs text-slate-400">
                  {embeddingMode === 'lite'
                    ? '使用 TF-IDF 文本检索，开箱即用，无需安装额外软件'
                    : '使用 Ollama 本地运行 bge-m3 模型进行语义向量检索，需安装 Ollama'}
                </p>
              </div>
              {embeddingMode === 'full' && (
                <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4 animate-fade-in">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-slate-900">Ollama 状态</span>
                    {ollamaStatus?.status === 'ready' && (
                      <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs font-medium text-teal-700">{ollamaStatus.message}</span>
                    )}
                    {ollamaStatus?.status === 'error' && (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-600">{ollamaStatus.message}</span>
                    )}
                  </div>
                  <button onClick={handleCheckOllama} disabled={checkingOllama} className="btn-secondary w-full">
                    {checkingOllama ? '检查中...' : '检查 Ollama 并下载模型'}
                  </button>
                  <p className="text-xs text-slate-400">首次使用将自动下载 bge-m3 模型（约 2GB）</p>
                </div>
              )}
            </div>
          </div>

          <div className="panel panel-pad">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">系统状态</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <StatusCard label="应用" value={settings?.app_name || ''} />
              <StatusCard label="版本" value={settings?.app_version || ''} />
              <StatusCard label="检索模式" value={embeddingMode === 'full' ? 'Full (向量)' : 'Lite (TF-IDF)'} />
              <StatusCard label="Qdrant" value={settings?.qdrant_enabled ? '已启用' : '未启用'} ok={embeddingMode === 'full' ? settings?.qdrant_enabled : false} />
              <StatusCard label="LightRAG" value={settings?.lightrag_enabled ? '已启用' : '未启用'} ok={settings?.lightrag_enabled} />
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="panel panel-pad">
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">关于</h2>
            <p className="text-sm leading-6 text-slate-600">
              Digital Self 是基于 LightRAG 知识图谱和分层记忆架构的数字分身系统。
            </p>
            <p className="mt-2 text-xs text-slate-400">
              FastAPI + Next.js + SQLite + LightRAG + Qdrant
            </p>
          </div>

          <div className="panel panel-pad">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">快捷操作</h2>
            <div className="space-y-2">
              <Link href="/chat" className="btn-secondary block w-full text-center">进入聊天</Link>
              <Link href="/knowledge" className="btn-secondary block w-full text-center">管理知识库</Link>
              <Link href="/sync" className="btn-secondary block w-full text-center">导入数据</Link>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function StatusCard({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="text-xs font-semibold text-slate-400">{label}</div>
      <div className={`mt-1 text-sm font-bold ${ok === false ? 'text-slate-400' : ok === true ? 'text-teal-700' : 'text-slate-900'}`}>
        {value}
      </div>
    </div>
  );
}
