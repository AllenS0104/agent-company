import type { DecisionData } from '../types';

export function DecisionCard({ decision }: { decision: DecisionData }) {
  return (
    <div className="my-6 relative overflow-hidden rounded-xl animate-stamp">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/8 via-purple-600/8 to-pink-600/8" />
      <div className="absolute inset-0 border border-indigo-400/12 rounded-xl" />

      <div className="relative p-7">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <span className="text-xl">⚖️</span>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Final Decision</h3>
            <p className="text-xs text-slate-500 font-medium">Arbitration Complete</p>
          </div>
          <span className={'chip ml-auto ' +
            (decision.status === 'approved'
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15'
              : 'bg-amber-500/10 text-amber-400 border border-amber-500/15')
          }>
            {decision.status}
          </span>
        </div>

        <div className="space-y-3 text-sm">
          <div className="bg-white/[0.04] rounded-xl p-5 border border-white/5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Summary</p>
            <p className="text-white font-medium">{decision.summary}</p>
          </div>

          {decision.chosen_option && (
            <div className="bg-white/[0.04] rounded-xl p-5 border border-white/5">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Chosen Option</p>
              <p className="text-emerald-300">{decision.chosen_option}</p>
            </div>
          )}

          {decision.reasoning && (
            <div className="bg-white/[0.04] rounded-xl p-5 border border-white/5">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Reasoning</p>
              <p className="text-slate-300 whitespace-pre-wrap">{decision.reasoning}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
