'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPost, apiDelete } from '@/lib/api';

type MemoryItem = {
  id: number;
  content: string;
  summary: string | null;
  memory_type: string;
  importance: number;
  tags: string[];
};

type SearchResult = {
  id: number;
  content: string;
  summary: string | null;
  importance: number;
  memory_type: string;
  source: string | null;
  tags: string[];
  score: number;
};

const typeLabels: Record<string, string> = {
  short_term: '短期',
  long_term: '长期',
  episodic: '情景',
  semantic: '语义',
  fact: '事实',
  preference: '偏好',
  opinion: '观点',
  goal: '目标',
  relationship: '关系',
  knowledge: '知识',
  persona: '人格',
};

const PAGE_SIZE = 50;

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);

  const [showAdd, setShowAdd] = useState(false);
  const [addContent, setAddContent] = useState('');
  const [addSummary, setAddSummary] = useState('');
  const [addType, setAddType] = useState('long_term');
  const [addImportance, setAddImportance] = useState(5);
  const [addTags, setAddTags] = useState('');
  const [adding, setAdding] = useState(false);

  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [distilling, setDistilling] = useState(false);
  const [distillResult, setDistillResult] = useState('');

  async function loadMemories(reset = false) {
    const currentSkip = reset ? 0 : skip;
    const setter = reset ? setLoading : setLoadingMore;
    setter(true);
    try {
      const data = await apiGet<{ items: MemoryItem[]; total: number }>(`/memory/?skip=${currentSkip}&limit=${PAGE_SIZE}`);
      setMemories((prev) => reset ? data.items : [...prev, ...data.items]);
      setTotal(data.total);
      setSkip(currentSkip + data.items.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setter(false);
    }
  }

  useEffect(() => { loadMemories(true); }, []);

  async function handleAdd() {
    if (!addContent.trim()) return;
    setAdding(true);
    setError('');
    try {
      await apiPost('/memory/', {
        content: addContent.trim(),
        summary: addSummary.trim() || null,
        memory_type: addType,
        importance: addImportance,
        tags: addTags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      setShowAdd(false);
      setAddContent('');
      setAddSummary('');
      setAddType('long_term');
      setAddImportance(5);
      setAddTags('');
      await loadMemories(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('确定删除此记忆？')) return;
    try {
      await apiDelete(`/memory/${id}`);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  }

  async function handleSearch() {
    const text = query.trim();
    if (!text) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const data = await apiPost<{ results: SearchResult[] }>('/memory/search', { query: text, limit: 10 });
      setSearchResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索失败');
    } finally {
      setSearching(false);
    }
  }

  async function handleDistill() {
    setDistilling(true);
    setDistillResult('');
    setError('');
    try {
      const data = await apiPost<{ status: string; count: number; summary?: string }>('/memory/distill', {});
      setDistillResult(`已蒸馏 ${data.count} 条记忆${data.summary ? '：' + data.summary.slice(0, 100) + '...' : ''}`);
      await loadMemories(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '蒸馏失败');
    } finally {
      setDistilling(false);
    }
  }

  function importanceBar(level: number): string {
    if (level >= 8) return 'bg-red-400';
    if (level >= 6) return 'bg-amber-400';
    if (level >= 4) return 'bg-teal-400';
    return 'bg-slate-300';
  }

  return (
    <div className="page-container">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">记忆管理</h1>
          <p className="page-subtitle">{total} 条记忆，支持语义搜索和蒸馏</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleDistill} disabled={distilling} className="btn-secondary">
            {distilling ? '蒸馏中...' : '蒸馏记忆'}
          </button>
          <button onClick={() => setShowAdd(!showAdd)} className="btn-primary">
            + 新建记忆
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-error mb-4">
          {error}
          <button onClick={() => setError('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      {distillResult && (
        <div className="alert-success mb-4">
          {distillResult}
          <button onClick={() => setDistillResult('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      {showAdd && (
        <div className="panel panel-pad mb-4 animate-fade-in">
          <h3 className="mb-3 text-base font-bold text-slate-900">新建记忆</h3>
          <div className="space-y-3">
            <div>
              <label className="label">内容 *</label>
              <textarea value={addContent} onChange={(e) => setAddContent(e.target.value)} className="field min-h-[100px] resize-y" placeholder="记忆内容..." />
            </div>
            <div>
              <label className="label">摘要</label>
              <input value={addSummary} onChange={(e) => setAddSummary(e.target.value)} className="field" placeholder="简短摘要（可选）" />
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className="label">类型</label>
                <select value={addType} onChange={(e) => setAddType(e.target.value)} className="field">
                  <option value="long_term">长期</option>
                  <option value="short_term">短期</option>
                  <option value="episodic">情景</option>
                  <option value="semantic">语义</option>
                </select>
              </div>
              <div>
                <label className="label">重要性 ({addImportance})</label>
                <input type="range" min={1} max={10} value={addImportance} onChange={(e) => setAddImportance(Number(e.target.value))} className="field" />
              </div>
              <div>
                <label className="label">标签（逗号分隔）</label>
                <input value={addTags} onChange={(e) => setAddTags(e.target.value)} className="field" placeholder="tag1, tag2" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={handleAdd} disabled={adding || !addContent.trim()} className="btn-primary">{adding ? '保存中...' : '保存'}</button>
              <button onClick={() => setShowAdd(false)} className="btn-secondary">取消</button>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div>
          {loading ? (
            <div className="panel panel-pad text-sm text-slate-500">加载中...</div>
          ) : memories.length === 0 ? (
            <div className="panel panel-pad text-center animate-fade-in">
              <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-100 text-2xl">◈</div>
              <p className="text-lg font-semibold text-slate-800">暂无记忆</p>
              <p className="mt-2 text-sm text-slate-500">新建记忆或通过聊天自动生成</p>
            </div>
          ) : (
            <div className="space-y-3">
              {memories.map((mem) => (
                <article key={mem.id} className="panel panel-pad panel-hover animate-fade-in">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-900 line-clamp-2">
                        {mem.summary || mem.content.slice(0, 120)}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="chip-teal">{typeLabels[mem.memory_type] || mem.memory_type}</span>
                        <span className="flex items-center gap-1 text-xs text-slate-400">
                          <span className={`inline-block h-2 w-8 rounded-full ${importanceBar(mem.importance)}`} />
                          {mem.importance}
                        </span>
                        {mem.tags?.map((tag) => <span key={tag} className="chip">{tag}</span>)}
                      </div>
                    </div>
                    <button onClick={() => handleDelete(mem.id)} className="btn-ghost shrink-0 text-xs !text-red-500 hover:!text-red-700">删除</button>
                  </div>
                </article>
              ))}
              {skip < total && (
                <div className="pt-2 text-center">
                  <button onClick={() => loadMemories()} disabled={loadingMore} className="btn-secondary">
                    {loadingMore ? '加载中...' : `加载更多（已加载 ${memories.length}/${total}）`}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <aside>
          <div className="panel panel-pad sticky top-6">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">语义搜索</h2>
            <div className="flex gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="field flex-1"
                placeholder="搜索记忆..."
              />
              <button onClick={handleSearch} disabled={searching} className="btn-primary px-4">
                {searching ? '...' : '搜索'}
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="mt-4 space-y-2">
                {searchResults.map((r) => (
                  <div key={r.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="chip-teal">{typeLabels[r.memory_type] || r.memory_type}</span>
                      <span className="shrink-0 chip-teal">{r.score.toFixed(3)}</span>
                    </div>
                    <p className="mt-1 line-clamp-4 text-xs leading-4 text-slate-500">
                      {r.summary || r.content.slice(0, 200)}
                    </p>
                  </div>
                ))}
              </div>
            )}
            {searchResults.length === 0 && query && !searching && (
              <p className="mt-3 text-xs text-slate-400">未找到匹配记忆</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
