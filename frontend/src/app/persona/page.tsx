'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPost } from '@/lib/api';

type Trait = { name: string; description: string; weight: number };
type Style = { speaking_style: string[]; interests: string[]; values: string[] };
type PersonaData = { name: string; traits: Trait[]; style: Style; summary: string };

export default function PersonaPage() {
  const [persona, setPersona] = useState<PersonaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function loadPersona() {
    try {
      const data = await apiGet<PersonaData>('/persona/');
      setPersona(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadPersona(); }, []);

  async function handleGenerate() {
    setGenerating(true);
    setError('');
    setMessage('');
    try {
      const data = await apiPost<{ status: string; persona?: PersonaData; message?: string }>('/persona/generate');
      if (data.status === 'no_data') {
        setMessage(data.message || '没有足够的聊天记录');
      } else if (data.persona) {
        setPersona(data.persona);
        setMessage('Persona 已生成');
      } else {
        setMessage('生成完成，请刷新查看');
        await loadPersona();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成失败');
    } finally {
      setGenerating(false);
    }
  }

  const hasTraits = persona && persona.traits.length > 0;

  return (
    <div className="page-container">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">Persona</h1>
          <p className="page-subtitle">基于聊天记录和长期记忆的人格画像</p>
        </div>
        {hasTraits && (
          <button onClick={handleGenerate} disabled={generating} className="btn-secondary">
            {generating ? '重新生成中...' : '重新生成'}
          </button>
        )}
      </div>

      {error && (
        <div className="alert-error mb-4">
          {error}
          <button onClick={() => setError('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}
      {message && (
        <div className="alert-success mb-4">
          {message}
          <button onClick={() => setMessage('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      {loading ? (
        <div className="panel panel-pad text-sm text-slate-500">加载中...</div>
      ) : !hasTraits ? (
        <div className="panel panel-pad text-center animate-fade-in">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-100 text-2xl">◉</div>
          <p className="text-xl font-bold text-slate-900">尚未生成 Persona</p>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            导入聊天记录后，系统会分析你的性格、说话风格、兴趣和价值观。
          </p>
          <button onClick={handleGenerate} disabled={generating} className="btn-primary mt-6">
            {generating ? '生成中...' : '生成 Persona'}
          </button>
        </div>
      ) : (
        <div className="space-y-5 animate-fade-in">
          {/* Summary card */}
          <div className="panel panel-pad">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-100 text-2xl font-black text-teal-700">
                {persona!.name.charAt(0)}
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">{persona!.name}</h2>
                <p className="mt-1 text-sm text-slate-500">{persona!.summary}</p>
              </div>
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            {/* Traits */}
            <div className="panel panel-pad">
              <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">性格特征</h3>
              <div className="flex flex-wrap gap-2">
                {persona!.traits.map((trait) => (
                  <span key={trait.name} className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-1.5 text-sm font-medium text-teal-800">
                    {trait.name}
                  </span>
                ))}
              </div>
            </div>

            {/* Speaking style */}
            <div className="panel panel-pad">
              <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">说话风格</h3>
              {persona!.style.speaking_style.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {persona!.style.speaking_style.map((s) => (
                    <span key={s} className="chip">{s}</span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">暂无数据</p>
              )}
            </div>

            {/* Interests */}
            <div className="panel panel-pad">
              <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">兴趣爱好</h3>
              {persona!.style.interests.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {persona!.style.interests.map((i) => (
                    <span key={i} className="chip-green">{i}</span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">暂无数据</p>
              )}
            </div>

            {/* Values */}
            <div className="panel panel-pad">
              <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">价值观</h3>
              {persona!.style.values.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {persona!.style.values.map((v) => (
                    <span key={v} className="chip-purple">{v}</span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">暂无数据</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
