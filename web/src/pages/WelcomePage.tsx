import { useState, useRef, useEffect } from 'react';
import { updateConfig, getConfig, requestDeviceCode, pollGitHubToken } from '../api/client';
import { useTranslation } from 'react-i18next';

interface WelcomePageProps {
  onConfigured: () => void;
}

interface ProviderInfo {
  id: string;
  name: string;
  subtitle: string;
  emoji: string;
  desc: string;
  badge?: string;
  badgeColor?: string;
  fields: FieldDef[];
  helpText: string;
  helpUrl: string;
}

interface FieldDef {
  key: string;
  label: string;
  placeholder: string;
  required?: boolean;
}

const PROVIDERS: ProviderInfo[] = [
  {
    id: 'github',
    name: 'GitHub Models',
    subtitle: '免费 · 多模型',
    emoji: '🐙',
    desc: '免费使用 GitHub Models 上的多款模型，包括 GPT-4o、Llama、DeepSeek 等',
    badge: '⭐ 推荐 · 免费',
    badgeColor: 'from-amber-500 to-orange-500',
    fields: [
      { key: 'github_token', label: 'GitHub Token', placeholder: 'ghp_...', required: true },
    ],
    helpText: '从 GitHub Settings → Developer settings → Personal access tokens 生成',
    helpUrl: 'https://github.com/settings/tokens',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    subtitle: 'GPT-4o / o3',
    emoji: '🤖',
    desc: '使用 OpenAI 官方 API，支持 GPT-4o、o3-mini 等最新模型',
    fields: [
      { key: 'openai_api_key', label: 'API Key', placeholder: 'sk-...', required: true },
      { key: 'openai_base_url', label: 'Base URL（可选）', placeholder: 'https://api.openai.com/v1' },
    ],
    helpText: '从 OpenAI Platform 获取 API Key',
    helpUrl: 'https://platform.openai.com/api-keys',
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    subtitle: 'Gemini 2.5',
    emoji: '✨',
    desc: '使用 Google Gemini API，支持 Gemini 2.5 Pro / Flash 等模型',
    fields: [
      { key: 'gemini_api_key', label: 'API Key', placeholder: 'AIza...', required: true },
    ],
    helpText: '从 Google AI Studio 获取 API Key',
    helpUrl: 'https://aistudio.google.com/apikey',
  },
  {
    id: 'claude',
    name: 'Claude (Anthropic)',
    subtitle: 'Sonnet / Opus',
    emoji: '🧠',
    desc: '使用 Anthropic Claude API，支持 Claude Sonnet 4、Opus 4 等模型',
    fields: [
      { key: 'claude_api_key', label: 'API Key', placeholder: 'sk-ant-...', required: true },
    ],
    helpText: '从 Anthropic Console 获取 API Key',
    helpUrl: 'https://console.anthropic.com/settings/keys',
  },
];

type DeviceFlowState = 'idle' | 'waiting' | 'success' | 'error';
type GitHubTab = 'oauth' | 'token';

