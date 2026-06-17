'use client';

import { useEffect, useRef, useState } from 'react';
import { apiGet, apiPost, apiDelete } from '@/lib/api';

type Message = {
  role: 'user' | 'assistant';
  content: string;
};

type Conversation = {
  id: number;
  title: string;
  created_at: string;
};

type ChatResponse = {
  reply: string;
  conversation_id: number;
  memories_used: string[];
  knowledge_used: string[];
};

type RagContext = {
  memories: Array<{ id: number; summary?: string; content: string; score?: number; importance?: number }>;
  knowledge: Array<{ id: number; title: string; content: string; score?: number }>;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [context, setContext] = useState<RagContext>({ memories: [], knowledge: [] });
  const [error, setError] = useState('');
  const [showSidebar, setShowSidebar] = useState(true);
  const [loadingConvs, setLoadingConvs] = useState<Set<number>>(new Set());
  const [unreadConvs, setUnreadConvs] = useState<Set<number>>(new Set());
  const endRef = useRef<HTMLDivElement>(null);
  const currentConvRef = useRef<number | null>(null);
  const pendingRepliesRef = useRef<Map<number, { reply: string }>>(new Map());

  const loading = conversationId !== null && loadingConvs.has(conversationId);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loadingConvs]);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    currentConvRef.current = conversationId;
  }, [conversationId]);

  async function loadConversations() {
    try {
      const data = await apiGet<{ conversations: Conversation[] }>('/chat/conversations');
      setConversations(data.conversations);
    } catch {}
  }

  async function loadConversation(id: number) {
    setConversationId(id);
    setContext({ memories: [], knowledge: [] });
    setError('');
    setUnreadConvs((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    pendingRepliesRef.current.delete(id);

    try {
      const data = await apiGet<{ messages: Message[]; conversation_id: number }>(`/chat/conversations/${id}`);
      if (currentConvRef.current === id) {
        setMessages(data.messages);
      }
    } catch (err) {
      if (currentConvRef.current === id) {
        setError(err instanceof Error ? err.message : '加载会话失败');
      }
    }
  }

  function newConversation() {
    setMessages([]);
    setConversationId(null);
    setContext({ memories: [], knowledge: [] });
    setInput('');
    setError('');
  }

  async function deleteConversation(id: number) {
    if (!confirm('确定删除此会话？')) return;

    try {
      await apiDelete(`/chat/conversations/${id}`);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      setLoadingConvs((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      setUnreadConvs((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      if (conversationId === id) {
        newConversation();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;

    const targetId = conversationId;

    setInput('');
    setError('');
    setLoadingConvs((prev) => new Set(prev).add(targetId!));
    setMessages((prev) => [...prev, { role: 'user', content: text }]);

    try {
      const [chat, rag] = await Promise.all([
        apiPost<ChatResponse>('/chat/', { message: text, conversation_id: targetId }),
        apiPost<RagContext>('/chat/rag/search', { message: text }),
      ]);

      const resolvedId = chat.conversation_id ?? targetId;
      setLoadingConvs((prev) => {
        const next = new Set(prev);
        next.delete(resolvedId);
        return next;
      });

      if (currentConvRef.current === targetId) {
        setConversationId(resolvedId);
        setMessages((prev) => [...prev, { role: 'assistant', content: chat.reply }]);
        setContext(rag);
      } else {
        pendingRepliesRef.current.set(resolvedId, { reply: chat.reply });
        setUnreadConvs((prev) => new Set(prev).add(resolvedId));
      }
      loadConversations();
    } catch (err) {
      const msg = err instanceof Error ? err.message : '发送失败';
      setLoadingConvs((prev) => {
        const next = new Set(prev);
        next.delete(targetId!);
        return next;
      });
      if (currentConvRef.current === targetId) {
        setError(msg);
        setMessages((prev) => [...prev, { role: 'assistant', content: `[错误] ${msg}` }]);
      }
    }
  }

  return (
    <div className="flex h-screen">
      {/* Conversation list */}
      <div className="hidden w-64 flex-col border-r border-slate-200 bg-white lg:flex">
        <div className="border-b border-slate-200 p-4">
          <button onClick={newConversation} className="btn-primary w-full">
            + 新会话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.length === 0 ? (
            <p className="p-3 text-center text-xs text-slate-400">暂无会话</p>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === conversationId;
              const isLoading = loadingConvs.has(conv.id);
              const isUnread = unreadConvs.has(conv.id);
              return (
                <div
                  key={conv.id}
                  className={`group mb-1 flex w-full items-center rounded-lg text-sm transition-all ${
                    isActive
                      ? 'bg-teal-50 font-medium text-teal-700'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <button
                    onClick={() => loadConversation(conv.id)}
                    className="flex min-w-0 flex-1 items-center px-3 py-2.5 text-left"
                  >
                    <div className="truncate flex-1">{conv.title || `会话 #${conv.id}`}</div>
                    <div className="ml-2 flex shrink-0 items-center gap-1.5">
                      {isLoading && (
                        <div className="flex items-center gap-0.5">
                          <div className="h-1.5 w-1.5 rounded-full bg-teal-500 animate-pulse" />
                          <div className="h-1.5 w-1.5 rounded-full bg-teal-500 animate-pulse [animation-delay:0.2s]" />
                          <div className="h-1.5 w-1.5 rounded-full bg-teal-500 animate-pulse [animation-delay:0.4s]" />
                        </div>
                      )}
                      {isUnread && !isLoading && (
                        <div className="h-2 w-2 rounded-full bg-blue-500" />
                      )}
                    </div>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteConversation(conv.id);
                    }}
                    className="mr-1.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-slate-400 opacity-0 transition-all hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                    title="删除会话"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
          <div>
            <h1 className="text-lg font-bold text-slate-900">
              {conversationId ? `会话 #${conversationId}` : '新会话'}
            </h1>
            <p className="text-xs text-slate-500">
              回答基于 RAG 检索的记忆和知识库
            </p>
          </div>
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className="btn-ghost text-xs"
          >
            {showSidebar ? '隐藏来源' : '显示来源'}
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto bg-slate-50/50 px-5 py-6">
          {messages.length === 0 ? (
            <div className="mx-auto mt-20 max-w-md text-center animate-fade-in">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-100 text-2xl">
                ✦
              </div>
              <h2 className="text-xl font-bold text-slate-900">问一个和你有关的问题</h2>
              <p className="mt-3 text-sm leading-6 text-slate-500">
                数字分身会检索你的记忆和知识库来回答。
                导入越多数据，回答越精准。
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {['我最近在关注什么？', '总结一下我的技术栈', '我有什么重要事件？'].map((q) => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 transition hover:border-teal-300 hover:text-teal-700"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((message, i) => (
                <MessageBubble key={i} message={message} />
              ))}
              {loading && <TypingIndicator />}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-slate-200 bg-white p-4">
          {error && (
            <div className="alert-error mb-3">
              {error}
              <button onClick={() => setError('')} className="ml-2 font-semibold underline">
                关闭
              </button>
            </div>
          )}
          <div className="mx-auto flex max-w-3xl gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
              className="field min-h-[48px] max-h-[160px] flex-1 resize-none"
              disabled={loading}
              rows={1}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="btn-primary px-6"
            >
              {loading ? '...' : '发送'}
            </button>
          </div>
        </div>
      </div>

      {/* RAG context sidebar */}
      {showSidebar && (
        <div className="hidden w-80 flex-col border-l border-slate-200 bg-white xl:flex">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-bold text-slate-900">检索来源</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <SourceSection
              title="相关记忆"
              count={context.memories.length}
              empty="暂无命中记忆"
              items={context.memories.map((m) => ({
                key: String(m.id),
                title: m.summary || `记忆 #${m.id}`,
                text: m.content,
                score: m.score,
                badge: m.importance ? `重要度 ${m.importance}` : undefined,
              }))}
            />
            <div className="my-4 border-t border-slate-100" />
            <SourceSection
              title="知识片段"
              count={context.knowledge.length}
              empty="暂无命中知识"
              items={context.knowledge.map((k) => ({
                key: `${k.id}-${k.score}`,
                title: k.title,
                text: k.content,
                score: k.score,
              }))}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      {!isUser && (
        <div className="mr-2 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-teal-100 text-xs font-bold text-teal-700">
          DS
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? 'msg-user' : 'msg-assistant'}`}>
        <FormattedContent content={message.content} />
      </div>
    </div>
  );
}

function FormattedContent({ content }: { content: string }) {
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const code = part.slice(3, -3).replace(/^[a-z]*\n/, '');
          return (
            <pre key={i} className="my-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
              <code>{code}</code>
            </pre>
          );
        }
        return <span key={i} className="whitespace-pre-wrap">{renderInlineMarkdown(part)}</span>;
      })}
    </>
  );
}

function renderInlineMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  return lines.map((line, i) => {
    let processed: React.ReactNode = line;

    if (line.startsWith('## ')) {
      return <h3 key={i} className="mt-3 mb-1 text-base font-bold text-slate-900">{line.slice(3)}</h3>;
    }
    if (line.startsWith('### ')) {
      return <h4 key={i} className="mt-2 mb-1 text-sm font-bold text-slate-900">{line.slice(4)}</h4>;
    }
    if (line.match(/^\d+\.\s/)) {
      return <div key={i} className="ml-4">{line}</div>;
    }
    if (line.startsWith('- ') || line.startsWith('* ')) {
      return <div key={i} className="ml-4">{'  • ' + line.slice(2)}</div>;
    }

    const boldParts = line.split(/\*\*(.*?)\*\*/g);
    if (boldParts.length > 1) {
      processed = boldParts.map((part, j) =>
        j % 2 === 1 ? <strong key={j}>{part}</strong> : part
      );
    }

    return <span key={i}>{processed}{i < lines.length - 1 ? '\n' : ''}</span>;
  });
}

function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="mr-2 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-teal-100 text-xs font-bold text-teal-700">
        DS
      </div>
      <div className="msg-assistant flex items-center gap-1.5 px-5">
        <div className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
        <div className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
        <div className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
      </div>
    </div>
  );
}

function SourceSection({
  title,
  count,
  empty,
  items,
}: {
  title: string;
  count: number;
  empty: string;
  items: Array<{ key: string; title: string; text: string; score?: number; badge?: string }>;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">{title}</h3>
        <span className="chip">{count}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-slate-400">{empty}</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.key} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <div className="flex items-start justify-between gap-2">
                <h4 className="line-clamp-1 text-xs font-semibold text-slate-800">{item.title}</h4>
                {typeof item.score === 'number' && (
                  <span className="shrink-0 chip-teal">{item.score.toFixed(3)}</span>
                )}
              </div>
              <p className="mt-1 line-clamp-4 text-xs leading-4 text-slate-500">{item.text}</p>
              {item.badge && <span className="chip mt-1.5">{item.badge}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
