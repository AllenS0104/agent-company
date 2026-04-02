import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getThreads, getThreadMessages, exportThread } from '../api/client';
import { MessageBubble } from '../components/MessageBubble';
import { Clock, MessageSquare, Download, ArrowRight, Loader2 } from 'lucide-react';
import type { ThreadItem, MessageData } from '../types';

const MODE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  debate:  { bg: 'bg-indigo-500/10', text: 'text-indigo-400', label: '🗣️ Debate' },
  pair:    { bg: 'bg-green-500/10',  text: 'text-green-400',  label: '👥 Pair' },
  redblue: { bg: 'bg-red-500/10',    text: 'text-red-400',    label: '🔴🔵 Red/Blue' },
  spec:    { bg: 'bg-cyan-500/10',   text: 'text-cyan-400',   label: '📋 Spec' },
  tdd:     { bg: 'bg-amber-500/10',  text: 'text-amber-400',  label: '🧪 TDD' },
};

function formatRelativeTime(dateStr: string | undefined): string {
  if (!dateStr) return '';
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  if (isNaN(then)) return dateStr;
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60)    return '刚刚';
  if (diffSec < 3600)  return `${Math.floor(diffSec / 60)} 分钟前`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`;
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)} 天前`;
  return new Date(then).toLocaleDateString('zh-CN');
}

