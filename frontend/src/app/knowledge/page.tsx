'use client';

import { useEffect, useRef, useState } from 'react';
import { apiGet, apiPost, apiDelete } from '@/lib/api';

type KnowledgeItem = {
  id: number;
  title: string;
  content: string | null;
  content_type: string | null;
  category: string | null;
  tags: string[];
};

type SearchResult = {
  id: number;
  knowledge_id: number;
  title: string;
  content: string;
  score: number;
  chunk_index: number;
};

const PAGE_SIZE = 50;

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);

  const [showAdd, setShowAdd] = useState(false);
  const [addTitle, setAddTitle] = useState('');
  const [addContent, setAddContent] = useState('');
  const [addCategory, setAddCategory] = useState('');
  const [addTags, setAddTags] = useState('');
  const [adding, setAdding] = useState(false);

  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function loadItems(reset = false) {
    const currentSkip = reset ? 0 : skip;
    const setter = reset ? setLoading : setLoadingMore;
    setter(true);
    try {
      const data = await apiGet<{ items: KnowledgeItem[]; total: number }>(`/knowledge/?skip=${currentSkip}&limit=${PAGE_SIZE}`);
      setItems((prev) => reset ? data.items : [...prev, ...data.items]);
      setTotal(data.total);
      setSkip(currentSkip + data.items.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setter(false);
    }
  }

  useEffect(() => {
    loadItems(true);
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      await apiPost('/knowledge/upload', formData);
      await loadItems(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function handleAdd() {
    if (!addTitle.trim()) return;
    setAdding(true);
    setError('');
    try {
      await apiPost('/knowledge/', {
        title: addTitle.trim(),
        content: addContent.trim() || null,
        category: addCategory.trim() || null,
        tags: addTags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      setShowAdd(false);
      setAddTitle('');
      setAddContent('');
      setAddCategory('');
      setAddTags('');
      await loadItems(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('确定删除？')) return;
    try {
      await apiDelete(`/knowledge/${id}`);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  }

  async function handleSearch() {
    const text = query.trim();
    if (!text) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const data = await apiPost<{ results: SearchResult[] }>('/knowledge/search', { query: text, limit: 10 });
      setSearchResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索失败');
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="page-container">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">知识库</h1>
          <p className="page-subtitle">{total} 篇文档，支持语义搜索和 RAG 检索</p>
        </div>
        <div className="flex gap-2">
          <label className="btn-secondary cursor-pointer">
            {uploading ? '上传中...' : '上传文件'}
            <input
              ref={fileRef}
              type="file"
              className="hidden"
              accept=".txt,.md,.json,.csv"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
          <button onClick={() => setShowAdd(!showAdd)} className="btn-primary">
            + 手动录入
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-error mb-4">
          {error}
          <button onClick={() => setError('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      {showAdd && (
        <div className="panel panel-pad mb-4 animate-fade-in">
          <h3 className="mb-3 text-base font-bold text-slate-900">新增知识条目</h3>
          <div className="space-y-3">
            <div>
              <label className="label">标题 *</label>
              <input value={addTitle} onChange={(e) => setAddTitle(e.target.value)} className="field" placeholder="文章标题" />
            </div>
            <div>
              <label className="label">内容</label>
              <textarea value={addContent} onChange={(e) => setAddContent(e.target.value)} className="field min-h-[120px] resize-y" placeholder="正文内容..." />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label">分类</label>
                <input value={addCategory} onChange={(e) => setAddCategory(e.target.value)} className="field" placeholder="例如：技术、生活" />
              </div>
              <div>
                <label className="label">标签（逗号分隔）</label>
                <input value={addTags} onChange={(e) => setAddTags(e.target.value)} className="field" placeholder="tag1, tag2" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={handleAdd} disabled={adding || !addTitle.trim()} className="btn-primary">{adding ? '保存中...' : '保存'}</button>
              <button onClick={() => setShowAdd(false)} className="btn-secondary">取消</button>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div>
          {loading ? (
            <div className="panel panel-pad text-sm text-slate-500">加载中...</div>
          ) : items.length === 0 ? (
            <div className="panel panel-pad text-center animate-fade-in">
              <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100 text-2xl">▤</div>
              <p className="text-lg font-semibold text-slate-800">暂无知识条目</p>
              <p className="mt-2 text-sm text-slate-500">上传文章、笔记或手动录入来构建知识库</p>
            </div>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <article key={item.id} className="panel panel-pad panel-hover animate-fade-in">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-base font-bold text-slate-900">{item.title}</h3>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2">
                        {item.category && <span className="chip-teal">{item.category}</span>}
                        {item.tags?.map((tag) => <span key={tag} className="chip">{tag}</span>)}
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button onClick={() => setExpandedId(expandedId === item.id ? null : item.id)} className="btn-ghost text-xs">
                        {expandedId === item.id ? '收起' : '展开'}
                      </button>
                      <button onClick={() => handleDelete(item.id)} className="btn-ghost text-xs !text-red-500 hover:!text-red-700">删除</button>
                    </div>
                  </div>
                  {expandedId === item.id && item.content && (
                    <p className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-700 animate-fade-in">
                      {item.content}
                    </p>
                  )}
                </article>
              ))}
              {skip < total && (
                <div className="pt-2 text-center">
                  <button onClick={() => loadItems()} disabled={loadingMore} className="btn-secondary">
                    {loadingMore ? '加载中...' : `加载更多（已加载 ${items.length}/${total}）`}
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
                placeholder="搜索知识库..."
              />
              <button onClick={handleSearch} disabled={searching} className="btn-primary px-4">
                {searching ? '...' : '搜索'}
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="mt-4 space-y-2">
                {searchResults.map((r) => (
                  <div key={`${r.knowledge_id}-${r.chunk_index}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="line-clamp-1 text-xs font-semibold text-slate-800">{r.title}</h3>
                      <span className="shrink-0 chip-teal">{r.score.toFixed(3)}</span>
                    </div>
                    <p className="mt-1 line-clamp-4 text-xs leading-4 text-slate-500">{r.content}</p>
                  </div>
                ))}
              </div>
            )}
            {searchResults.length === 0 && query && !searching && (
              <p className="mt-3 text-xs text-slate-400">未找到匹配内容</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
