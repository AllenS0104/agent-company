export function LoadingScreen() {
  return (
    <div className="flex items-center justify-center h-screen bg-gradient-to-b from-slate-950 to-[#0a0e1a]">
      <div className="text-center">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 border border-indigo-500/20 flex items-center justify-center mx-auto mb-5 animate-float">
          <span className="text-3xl">🏢</span>
        </div>
        <h3 className="text-xl font-bold gradient-text mb-3">Agent Company</h3>
        <div className="flex items-center justify-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse-dot" />
          <div className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse-dot" style={{ animationDelay: '0.3s' }} />
          <div className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-pulse-dot" style={{ animationDelay: '0.6s' }} />
        </div>
        <p className="text-xs text-slate-600 mt-3">正在连接...</p>
      </div>
    </div>
  );
}