export function HistoryPage() {
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [selectedThread, setSelectedThread] = useState<ThreadItem | null>(null);
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getThreads()
      .then(setThreads)
      .catch((err: Error) => setError('加载历史记录失败: ' + err.message));
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-polling for in-progress discussions
  useEffect(() => {
    if (!selectedThread || selectedThread.status !== 'discussing') {
      setAutoRefresh(false);
      return;
    }
    setAutoRefresh(true);

    const timer = setInterval(async () => {
      try {
        const msgs = await getThreadMessages(selectedThread.id);
        setMessages(msgs);

        const freshThreads = await getThreads();
        const current = freshThreads.find(t => t.id === selectedThread.id);
        if (current) {
          setThreads(freshThreads);
          if (current.status !== 'discussing') {
            setSelectedThread(current);
            setAutoRefresh(false);
          }
        }
      } catch { /* ignore polling errors */ }
    }, 3000);

    return () => clearInterval(timer);
  }, [selectedThread?.id, selectedThread?.status]);

  const handleSelect = useCallback(async (thread: ThreadItem) => {
    setSelectedThread(thread);
    setLoading(true);
    setError('');
    try {
      setMessages(await getThreadMessages(thread.id));
    } catch (err: any) {
      setMessages([]);
      setError('加载消息失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleExport(e: React.MouseEvent, threadId: string) {
    e.stopPropagation();
    try {
      const blob = await exportThread(threadId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `discussion-${threadId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError('导出失败: ' + (err.message || '未知错误'));
    }
  }

  return (
    <div className="flex h-screen page-enter">
      {/* Thread list */}
      <div className="w-80 border-r border-white/5 overflow-y-auto bg-slate-950/50">
        <div className="p-5 border-b border-white/5">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Clock size={18} className="text-slate-500" />
            History
          </h2>
          <p className="text-xs text-slate-600 mt-1">{threads.length} 条讨论记录</p>
        </div>
        {threads.length === 0 ? (
          <div className="p-10 text-center">
            <div className="w-16 h-16 rounded-xl bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
              <MessageSquare size={28} className="text-slate-700" />
            </div>
            <p className="text-base text-slate-500 font-medium mb-1">还没有讨论记录</p>
            <p className="text-xs text-slate-700 mb-4">发起你的第一次 Agent 讨论吧</p>
            <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
              去发起一个 <ArrowRight size={14} />
            </Link>
          </div>
        ) : (
          threads.map((t, i) => {
            const modeStyle = MODE_STYLES[t.mode] ?? { bg: 'bg-white/5', text: 'text-slate-500', label: t.mode };
            const isDiscussing = t.status === 'discussing';
            return (
              <button key={t.id} onClick={() => handleSelect(t)}
                className={'w-full text-left p-4 border-b border-white/5 transition-all duration-200 animate-msg-in ' +
                  (selectedThread?.id === t.id
                    ? 'bg-indigo-500/8 border-l-2 border-l-indigo-400'
                    : 'hover:bg-white/[0.03] border-l-2 border-l-transparent')
                }
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <div className="flex items-center gap-2">
                  {isDiscussing && (
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
                  )}
                  <p className={'text-sm truncate font-medium ' + (isDiscussing ? 'text-emerald-200' : 'text-white')}>{t.topic}</p>
                </div>
                <div className="flex items-center gap-2 mt-2 text-[11px]">
                  <span className={`chip ${modeStyle.bg} ${modeStyle.text}`}>
                    {modeStyle.label}
                  </span>
                  {isDiscussing ? (
                    <span className="chip text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-1">
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      讨论中
                    </span>
                  ) : (
                    <span className="chip text-emerald-500 bg-emerald-500/8">
                      ✓ 已完成
                    </span>
                  )}
                  {'created_at' in t && (
                    <span className="text-slate-600 ml-auto">{formatRelativeTime((t as any).created_at)}</span>
                  )}
                  <button onClick={(e) => handleExport(e, t.id)}
                    className="ml-auto p-1 rounded-xl text-slate-500 hover:text-indigo-300 hover:bg-indigo-500/15 transition-all"
                    title="导出报告">
                    <Download size={12} />
                  </button>
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Status bar for active discussions */}
        {selectedThread?.status === 'discussing' && (
          <div className="px-4 py-2.5 border-b border-white/5 bg-indigo-500/5 flex items-center gap-2 flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            <span className="text-xs text-indigo-300 font-medium">讨论进行中...</span>
            <span className="text-xs text-slate-600">
              已产生 {messages.length} 条消息 · 每 3 秒自动刷新
            </span>
            {autoRefresh && (
              <Loader2 size={12} className="animate-spin text-indigo-400 ml-auto" />
            )}
          </div>
        )}

        {/* Completion bar */}
        {selectedThread && selectedThread.status !== 'discussing' && messages.length > 0 && (
          <div className="px-4 py-2.5 border-b border-white/5 bg-emerald-500/5 flex items-center gap-2 flex-shrink-0">
            <span className="text-xs text-emerald-400 font-medium">✅ 讨论已完成</span>
            <span className="text-xs text-slate-600">
              共 {messages.length} 条消息
            </span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="card p-4 mb-4 border-red-500/15 bg-red-500/5 animate-msg-in">
              <p className="text-sm text-red-400">❌ {error}</p>
            </div>
          )}
          {!selectedThread && !error && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-16 h-16 rounded-xl bg-white/[0.03] border border-white/5 flex items-center justify-center mx-auto mb-4">
                  <MessageSquare size={24} className="text-slate-700" />
                </div>
                <p className="text-base text-slate-500 font-medium">选择一条讨论查看详情</p>
                <p className="text-xs text-slate-700 mt-1">从左侧列表中点击选择</p>
              </div>
            </div>
          )}
          {loading && (
            <div className="flex items-center justify-center mt-16">
              <Loader2 size={20} className="animate-spin text-indigo-400 mr-2" />
              <span className="text-sm text-slate-400">加载中...</span>
            </div>
          )}
          {selectedThread && !loading && messages.map((msg, i) => (
            <div key={i} className="animate-msg-in" style={{ animationDelay: `${i * 0.06}s` }}>
              <MessageBubble msg={msg} />
            </div>
          ))}
          {selectedThread && !loading && messages.length === 0 && !error && (
            <div className="flex items-center justify-center mt-16">
              <div className="text-center">
                <Loader2 size={20} className="animate-spin text-indigo-400 mx-auto mb-3" />
                <p className="text-sm text-slate-400">等待 Agent 产生消息...</p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  );
}