function Spinner({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={`${className} animate-spin`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function GitHubDeviceFlow({ onConfigured }: { onConfigured: () => void }) {
  const { t } = useTranslation();
  const [deviceFlow, setDeviceFlow] = useState<DeviceFlowState>('idle');
  const [userCode, setUserCode] = useState('');
  const [verificationUri, setVerificationUri] = useState('');
  const [githubUser, setGithubUser] = useState<{ login: string; avatar_url: string; name: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const abortRef = useRef(false);

  useEffect(() => {
    return () => { abortRef.current = true; };
  }, []);

  async function pollUntilDone(deviceCode: string, interval: number) {
    let retries = 0;
    const maxRetries = 3;

    while (!abortRef.current) {
      await new Promise(r => setTimeout(r, interval * 1000));
      if (abortRef.current) break;

      try {
        const result = await pollGitHubToken(deviceCode);
        retries = 0; // reset on success

        if (result.status === 'success') {
          setDeviceFlow('success');
          setGithubUser(result.user || null);
          return;
        } else if (result.status === 'expired') {
          setDeviceFlow('error');
          setError(t('welcome.authExpired'));
          return;
        } else if (result.status === 'error') {
          setDeviceFlow('error');
          setError(result.error || t('welcome.authFailed'));
          return;
        } else if (result.status === 'slow_down') {
          interval = result.interval || interval + 5;
        }
        // 'pending' → continue polling
      } catch {
        retries++;
        if (retries >= maxRetries) {
          setDeviceFlow('error');
          setError(t('welcome.networkError'));
          return;
        }
        // retry after a short delay
        await new Promise(r => setTimeout(r, 2000));
      }
    }
  }

  async function startGitHubLogin() {
    setDeviceFlow('waiting');
    setError('');
    setCopied(false);
    abortRef.current = false;
    try {
      const { device_code, user_code, verification_uri, interval } = await requestDeviceCode();
      setUserCode(user_code);
      setVerificationUri(verification_uri);
      window.open(verification_uri, '_blank');
      pollUntilDone(device_code, interval || 5);
    } catch {
      setDeviceFlow('error');
      setError(t('welcome.cannotGetCode'));
    }
  }

  async function handleCopyCode() {
    try {
      await navigator.clipboard.writeText(userCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  if (deviceFlow === 'idle') {
    return (
      <div className="space-y-4">
        <p className="text-[11px] text-slate-500 leading-relaxed">
          {t('welcome.loginHint')}
        </p>
        <button
          onClick={startGitHubLogin}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-slate-800 to-slate-700 hover:from-slate-700 hover:to-slate-600 text-white font-medium text-sm transition-all border border-white/10 hover:border-white/20 flex items-center justify-center gap-2"
        >
          <span className="text-lg">🐙</span>
          {t('welcome.loginWithGithub')}
        </button>
      </div>
    );
  }

  if (deviceFlow === 'waiting') {
    return (
      <div className="space-y-4">
        <div className="text-center">
          <p className="text-[11px] text-slate-400 mb-3">{t('welcome.enterCode')}</p>
          <div className="inline-block border-2 border-dashed border-indigo-500/40 rounded-xl px-8 py-4 bg-indigo-500/5">
            <span className="text-2xl font-mono font-bold text-white tracking-[0.3em]">{userCode}</span>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleCopyCode}
            className="flex-1 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-slate-300 transition-all flex items-center justify-center gap-1.5"
          >
            {copied ? `✓ ${t('welcome.copied')}` : `📋 ${t('welcome.copyCode')}`}
          </button>
          <a
            href={verificationUri}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-slate-300 transition-all flex items-center justify-center gap-1.5"
          >
            🔗 {t('welcome.openGithub')}
          </a>
        </div>

        <div className="flex items-center justify-center gap-2 pt-2">
          <Spinner className="w-4 h-4 text-indigo-400" />
          <span className="text-xs text-slate-500">{t('welcome.waitingAuth')}</span>
        </div>
      </div>
    );
  }

  if (deviceFlow === 'success') {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          {githubUser?.avatar_url && (
            <img
              src={githubUser.avatar_url}
              alt={githubUser.login}
              className="w-10 h-10 rounded-full border-2 border-emerald-500/30"
            />
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-emerald-400">✅ {t('welcome.authSuccess')}</p>
            <p className="text-xs text-slate-400 truncate">
              {t('welcome.welcome')}, @{githubUser?.login}
              {githubUser?.name && ` (${githubUser.name})`}
            </p>
          </div>
        </div>

        <button
          onClick={onConfigured}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2"
        >
          {t('welcome.startUsing')}
        </button>
      </div>
    );
  }

  // error state
  return (
    <div className="space-y-4">
      <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
        <p className="text-xs text-red-400">❌ {error || t('welcome.authFailed')}</p>
      </div>
      <button
        onClick={() => { setDeviceFlow('idle'); setError(''); }}
        className="w-full py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium text-sm transition-all flex items-center justify-center gap-2"
      >
        🔄 {t('welcome.retry')}
      </button>
    </div>
  );
}

export function WelcomePage({ onConfigured }: WelcomePageProps) {
  const { t } = useTranslation();
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [githubTab, setGithubTab] = useState<GitHubTab>('oauth');

  function handleCardClick(providerId: string) {
    setSelectedProvider(prev => prev === providerId ? null : providerId);
    setFormValues({});
    setError('');
    setGithubTab('oauth');
  }

  function handleFieldChange(key: string, value: string) {
    setFormValues(prev => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(provider: ProviderInfo) {
    const requiredFields = provider.fields.filter(f => f.required !== false);
    const missing = requiredFields.find(f => !formValues[f.key]?.trim());
    if (missing) {
      setError(`${t('welcome.pleaseEnter')} ${missing.label}`);
      return;
    }

    setSaving(true);
    setError('');
    try {
      const updates: Record<string, string> = {};
      for (const field of provider.fields) {
        if (formValues[field.key]?.trim()) {
          updates[field.key] = formValues[field.key].trim();
        }
      }
      await updateConfig(updates);
      // Verify config was saved
      const cfg = await getConfig();
      const providerCfg = cfg.providers?.[provider.id];
      if (providerCfg?.configured) {
        onConfigured();
      } else {
        setError(t('welcome.configSavedButInactive'));
      }
    } catch (err: any) {
      setError(`${t('welcome.saveFailed')}: ` + (err.message || ''));
    } finally {
      setSaving(false);
    }
  }

  const selected = PROVIDERS.find(p => p.id === selectedProvider);
  const isGitHub = selected?.id === 'github';

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-b from-slate-950 via-[#0c1029] to-[#0a0e1a] p-6">
      {/* Background decorative elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-indigo-500/15 to-purple-600/15 border border-indigo-500/15 flex items-center justify-center mx-auto mb-5 animate-float">
            <span className="text-3xl">🏢</span>
          </div>
          <h1 className="text-4xl font-bold gradient-text mb-2">{t('welcome.title')}</h1>
          <p className="text-base text-slate-400 mb-1">{t('welcome.subtitle')}</p>
          <p className="text-xs text-slate-600">{t('welcome.chooseProvider')}</p>
        </div>

        {/* Provider cards grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {PROVIDERS.map(provider => {
            const isSelected = selectedProvider === provider.id;
            return (
              <button
                key={provider.id}
                onClick={() => handleCardClick(provider.id)}
                className={`
                  relative text-left rounded-xl p-5 transition-all duration-300 group
                  ${isSelected
                    ? 'bg-white/[0.06] border-2 border-indigo-500/40 shadow-lg shadow-indigo-500/8 scale-[1.02]'
                    : 'card card-hover hover:scale-[1.01]'
                  }
                `}
              >
                {/* Recommended badge */}
                {provider.badge && (
                  <span className={`absolute -top-2.5 -right-2 px-2.5 py-0.5 rounded-full text-[11px] font-bold text-white bg-gradient-to-r ${provider.badgeColor} shadow-md`}>
                    {provider.badge}
                  </span>
                )}

                <div className="text-3xl mb-3">{provider.emoji}</div>
                <h3 className="text-base font-bold text-white mb-0.5">{provider.name}</h3>
                <p className="text-[11px] text-indigo-400/70 font-medium mb-2">{provider.subtitle}</p>
                <p className="text-[11px] text-slate-500 leading-relaxed">{provider.desc}</p>

                {/* Selection indicator */}
                {isSelected && (
                  <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Configuration form (slides in when a provider is selected) */}
        {selected && (
          <div className="card rounded-xl p-6 mb-6 animate-msg-in">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <span className="text-lg">{selected.emoji}</span>
              配置 {selected.name}
            </h3>

            {/* GitHub: tab switcher between OAuth and manual token */}
            {isGitHub && (
              <div className="flex mb-4 rounded-xl bg-white/5 p-1 border border-white/5">
                <button
                  onClick={() => setGithubTab('oauth')}
                  className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all ${
                    githubTab === 'oauth'
                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-500 hover:text-slate-400 border border-transparent'
                  }`}
                >
                  🔐 {t('welcome.githubLogin')}
                </button>
                <button
                  onClick={() => setGithubTab('token')}
                  className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all ${
                    githubTab === 'token'
                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-500 hover:text-slate-400 border border-transparent'
                  }`}
                >
                  🔑 {t('welcome.manualToken')}
                </button>
              </div>
            )}

            {/* GitHub OAuth tab */}
            {isGitHub && githubTab === 'oauth' && (
              <GitHubDeviceFlow onConfigured={onConfigured} />
            )}

            {/* Manual token / other providers form */}
            {(!isGitHub || githubTab === 'token') && (
              <>
                <div className="space-y-4">
                  {selected.fields.map(field => (
                    <div key={field.key}>
                      <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">
                        {field.label} {field.required !== false && <span className="text-red-400">*</span>}
                      </label>
                      <input
                        type="password"
                        placeholder={field.placeholder}
                        value={formValues[field.key] || ''}
                        onChange={e => handleFieldChange(field.key, e.target.value)}
                        className="w-full bg-white/5 text-slate-200 border border-white/10 rounded-xl px-4 py-3.5 text-base focus:outline-none focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 transition-all placeholder-slate-700"
                        autoFocus={field.required !== false}
                      />
                    </div>
                  ))}
                </div>

                {/* Help link */}
                <p className="text-[11px] text-slate-600 mt-3">
                  {selected.helpText}
                  {' → '}
                  <a
                    href={selected.helpUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
                  >
                    {t('welcome.getKey')}
                  </a>
                </p>

                {/* Error */}
                {error && (
                  <div className="mt-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
                    <p className="text-xs text-red-400">❌ {error}</p>
                  </div>
                )}

                {/* Submit */}
                <button
                  onClick={() => handleSubmit(selected)}
                  disabled={saving}
                  className="mt-4 w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:from-slate-800 disabled:to-slate-800 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-500/20 disabled:shadow-none disabled:text-slate-600 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {saving ? (
                    <>
                      <Spinner />
                      {t('welcome.saving')}
                    </>
                  ) : (
                    <>{`🚀 ${t('welcome.saveAndStart')}`}</>
                  )}
                </button>
              </>
            )}
          </div>
        )}

        {/* Footer note */}
        <p className="text-center text-[11px] text-slate-700">
          🔒 {t('welcome.privacyNote')}
        </p>
      </div>
    </div>
  );
}
