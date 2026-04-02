import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex items-center justify-center h-screen bg-gradient-to-b from-slate-950 to-[#0a0e1a]">
      {/* Background decorative elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-80 h-80 bg-indigo-600/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 right-1/3 w-80 h-80 bg-purple-600/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 card p-10 text-center max-w-sm">
        <p className="text-6xl font-bold gradient-text mb-4">404</p>
        <p className="text-lg text-slate-400 mb-2">页面不存在</p>
        <p className="text-[11px] text-slate-600 mb-6">你访问的页面可能已被移除或从未存在</p>
        <Link
          to="/"
          className="inline-block bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all shadow-lg shadow-indigo-500/20"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
