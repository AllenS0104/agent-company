import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Settings2, Download, Sparkles, Key } from 'lucide-react';
import { postDiscuss, getModes, getProviders, exportThread, getConfig, updateConfig, getThreads, getThreadMessages } from '../api/client';
import { MessageBubble } from '../components/MessageBubble';
import { DecisionCard } from '../components/DecisionCard';
import { TaskList } from '../components/TaskList';
import type { DiscussResponse, ModeInfo } from '../types';

const MODEL_OPTIONS: Record<string, string[]> = {
  github: [
    // OpenAI — GPT-5 Series
    'openai/gpt-5.4', 'openai/gpt-5.4-mini',
    'openai/gpt-5.3-codex', 'openai/gpt-5.2-codex',
    'openai/gpt-5.2', 'openai/gpt-5.1', 'openai/gpt-5-mini',
    // OpenAI — GPT-4 Series
    'openai/gpt-4.1', 'openai/gpt-4.1-mini', 'openai/gpt-4.1-nano',
    // OpenAI — Reasoning
    'openai/o4-mini', 'openai/o3', 'openai/o3-mini',
    // DeepSeek
    'deepseek/DeepSeek-R1', 'deepseek/DeepSeek-V3-0324',
    // Meta Llama 4
    'meta/Llama-4-Scout-17B-16E-Instruct', 'meta/Llama-4-Maverick-17B-128E-Instruct-FP8',
    // xAI
    'xai/grok-3', 'xai/grok-3-mini',
    // Others
    'cohere/cohere-command-a',
    'microsoft/Phi-4', 'microsoft/Phi-4-mini-instruct',
    'Codestral-2501', 'mistral-small-2503',
  ],
  openai: [
    'gpt-5.4', 'gpt-5.4-mini',
    'gpt-5.3-codex', 'gpt-5.2-codex',
    'gpt-5.2', 'gpt-5.1', 'gpt-5-mini',
    'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano',
    'o4-mini', 'o3-mini',
  ],
  gemini: [
    'gemini-3.1-pro', 'gemini-3.1-flash',
    'gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash',
  ],
  claude: [
    'claude-sonnet-4-20250514', 'claude-opus-4-20250514',
    'claude-haiku-4-20250414',
    'claude-sonnet-4.5', 'claude-sonnet-4.6',
    'claude-opus-4.5', 'claude-opus-4.6',
    'claude-opus-4-20250514',
  ],
};

const LOADING_PHASES = [
  { text: '收集观点...', emoji: '💡', sub: 'Agents are sharing initial perspectives' },
  { text: '质疑讨论...', emoji: '⚔️', sub: 'Challenging ideas and exploring alternatives' },
  { text: '深入分析...', emoji: '🔬', sub: 'Evaluating trade-offs and risks' },
  { text: '仲裁决策...', emoji: '⚖️', sub: 'Synthesizing conclusions' },
];

const SAMPLE_TOPICS = [
  { emoji: '🚀', title: '微服务 vs 单体架构', desc: '探讨不同项目规模下的最佳架构选择' },
  { emoji: '🔐', title: 'JWT vs Session 认证方案', desc: '分析两种主流认证方式的优劣' },
  { emoji: '📊', title: 'React vs Vue 技术选型', desc: '从团队、生态和性能角度比较前端框架' },
  { emoji: '🤖', title: 'AI Agent 协作模式设计', desc: '多 Agent 系统的通信与协调策略' },
];

interface DiscussPageProps {
  onReconfigure?: () => void;
}

