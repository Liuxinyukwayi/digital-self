'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiPost, apiDelete } from '@/lib/api';

type TimelineEvent = {
  id: number | string;
  source_type?: string;
  title: string;
  description: string | null;
  date: string | null;
  type: string;
  importance: number;
  tags: string[];
};

const PAGE_SIZE = 50;

function formatDate(iso: string | null): string {
  if (!iso) return '未知日期';
  try {
    const d = new Date(iso);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return iso;
  }
}

function importanceColor(level: number): string {
  if (level >= 8) return 'bg-red-500';
  if (level >= 6) return 'bg-amber-400';
  if (level >= 4) return 'bg-teal-500';
  return 'bg-slate-400';
}

const typeLabels: Record<string, string> = {
  manual: '手动',
  work: '工作',
  study: '学习',
  life: '生活',
  milestone: '里程碑',
  wechat: '微信',
  qq: 'QQ',
  feishu: '飞书',
  github: 'GitHub',
  email: '邮件',
};

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);

  const [showAdd, setShowAdd] = useState(false);
  const [addTitle, setAddTitle] = useState('');
  const [addDesc, setAddDesc] = useState('');
  const [addDate, setAddDate] = useState('');
  const [addType, setAddType] = useState('manual');
  const [addImportance, setAddImportance] = useState(5);
  const [adding, setAdding] = useState(false);

  async function loadEvents(reset = false) {
    const currentSkip = reset ? 0 : skip;
    const setter = reset ? setLoading : setLoadingMore;
    setter(true);
    try {
      const data = await apiGet<{ items: TimelineEvent[]; total: number }>(`/timeline/?skip=${currentSkip}&limit=${PAGE_SIZE}`);
      setEvents((prev) => reset ? data.items : [...prev, ...data.items]);
      setTotal(data.total);
      setSkip(currentSkip + data.items.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setter(false);
    }
  }

  useEffect(() => { loadEvents(true); }, []);

  async function handleDelete(eventId: string | number) {
    if (!confirm('确定删除此事件？')) return;
    try {
      await apiDelete(`/timeline/${eventId}`);
      setEvents((prev) => prev.filter((e) => String(e.id) !== String(eventId)));
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  }

  async function handleAdd() {
    if (!addTitle.trim()) return;
    setAdding(true);
    setError('');
    try {
      await apiPost('/timeline/', {
        title: addTitle.trim(),
        description: addDesc.trim() || null,
        event_date: addDate ? new Date(addDate).toISOString() : null,
        event_type: addType,
        importance: addImportance,
      });
      setShowAdd(false);
      setAddTitle('');
      setAddDesc('');
      setAddDate('');
      setAddType('manual');
      setAddImportance(5);
      await loadEvents(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="page-container">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">时间线</h1>
          <p className="page-subtitle">{total} 个事件</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="btn-primary">
          + 添加事件
        </button>
      </div>

      {error && (
        <div className="alert-error mb-4">
          {error}
          <button onClick={() => setError('')} className="ml-3 font-semibold underline">关闭</button>
        </div>
      )}

      {showAdd && (
        <div className="panel panel-pad mb-6 animate-fade-in">
          <h3 className="mb-3 text-base font-bold text-slate-900">新增事件</h3>
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label">标题 *</label>
                <input value={addTitle} onChange={(e) => setAddTitle(e.target.value)} className="field" placeholder="事件标题" />
              </div>
              <div>
                <label className="label">日期</label>
                <input type="date" value={addDate} onChange={(e) => setAddDate(e.target.value)} className="field" />
              </div>
            </div>
            <div>
              <label className="label">描述</label>
              <textarea value={addDesc} onChange={(e) => setAddDesc(e.target.value)} className="field min-h-[80px] resize-y" placeholder="事件描述..." />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label">类型</label>
                <select value={addType} onChange={(e) => setAddType(e.target.value)} className="field">
                  <option value="manual">手动记录</option>
                  <option value="work">工作</option>
                  <option value="study">学习</option>
                  <option value="life">生活</option>
                  <option value="milestone">里程碑</option>
                </select>
              </div>
              <div>
                <label className="label">重要性 ({addImportance})</label>
                <input type="range" min={1} max={10} value={addImportance} onChange={(e) => setAddImportance(Number(e.target.value))} className="field" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={handleAdd} disabled={adding || !addTitle.trim()} className="btn-primary">{adding ? '保存中...' : '保存'}</button>
              <button onClick={() => setShowAdd(false)} className="btn-secondary">取消</button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="panel panel-pad text-sm text-slate-500">加载中...</div>
      ) : events.length === 0 ? (
        <div className="panel panel-pad text-center animate-fade-in">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-2xl">◈</div>
          <p className="text-lg font-semibold text-slate-800">暂无事件</p>
          <p className="mt-2 text-sm text-slate-500">添加事件或导入聊天记录后自动生成</p>
        </div>
      ) : (
        <div className="relative">
          <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-gradient-to-b from-teal-200 via-slate-200 to-slate-100" />
          <div className="space-y-4">
            {events.map((event) => (
              <div key={event.id} className="relative flex gap-5 pl-12 animate-fade-in">
                <div className={`absolute left-3 top-4 h-3.5 w-3.5 rounded-full border-2 border-white shadow ${importanceColor(event.importance)}`} />
                <article className="panel panel-pad min-w-0 flex-1 panel-hover">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-base font-bold text-slate-900">{event.title}</h3>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs font-medium text-slate-400">{formatDate(event.date)}</span>
                      <button onClick={() => handleDelete(event.id)} className="btn-ghost text-xs !text-red-500 hover:!text-red-700">删除</button>
                    </div>
                  </div>
                  {event.description && (
                    <p className="mt-2 text-sm leading-6 text-slate-600">{event.description}</p>
                  )}
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className="chip">{typeLabels[event.type] || event.type}</span>
                    <span className="text-xs text-slate-400">重要性 {event.importance}</span>
                    {event.tags?.map((tag) => <span key={tag} className="chip">{tag}</span>)}
                  </div>
                </article>
              </div>
            ))}
            {skip < total && (
              <div className="relative pl-12 pt-2 animate-fade-in">
                <button onClick={() => loadEvents()} disabled={loadingMore} className="btn-secondary">
                  {loadingMore ? '加载中...' : `加载更多（已加载 ${events.length}/${total}）`}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
