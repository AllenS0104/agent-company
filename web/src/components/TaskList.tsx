import type { TaskData } from '../types';
import { ROLE_CONFIG } from '../types';

export function TaskList({ tasks }: { tasks: TaskData[] }) {
  if (tasks.length === 0) return null;

  return (
    <div className="my-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <span className="text-xl">📋</span>
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Task Plan</h3>
          <p className="text-xs text-slate-500 font-medium">{tasks.length} tasks generated</p>
        </div>
      </div>

      <div className="space-y-2">
        {tasks.map((task, i) => (
          <div key={`${task.objective}-${i}`} className="card card-hover p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 flex-1">
                <span className="w-6 h-6 rounded-full bg-white/8 flex items-center justify-center text-xs font-bold text-slate-400 shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{task.objective}</p>
                  {task.definition_of_done && (
                    <p className="text-xs text-slate-500 mt-1">✅ {task.definition_of_done}</p>
                  )}
                </div>
              </div>
              <span className={'chip shrink-0 ' +
                (task.status === 'done' ? 'bg-emerald-500/10 text-emerald-400' :
                 task.status === 'in_progress' ? 'bg-blue-500/10 text-blue-400' :
                 'bg-white/5 text-slate-500')
              }>
                {task.status}
              </span>
            </div>
            <div className="flex gap-1.5 mt-2.5 ml-9">
              {task.assignee_roles.map(role => {
                const c = ROLE_CONFIG[role];
                return (
                  <span key={role} className="chip"
                    style={{ backgroundColor: (c?.color ?? '#666') + '10', color: c?.color ?? '#999', border: '1px solid ' + (c?.color ?? '#666') + '15' }}>
                    {c?.emoji} {role}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