export function DiscussPage({ onReconfigure }: DiscussPageProps) {
  const [topic, setTopic] = useState('');
  const [mode, setMode] = useState('debate');
  const [rounds, setRounds] = useState(2);
  const [extended, setExtended] = useState(false);
  const [provider, setProvider] = useState('github');
  const [model, setModel] = useState('openai/gpt-4.1');
  const [showSettings, setShowSettings] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiscussResponse | null>(null);
  const [modes, setModes] = useState<ModeInfo[]>([]);
  const [providers, setProviders] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [loadingPhase, setLoadingPhase] = useState(0);
  const [showApiKeys, setShowApiKeys] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [claudeKey, setClaudeKey] = useState('');
  const [configStatus, setConfigStatus] = useState<any>(null);
  const [configSaved, setConfigSaved] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollActiveDiscussion = useCallback((threadId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const threads = await getThreads();
        const current = threads.find(t => t.id === threadId);
        if (current && current.status !== 'discussing') {
          if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
          const msgs = await getThreadMessages(threadId);
          setResult({
            success: true,
            thread_id: threadId,
            messages: msgs,
            decision: null,
            tasks: [],
            error: '',
          });
          setLoading(false);
        }
      } catch { /* ignore polling errors */ }
    }, 3000);
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    getModes().then(setModes).catch((err: Error) => setError('加载模式失败: ' + err.message));
    getProviders().then(setProviders).catch((err: Error) => setError('加载服务商失败: ' + err.message));
    getConfig().then(setConfigStatus).catch(() => {});

    // Check for any active discussion and resume polling
    getThreads().then(threads => {
      const active = threads.find(t => t.status === 'discussing');
      if (active) {
        setLoading(true);
        setTopic(active.topic);
        pollActiveDiscussion(active.id);
      }
    }).catch(() => {});
  }, [pollActiveDiscussion]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [result]);

  // Cycle through loading phases
  useEffect(() => {
    if (!loading) { setLoadingPhase(0); return; }
    const timer = setInterval(() => {
      setLoadingPhase(p => (p + 1) % LOADING_PHASES.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [loading]);

  function handleProviderChange(p: string) {
    setProvider(p);
    const models = MODEL_OPTIONS[p] ?? [];
    setModel(models[0] ?? '');
  }

  function handleQuickTopic(title: string) {
    setTopic(title);
  }

  async function handleSaveConfig() {
    const updates: Record<string, string> = {};
    if (githubToken) updates.github_token = githubToken;
    if (openaiKey) updates.openai_api_key = openaiKey;
    if (geminiKey) updates.gemini_api_key = geminiKey;
    if (claudeKey) updates.claude_api_key = claudeKey;
    try {
      await updateConfig(updates);
      setConfigSaved(true);
      setConfigStatus(await getConfig());
      setTimeout(() => setConfigSaved(false), 3000);
    } catch (err: any) {
      setError('配置保存失败: ' + err.message);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim() || loading) return;
    setLoading(true);
    setResult(null);
    setError('');
    try {
      const data = await postDiscuss({
        topic: topic.trim(), mode, max_rounds: rounds,
        extended_agents: extended, provider, model,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    if (!result?.thread_id) return;
    try {
      const blob = await exportThread(result.thread_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `discussion-${result.thread_id}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError('导出失败: ' + (err.message || '未知错误'));
    }
  }

  const currentModels = MODEL_OPTIONS[provider] || [];
  const phase = LOADING_PHASES[loadingPhase];

  return (
    <div className="flex flex-col h-screen bg-gradient-to-b from-slate-950 to-[#0a0e1a] page-enter">
      {/* Header */}
      <header className="px-6 py-4 border-b border-white/5 flex items-center justify-between glass">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">New Discussion</h2>
          <p className="text-xs text-slate-500 mt-0.5">Multi-agent collaborative analysis</p>
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className={'p-2 rounded-xl transition-all duration-200 ' + (showSettings ? 'bg-indigo-500/15 text-indigo-300 rotate-90' : 'text-slate-500 hover:bg-white/5 hover:text-slate-300')}
        >
          <Settings2 size={18} />
        </button>
      </header>

      {/* Settings panel */}
      {showSettings && (
        <div className="px-6 py-4 border-b border-white/5 glass animate-settings">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">Provider</label>
              <select value={provider} onChange={e => handleProviderChange(e.target.value)}
                className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-colors">
                {(providers.length > 0 ? providers : ['github', 'openai', 'gemini', 'claude']).map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">Model</label>
              <select value={model} onChange={e => setModel(e.target.value)}
                className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-colors">
                {currentModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">Workflow</label>
              <select value={mode} onChange={e => setMode(e.target.value)}
                className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-colors">
                {modes.length > 0
                  ? modes.map(m => <option key={m.id} value={m.id}>{m.name}</option>)
                  : ['debate','pair','redblue','spec','tdd'].map(m => <option key={m} value={m}>{m}</option>)
                }
              </select>
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">Options</label>
              <div className="flex items-center gap-4 py-2">
                <div className="flex items-center gap-1.5">
                  <label className="text-[11px] text-slate-400">Rounds</label>
                  <input type="number" min={1} max={10} value={rounds}
                    onChange={e => {
                      const v = parseInt(e.target.value, 10);
                      if (!Number.isNaN(v)) setRounds(Math.min(10, Math.max(1, v)));
                    }}
                    className="w-12 bg-white/5 text-slate-200 border border-white/10 rounded-xl px-2 py-1 text-xs text-center focus:outline-none focus:border-indigo-500/50 transition-colors" />
                </div>
                <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer select-none">
                  <input type="checkbox" checked={extended}
                    onChange={e => setExtended(e.target.checked)}
                    className="rounded border-slate-600 bg-white/5 text-indigo-500 focus:ring-indigo-500/20" />
                  Extended
                </label>
              </div>
            </div>
          </div>

          {/* API Key Configuration */}
          <div className="mt-4 pt-4 border-t border-white/5">
            <button onClick={() => setShowApiKeys(!showApiKeys)}
              className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5 hover:text-slate-300 transition-colors">
              <Key size={12} />
              API Keys {showApiKeys ? '▾' : '▸'}
              {configStatus && (
                <span className="ml-2 text-[11px] normal-case text-slate-600">
                  {Object.values(configStatus.providers || {}).filter((p: any) => p.configured).length}/{Object.keys(configStatus.providers || {}).length} configured
                </span>
              )}
            </button>

            {showApiKeys && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
                {/* GitHub Token */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">
                    GitHub Token {configStatus?.providers?.github?.configured ? '✅' : '❌'}
                  </label>
                  <input type="password" placeholder="ghp_..." value={githubToken}
                    onChange={e => setGithubToken(e.target.value)}
                    className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-colors placeholder-slate-700" />
                </div>

                {/* OpenAI API Key */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">
                    OpenAI API Key {configStatus?.providers?.openai?.configured ? '✅' : '❌'}
                  </label>
                  <input type="password" placeholder="sk-..." value={openaiKey}
                    onChange={e => setOpenaiKey(e.target.value)}
                    className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-colors placeholder-slate-700" />
                </div>

                {/* Gemini API Key */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">
                    Gemini API Key {configStatus?.providers?.gemini?.configured ? '✅' : '❌'}
                  </label>
                  <input type="password" placeholder="AIza..." value={geminiKey}
                    onChange={e => setGeminiKey(e.target.value)}
                    className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-colors placeholder-slate-700" />
                </div>

                {/* Claude API Key */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">
                    Claude API Key {configStatus?.providers?.claude?.configured ? '✅' : '❌'}
                  </label>
                  <input type="password" placeholder="sk-ant-..." value={claudeKey}
                    onChange={e => setClaudeKey(e.target.value)}
                    className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-colors placeholder-slate-700" />
                </div>

                {/* Save button */}
                <div className="col-span-full flex items-center gap-3">
                  <button onClick={handleSaveConfig}
                    className="px-4 py-2 rounded-xl bg-indigo-500/15 text-indigo-300 hover:bg-indigo-500/25 transition-all text-xs font-medium border border-indigo-500/15">
                    💾 保存配置（当前会话）
                  </button>
                  {onReconfigure && (
                    <button onClick={onReconfigure}
                      className="px-4 py-2 rounded-xl bg-amber-500/8 text-amber-300 hover:bg-amber-500/15 transition-all text-xs font-medium border border-amber-500/15">
                      🔄 重新配置 Provider
                    </button>
                  )}
                  {configSaved && (
                    <span className="text-xs text-emerald-400 animate-phase">✅ 已保存</span>
                  )}
                  <span className="text-[11px] text-slate-600">* 配置仅在当前会话有效，重启后需重新输入</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* Empty / welcome state */}
        {!result && !loading && !error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-lg">
              <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-indigo-500/15 to-purple-600/15 border border-indigo-500/15 flex items-center justify-center mx-auto mb-5 animate-float">
                <span className="text-3xl">🏢</span>
              </div>
              <h3 className="text-3xl font-bold gradient-text mb-2">Agent Company</h3>
              <p className="text-base text-slate-500 leading-relaxed mb-6">
                输入话题，多个 AI Agent 将从不同视角协作分析<br/>
                产品、架构、开发、评审 —— 全方位讨论
              </p>

              {/* Agent role badges */}
              <div className="flex items-center justify-center gap-2.5 mb-8 flex-wrap">
                <span className="chip bg-yellow-500/8 border border-yellow-500/12 text-yellow-400/80 text-xs px-3.5 py-2">💡 Idea</span>
                <span className="chip bg-blue-500/8 border border-blue-500/12 text-blue-400/80 text-xs px-3.5 py-2">🏗️ Architect</span>
                <span className="chip bg-green-500/8 border border-green-500/12 text-green-400/80 text-xs px-3.5 py-2">💻 Coder</span>
                <span className="chip bg-red-500/8 border border-red-500/12 text-red-400/80 text-xs px-3.5 py-2">🔍 Reviewer</span>
                <span className="chip bg-purple-500/8 border border-purple-500/12 text-purple-400/80 text-xs px-3.5 py-2">🧪 QA</span>
                <span className="chip bg-red-600/8 border border-red-600/12 text-red-300/80 text-xs px-3.5 py-2">🛡️ Security</span>
              </div>

              {/* Quick-start topics */}
              <div className="text-left">
                <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Sparkles size={12} /> 快速开始 · 点击话题即可发起讨论
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {SAMPLE_TOPICS.map(t => (
                    <button
                      key={t.title}
                      onClick={() => handleQuickTopic(t.title)}
                      className="topic-card text-left card card-hover p-3.5 group"
                    >
                      <div className="flex items-start gap-2.5">
                        <span className="text-lg mt-0.5">{t.emoji}</span>
                        <div>
                          <p className="text-sm font-medium text-slate-200 group-hover:text-white transition-colors">{t.title}</p>
                          <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">{t.desc}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading with meeting scene */}
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              {/* Agent circle - meeting scene */}
              <div className="flex items-center justify-center gap-6 mb-8">
                {[
                  { emoji: '💡', label: 'Idea', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' },
                  { emoji: '🏗️', label: 'Architect', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
                  { emoji: '💻', label: 'Coder', bg: 'bg-green-500/10', border: 'border-green-500/20' },
                  { emoji: '🔍', label: 'Reviewer', bg: 'bg-red-500/10', border: 'border-red-500/20' },
                ].map((agent, i) => (
                  <div key={agent.label} className={`
                    flex flex-col items-center gap-2 transition-all duration-500
                    ${loadingPhase === i ? 'scale-125 opacity-100' : 'scale-100 opacity-50'}
                  `}>
                    <div className={`
                      w-14 h-14 rounded-2xl flex items-center justify-center text-2xl
                      ${loadingPhase === i ? 'speaking ring-2 ring-indigo-400/50' : ''}
                      ${agent.bg} border ${agent.border}
                    `}>
                      {agent.emoji}
                    </div>
                    <span className="text-[11px] text-slate-500">{agent.label}</span>
                  </div>
                ))}
              </div>

              {/* Phase indicator */}
              <div className="mb-6">
                <p className="text-lg font-semibold text-white animate-phase" key={`t-${loadingPhase}`}>
                  {phase.emoji} {phase.text}
                </p>
                <p className="text-sm text-slate-500 mt-1 animate-phase" key={`s-${loadingPhase}`}>
                  {phase.sub}
                </p>
              </div>

              {/* Step progress */}
              <div className="flex items-center gap-2 justify-center">
                {LOADING_PHASES.map((_, i) => (
                  <div key={i} className={`
                    h-1.5 rounded-full transition-all duration-500
                    ${i === loadingPhase ? 'w-8 bg-indigo-500' : i < loadingPhase ? 'w-4 bg-indigo-500/40' : 'w-4 bg-white/10'}
                  `} />
                ))}
              </div>

              <p className="text-xs text-slate-700 mt-6">讨论可能需要一分钟，请耐心等待</p>
            </div>
          </div>
        )}

        {error && (
          <div className="card p-4 border-red-500/15 bg-red-500/5 animate-msg-in">
            <p className="text-sm text-red-400">❌ {error}</p>
          </div>
        )}

        {result && (
          <div>
            {/* Messages with connection lines */}
            {result.messages.map((msg, i) => (
              <div key={i}>
                {i > 0 && (
                  <div className="flex justify-center py-1">
                    <div className="w-px h-4 bg-gradient-to-b from-white/10 to-transparent" />
                  </div>
                )}
                <div className="animate-msg-in" style={{ animationDelay: `${i * 0.08}s` }}>
                  <MessageBubble msg={msg} />
                </div>
              </div>
            ))}
            {result.decision && (
              <div className="animate-msg-in" style={{ animationDelay: `${result.messages.length * 0.08}s` }}>
                <DecisionCard decision={result.decision} />
              </div>
            )}
            {result.tasks.length > 0 && (
              <div className="animate-msg-in" style={{ animationDelay: `${(result.messages.length + 1) * 0.08}s` }}>
                <TaskList tasks={result.tasks} />
              </div>
            )}

            {/* Discussion complete with sparkle */}
            <div className="mt-6 card p-5 text-center flex items-center justify-center gap-4 animate-stamp relative overflow-hidden" style={{ animationDelay: `${(result.messages.length + 2) * 0.08}s` }}>
              <span className="sparkle-item absolute top-2 left-8 text-sm" style={{ animationDelay: '0s' }}>✨</span>
              <span className="sparkle-item absolute top-3 right-12 text-xs" style={{ animationDelay: '0.5s' }}>⭐</span>
              <span className="sparkle-item absolute bottom-2 left-16 text-xs" style={{ animationDelay: '1s' }}>💫</span>
              <span className="sparkle-item absolute bottom-3 right-20 text-sm" style={{ animationDelay: '0.3s' }}>✨</span>
              <p className="text-base text-emerald-400 font-medium">
                ✅ Discussion complete · {result.messages.length} messages · {result.tasks.length} tasks
              </p>
              <button onClick={handleExport}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-500/15 text-indigo-300 hover:bg-indigo-500/25 transition-all text-sm font-medium border border-indigo-500/15">
                <Download size={14} />
                📥 导出报告
              </button>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="px-6 py-4 border-t border-white/5 glass shadow-[0_-4px_24px_rgba(0,0,0,0.15)]">
        <div className="flex gap-3">
          <input
            type="text" value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="输入你想讨论的话题..."
            className="flex-1 bg-white/5 text-white border border-white/10 rounded-xl px-4 py-3.5 text-base placeholder-slate-600 focus:outline-none focus:border-indigo-500/40 focus:ring-2 focus:ring-indigo-500/10 transition-all"
            disabled={loading}
          />
          <button type="submit" disabled={!topic.trim() || loading}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-600 disabled:cursor-not-allowed text-white px-6 py-3.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20 disabled:shadow-none flex items-center gap-2 text-sm font-medium">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            {loading ? 'Thinking...' : 'Send'}
          </button>
        </div>
        <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-600">
          <span>{provider}/{model}</span>
          <span>·</span>
          <span>{modes.find(m => m.id === mode)?.name || mode} mode</span>
          <span>·</span>
          <span>{rounds} rounds</span>
          {extended && <><span>·</span><span className="text-purple-500">Extended agents</span></>}
        </div>
      </form>
    </div>
  );
}
