import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getMemories, getMemorySummary } from '../api/client';
import { Search, Brain, Loader2, ArrowRight, Lightbulb, Scale, Wrench, Star, Archive, Tag, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { MemoryItem, MemorySummary } from '../types';

const TYPE_CONFIG: Record<string, { emoji: string; bg: string; text: string; border: string; icon: typeof Brain }> = {
  decision_history: { emoji: '⚖️', bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/15', icon: Scale },
  knowledge:        { emoji: '💬', bg: 'bg-cyan-500/10',   text: 'text-cyan-400',   border: 'border-cyan-500/15',   icon: Lightbulb },
  lesson_learned:   { emoji: '📖', bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/15', icon: Lightbulb },
  style_guide:      { emoji: '🎨', bg: 'bg-pink-500/10',   text: 'text-pink-400',   border: 'border-pink-500/15',   icon: Wrench },
  adr:              { emoji: '📋', bg: 'bg-amber-500/10',  text: 'text-amber-400',  border: 'border-amber-500/15',  icon: Wrench },
};

function formatMemoryDate(dateStr: string | undefined): string {
  if (!dateStr) return '';
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  if (isNaN(then)) return dateStr.slice(0, 10);
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 3600)  return `${Math.max(1, Math.floor(diffSec / 60))} 分钟前`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`;
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)} 天前`;
  return new Date(then).toLocaleDateString('zh-CN');
}

function ImportanceStars({ level }: { level: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" title={`重要度: ${level}/5`}>
      {Array.from({ length: 5 }, (_, i) => (
        <Star key={i} size={12}
          className={i < level ? 'text-yellow-400 fill-yellow-400' : 'text-slate-700'}
        />
      ))}
    </span>
  );
}

export function MemoryPage() {
  const { t } = useTranslation();
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [keyword, setKeyword] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function loadSummary() {
    try { setSummary(await getMemorySummary()); }
    catch { /* ignore */ }
  }

  async function search() {
    setLoading(true);
    setError('');
    try { setMemories(await getMemories(keyword, 20, selectedTags)); }
    catch (err: any) { setMemories([]); setError('搜索失败: ' + (err.message || '未知错误')); }
    finally { setLoading(false); }
  }

  function toggleTag(tag: string) {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  }

  useEffect(() => { loadSummary(); search(); }, []);
  useEffect(() => { search(); }, [selectedTags]);

  return (
    <div className="p-6 max-w-4xl mx-auto page-enter">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center shadow-lg shadow-purple-500/25">
          <Brain size={20} className="text-white" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">{t('memoryPage.title')}</h2>
          <p className="text-xs text-slate-500">{t('memoryPage.subtitle')}</p>
        </div>
        {memories.length > 0 && (
          <span className="ml-auto text-xs text-slate-600 bg-white/5 px-2.5 py-1 rounded-full">
            共 {memories.length} 条记忆
          </span>
        )}
      </div>

      {/* Summary Card */}
      {summary && summary.total > 0 && (
        <div className="card p-4 mb-6 grid grid-cols-2 sm:grid-cols-4 gap-3 animate-msg-in">
          <div className="text-center">
            <div className="text-xl font-bold text-white">{summary.active}</div>
            <div className="text-xs text-slate-500">{t('memoryPage.active')}</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-slate-400 flex items-center justify-center gap-1">
              <Archive size={16} /> {summary.archived}
            </div>
            <div className="text-xs text-slate-500">{t('memoryPage.archived')}</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-indigo-400">{Object.keys(summary.by_type).length}</div>
            <div className="text-xs text-slate-500">记忆类型</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-amber-400 flex items-center justify-center gap-1">
              <Tag size={16} /> {summary.all_tags.length}
            </div>
            <div className="text-xs text-slate-500">{t('memoryPage.tags')}</div>
          </div>
        </div>
      )}

      {/* Tag Filter */}
      {summary && summary.all_tags.length > 0 && (
        <div className="flex gap-1.5 mb-4 flex-wrap items-center">
          <span className="text-xs text-slate-500 mr-1">{t('memoryPage.allTags')}:</span>
          {summary.all_tags.map(tag => (
            <button key={tag}
              onClick={() => toggleTag(tag)}
              className={`chip border transition-all cursor-pointer ${
                selectedTags.includes(tag)
                  ? 'bg-purple-500/15 text-purple-300 border-purple-500/20'
                  : 'bg-white/5 text-slate-500 border-white/5 hover:border-white/15'
              }`}
            >
              #{tag}
              {selectedTags.includes(tag) && <X size={10} className="inline ml-1" />}
            </button>
          ))}
          {selectedTags.length > 0 && (
            <button onClick={() => setSelectedTags([])}
              className="text-[11px] text-red-400 hover:text-red-300 ml-2 transition-colors">
              清除筛选
            </button>
          )}
        </div>
      )}

      {/* Search */}
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1 group">
          <Search size={15} className="absolute left-3.5 top-3 text-slate-600 group-focus-within:text-indigo-400 transition-colors" />
          <input type="text" value={keyword}
            onChange={e => setKeyword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            placeholder={t('memoryPage.search')}
            className="w-full bg-white/5 text-white border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm placeholder-slate-600 focus:outline-none focus:border-purple-500/40 focus:ring-2 focus:ring-purple-500/10 transition-all" />
        </div>
        <button onClick={search} disabled={loading}
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:from-slate-800 disabled:to-slate-800 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all shadow-lg shadow-purple-500/15 disabled:shadow-none flex items-center gap-2">
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          {t('memoryPage.search')}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={20} className="animate-spin text-purple-400 mr-2" />
          <span className="text-sm text-slate-400">{t('common.loading')}</span>
        </div>
      )}

      {error && (
        <div className="card p-4 mb-4 border-red-500/15 bg-red-500/5 animate-msg-in">
          <p className="text-sm text-red-400">❌ {error}</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && memories.length === 0 && (
        <div className="text-center py-20">
          <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-purple-500/8 to-pink-500/8 border border-purple-500/10 flex items-center justify-center mx-auto mb-5 animate-float">
            <Brain size={36} className="text-purple-700" />
          </div>
          <h3 className="text-lg font-bold text-slate-300 mb-2">{t('memoryPage.empty')}</h3>
          <p className="text-sm text-slate-600 mb-5 leading-relaxed max-w-sm mx-auto">
            {t('memoryPage.emptyHint')}
          </p>
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-purple-400 hover:text-purple-300 font-medium transition-colors">
            {t('history.startOne')} <ArrowRight size={14} />
          </Link>
        </div>
      )}

      {/* Memory cards */}
      <div className="space-y-3">
        {memories.map((mem, i) => {
          const typeKey = mem.type?.toLowerCase() ?? '';
          const config = TYPE_CONFIG[typeKey] ?? { emoji: '📝', bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/15', icon: Brain };
          return (
            <div key={mem.id}
              className="card card-hover p-5 animate-msg-in"
              style={{ animationDelay: `${i * 0.06}s` }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className={`chip ${config.bg} ${config.text} ${config.border} border uppercase tracking-wider`}>
                  <span className="mr-1">{config.emoji}</span>
                  {mem.type}
                </span>
                <span className="text-sm font-medium text-white">{mem.title}</span>
                <span className="ml-auto flex items-center gap-2">
                  <ImportanceStars level={mem.importance ?? 3} />
                  <span className="text-[11px] text-slate-600">{formatMemoryDate(mem.created_at)}</span>
                </span>
              </div>
              <p className="text-sm text-slate-400 whitespace-pre-wrap leading-relaxed line-clamp-4">{mem.content}</p>
              {mem.tags && mem.tags.length > 0 && (
                <div className="flex gap-1.5 mt-3 flex-wrap">
                  {mem.tags.map(tag => (
                    <span key={tag}
                      onClick={() => toggleTag(tag)}
                      className={`chip border cursor-pointer transition-all ${
                        selectedTags.includes(tag)
                          ? 'bg-purple-500/15 text-purple-300 border-purple-500/20'
                          : 'bg-white/5 text-slate-500 border-white/5 hover:border-white/15'
                      }`}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
