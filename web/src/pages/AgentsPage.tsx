import { useState, useEffect } from 'react';
import { Users, Plus, Pencil, Trash2, X, Loader2, Bot } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ROLE_CONFIG } from '../types';
import {
  listCustomAgents,
  createCustomAgent,
  updateCustomAgent,
  deleteCustomAgent,
} from '../api/client';
import type { CustomAgent } from '../api/client';

const BUILT_IN_AGENTS = [
  { role: 'idea',      name: 'Idea Agent',      desc: '产品需求分析' },
  { role: 'architect', name: 'Architect Agent', desc: '系统架构设计' },
  { role: 'coder',     name: 'Coder Agent',     desc: '编码实现' },
  { role: 'reviewer',  name: 'Reviewer Agent',  desc: '代码评审' },
  { role: 'qa',        name: 'QA Agent',        desc: '质量保障' },
  { role: 'security',  name: 'Security Agent',  desc: '安全审计' },
  { role: 'devops',    name: 'DevOps Agent',    desc: '运维部署' },
  { role: 'perf',      name: 'Perf Agent',      desc: '性能优化' },
  { role: 'docs',      name: 'Docs Agent',      desc: '文档编写' },
];

const PRESET_COLORS = [
  '#8b5cf6', '#6366f1', '#3b82f6', '#06b6d4', '#10b981',
  '#f59e0b', '#ef4444', '#ec4899', '#f97316', '#84cc16',
];

const PRESET_EMOJIS = [
  '🤖', '🧠', '🎯', '📊', '🔬', '🎨', '🛡️', '📈', '🔧', '💼',
  '🌐', '🗂️', '📐', '🧩', '🔮', '🎓', '🏆', '🚀', '💎', '⚙️',
];

interface FormData {
  name: string;
  emoji: string;
  description: string;
  system_prompt: string;
  color: string;
}

const EMPTY_FORM: FormData = {
  name: '',
  emoji: '🤖',
  description: '',
  system_prompt: '',
  color: '#8b5cf6',
};

