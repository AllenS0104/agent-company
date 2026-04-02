import { ROLE_CONFIG, type MessageData } from '../types';

export function MessageBubble({ msg }: { msg: MessageData }) {
  const config = ROLE_CONFIG[msg.agent_role] ?? { emoji: '🤖', color: '#94a3b8', label: msg.agent_role };
  const isSystem = msg.msg_type === 'system';

  if (isSystem) {
    return (
      <div className="my-4 flex justify-center">
        <div className="card px-5 py-1.5 rounded-full text-[11px] text-slate-500 max-w-lg text-center italic">
          <span className="text-slate-600 mr-1.5">—</span>
          {msg.content}
          <span className="text-slate-600 ml-1.5">—</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4 flex gap-3 group hover:bg-white/[0.02] rounded-xl p-3 -mx-3 transition-all duration-200">
      {/* Avatar */}
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center text-xl shrink-0 shadow-md transition-transform duration-200 group-hover:scale-105 speaking"
        style={{
          background: 'linear-gradient(135deg, ' + config.color + '10, ' + config.color + '22)',
          border: '1px solid ' + config.color + '30',
          boxShadow: '0 4px 12px ' + config.color + '08',
        }}
      >
        {config.emoji}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="chip text-xs" style={{ backgroundColor: config.color + '10', color: config.color, border: '1px solid ' + config.color + '18' }}>
            {config.emoji} {config.label.toUpperCase()}
          </span>
          <span className="chip bg-white/5 text-slate-600">
            {msg.msg_type}
          </span>
        </div>

        <div className="text-[15px] text-slate-300 whitespace-pre-wrap leading-relaxed">
          {msg.content}
        </div>

        {/* Evidence block */}
        {(msg.claim || msg.evidence || msg.risk || msg.next_step) && (
          <div className="mt-3 text-[13px] space-y-1.5 pl-4 border-l rounded-r-xl bg-white/[0.02] py-2.5 pr-3"
            style={{ borderColor: config.color + '40' }}>
            {msg.claim && <p className="text-slate-400"><span className="text-slate-500 font-medium">📌 Claim:</span> {msg.claim}</p>}
            {msg.evidence && <p className="text-slate-400"><span className="text-slate-500 font-medium">📊 Evidence:</span> {msg.evidence}</p>}
            {msg.risk && <p className="text-amber-400/70"><span className="text-slate-500 font-medium">⚠️ Risk:</span> {msg.risk}</p>}
            {msg.next_step && <p className="text-slate-400"><span className="text-slate-500 font-medium">➡️ Next:</span> {msg.next_step}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
