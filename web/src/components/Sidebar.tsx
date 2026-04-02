import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { MessageSquare, History, Brain, Menu, X } from 'lucide-react';

const links = [
  { to: '/', icon: MessageSquare, label: '新讨论', desc: '发起多 Agent 讨论' },
  { to: '/history', icon: History, label: '历史记录', desc: '查看过往讨论' },
  { to: '/memory', icon: Brain, label: '项目记忆', desc: '知识库与决策' },
];

export function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setOpen(!open)}
        className="md:hidden fixed top-3 left-3 z-50 p-2 rounded-xl bg-slate-900 border border-white/10 text-slate-400 hover:text-white transition-colors"
      >
        {open ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Overlay */}
      {open && (
        <div className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-30 transition-opacity" onClick={() => setOpen(false)} />
      )}

      <aside className={
        'w-64 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-r border-white/5 flex flex-col h-screen shrink-0 ' +
        'fixed md:static z-40 transition-all duration-300 ease-out ' +
        (open ? 'translate-x-0 shadow-2xl shadow-black/50' : '-translate-x-full md:translate-x-0')
      }>
        {/* Logo */}
        <div className="p-5 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20">
              AC
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">Agent Company</h1>
              <p className="text-xs text-slate-500 font-medium">AI Collaboration Framework</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider px-3 py-2">Workspace</p>
          {links.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 relative ' +
                (isActive
                  ? 'bg-indigo-500/12 text-indigo-200 font-semibold nav-active-indicator shadow-md shadow-indigo-500/5'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200')
              }
            >
              {({ isActive }) => (
                <>
                  <div className={'w-7 h-7 rounded-xl flex items-center justify-center transition-colors ' +
                    (isActive ? 'bg-indigo-500/15' : 'bg-transparent')}>
                    <Icon size={18} strokeWidth={isActive ? 2.5 : 1.5} />
                  </div>
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Status + Version */}
        <div className="p-4 border-t border-white/5 space-y-3">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
            <span className="text-slate-500">GitHub Models · Connected</span>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-700">
            <span>Agent Company</span>
            <span className="px-1.5 py-0.5 rounded-lg bg-white/5 font-mono text-[11px]">v0.1.0</span>
          </div>
        </div>
      </aside>
    </>
  );
}