export function AgentsPage() {
  const { t } = useTranslation();
  const [customAgents, setCustomAgents] = useState<CustomAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  async function loadAgents() {
    setLoading(true);
    try {
      setCustomAgents(await listCustomAgents());
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAgents(); }, []);

  function openCreate() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  }

  function openEdit(agent: CustomAgent) {
    setEditingId(agent.id);
    setForm({
      name: agent.name,
      emoji: agent.emoji,
      description: agent.description,
      system_prompt: agent.system_prompt,
      color: agent.color,
    });
    setModalOpen(true);
  }

  async function handleSave() {
    if (!form.name.trim() || !form.system_prompt.trim()) return;
    setSaving(true);
    try {
      if (editingId) {
        await updateCustomAgent(editingId, form);
      } else {
        await createCustomAgent({
          name: form.name,
          emoji: form.emoji,
          description: form.description,
          system_prompt: form.system_prompt,
          color: form.color,
        });
      }
      setModalOpen(false);
      await loadAgents();
    } catch (err: any) {
      setError(err.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(agentId: string) {
    try {
      await deleteCustomAgent(agentId);
      setDeleteConfirm(null);
      await loadAgents();
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto page-enter overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
          <Users size={20} className="text-white" />
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-bold text-white">{t('agents.title')}</h2>
          <p className="text-xs text-slate-500">{t('agents.subtitle')}</p>
        </div>
        <button
          onClick={openCreate}
          className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all shadow-lg shadow-violet-500/15 flex items-center gap-2"
        >
          <Plus size={16} />
          {t('agents.createBtn')}
        </button>
      </div>

      {error && (
        <div className="card p-4 mb-4 border-red-500/15 bg-red-500/5 animate-msg-in">
          <p className="text-sm text-red-400">❌ {error}</p>
        </div>
      )}

      {/* Built-in Agents */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <h3 className="text-sm font-semibold text-slate-400">{t('agents.builtIn')}</h3>
          <span className="text-[11px] text-slate-600 bg-white/5 px-2 py-0.5 rounded-full">
            {t('agents.readOnly')}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {BUILT_IN_AGENTS.map((agent, i) => {
            const cfg = ROLE_CONFIG[agent.role] || { emoji: '🤖', color: '#8b5cf6', label: agent.role };
            return (
              <div
                key={agent.role}
                className="card p-4 animate-msg-in opacity-90"
                style={{ animationDelay: `${i * 0.04}s` }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0"
                    style={{ backgroundColor: cfg.color + '18', border: `1px solid ${cfg.color}25` }}
                  >
                    {cfg.emoji}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-white truncate">{agent.name}</div>
                    <div className="text-xs text-slate-500 truncate">{agent.desc}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Custom Agents */}
      <div>
        <h3 className="text-sm font-semibold text-slate-400 mb-4">{t('agents.custom')}</h3>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={20} className="animate-spin text-violet-400 mr-2" />
            <span className="text-sm text-slate-400">{t('common.loading')}</span>
          </div>
        ) : customAgents.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-violet-500/8 to-indigo-500/8 border border-violet-500/10 flex items-center justify-center mx-auto mb-5 animate-float">
              <Bot size={36} className="text-violet-700" />
            </div>
            <h3 className="text-lg font-bold text-slate-300 mb-2">{t('agents.noCustom')}</h3>
            <p className="text-sm text-slate-600 mb-5 leading-relaxed max-w-sm mx-auto">
              {t('agents.noCustomHint')}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {customAgents.map((agent, i) => (
              <div
                key={agent.id}
                className="card card-hover p-4 animate-msg-in"
                style={{ animationDelay: `${i * 0.06}s` }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0"
                    style={{ backgroundColor: agent.color + '18', border: `1px solid ${agent.color}25` }}
                  >
                    {agent.emoji}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-white truncate">{agent.name}</div>
                    <div className="text-xs text-slate-500 truncate">{agent.description || '—'}</div>
                  </div>
                </div>
                <p className="text-xs text-slate-600 line-clamp-2 mb-3 leading-relaxed">
                  {agent.system_prompt.slice(0, 120)}
                  {agent.system_prompt.length > 120 ? '...' : ''}
                </p>
                <div className="flex items-center gap-2 justify-end">
                  <button
                    onClick={() => openEdit(agent)}
                    className="text-xs text-slate-500 hover:text-indigo-400 transition-colors flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-white/5"
                  >
                    <Pencil size={12} /> {t('agents.editBtn')}
                  </button>
                  {deleteConfirm === agent.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleDelete(agent.id)}
                        className="text-xs text-red-400 hover:text-red-300 transition-colors px-2 py-1 rounded-lg bg-red-500/10"
                      >
                        {t('agents.deleteConfirm')}
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(null)}
                        className="text-xs text-slate-500 hover:text-slate-300 transition-colors px-1"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirm(agent.id)}
                      className="text-xs text-slate-500 hover:text-red-400 transition-colors flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-white/5"
                    >
                      <Trash2 size={12} /> {t('agents.deleteBtn')}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setModalOpen(false)} />
          <div className="relative w-full max-w-lg mx-4 card p-6 animate-msg-in max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-white">
                {editingId ? t('agents.editTitle') : t('agents.createTitle')}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-500 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/5"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  {t('agents.formName')} <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder={t('agents.formNamePlaceholder')}
                  className="w-full bg-white/5 text-white border border-white/10 rounded-xl px-4 py-2.5 text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500/40 focus:ring-2 focus:ring-violet-500/10 transition-all"
                />
              </div>

              {/* Emoji */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  {t('agents.formEmoji')}
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {PRESET_EMOJIS.map((emoji) => (
                    <button
                      key={emoji}
                      onClick={() => setForm({ ...form, emoji })}
                      className={`w-9 h-9 rounded-lg flex items-center justify-center text-lg transition-all ${
                        form.emoji === emoji
                          ? 'bg-violet-500/20 border border-violet-500/40 scale-110'
                          : 'bg-white/5 border border-transparent hover:bg-white/10'
                      }`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  {t('agents.formDescription')}
                </label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder={t('agents.formDescPlaceholder')}
                  className="w-full bg-white/5 text-white border border-white/10 rounded-xl px-4 py-2.5 text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500/40 focus:ring-2 focus:ring-violet-500/10 transition-all"
                />
              </div>

              {/* System Prompt */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  {t('agents.formPrompt')} <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={form.system_prompt}
                  onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                  placeholder={t('agents.formPromptPlaceholder')}
                  rows={6}
                  className="w-full bg-white/5 text-white border border-white/10 rounded-xl px-4 py-2.5 text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500/40 focus:ring-2 focus:ring-violet-500/10 transition-all resize-y"
                />
              </div>

              {/* Color */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  {t('agents.formColor')}
                </label>
                <div className="flex flex-wrap gap-2">
                  {PRESET_COLORS.map((color) => (
                    <button
                      key={color}
                      onClick={() => setForm({ ...form, color })}
                      className={`w-8 h-8 rounded-lg transition-all ${
                        form.color === color ? 'ring-2 ring-white/40 scale-110' : 'hover:scale-105'
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                  <input
                    type="color"
                    value={form.color}
                    onChange={(e) => setForm({ ...form, color: e.target.value })}
                    className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border border-white/10"
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-white/5">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-white hover:bg-white/5 transition-all"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim() || !form.system_prompt.trim()}
                className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:from-slate-800 disabled:to-slate-800 text-white px-5 py-2 rounded-xl text-sm font-medium transition-all shadow-lg shadow-violet-500/15 disabled:shadow-none flex items-center gap-2"
              >
                {saving && <Loader2 size={14} className="animate-spin" />}
                {t('common.save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
