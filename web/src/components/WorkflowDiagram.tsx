import React from 'react';
import type { MessageData } from '../types';

interface Stage {
  id: string;
  label: string;
  emoji: string;
  roles: string[];
}

const WORKFLOW_STAGES: Record<string, Stage[]> = {
  debate: [
    { id: 'open', label: '开场', emoji: '🎙️', roles: ['moderator'] },
    { id: 'propose', label: '提出观点', emoji: '💡', roles: ['idea', 'architect', 'coder'] },
    { id: 'challenge', label: '质疑讨论', emoji: '⚔️', roles: ['reviewer'] },
    { id: 'respond', label: '回应质疑', emoji: '💬', roles: ['architect', 'coder'] },
    { id: 'judge', label: '仲裁决策', emoji: '⚖️', roles: ['judge'] },
    { id: 'plan', label: '任务拆解', emoji: '📋', roles: ['planner'] },
  ],
  pair: [
    { id: 'design', label: '设计方向', emoji: '🏗️', roles: ['architect'] },
    { id: 'implement', label: '编码实现', emoji: '💻', roles: ['coder'] },
    { id: 'review', label: '代码审查', emoji: '🔍', roles: ['reviewer'] },
    { id: 'test', label: '测试验证', emoji: '🧪', roles: ['qa'] },
  ],
  redblue: [
    { id: 'blue-build', label: 'Blue 构建', emoji: '🔵', roles: ['idea', 'architect', 'coder'] },
    { id: 'red-attack', label: 'Red 攻击', emoji: '🔴', roles: ['reviewer', 'security', 'qa'] },
    { id: 'judge', label: '仲裁', emoji: '⚖️', roles: ['judge'] },
  ],
  spec: [
    { id: 'contract', label: '定义契约', emoji: '📝', roles: ['architect'] },
    { id: 'tests', label: '生成测试', emoji: '🧪', roles: ['qa'] },
    { id: 'implement', label: '实现代码', emoji: '💻', roles: ['coder'] },
    { id: 'verify', label: '审查验证', emoji: '🔍', roles: ['reviewer'] },
  ],
  tdd: [
    { id: 'write-test', label: '编写测试', emoji: '🧪', roles: ['qa'] },
    { id: 'implement', label: '实现代码', emoji: '💻', roles: ['coder'] },
    { id: 'refactor', label: '重构建议', emoji: '🔍', roles: ['reviewer'] },
  ],
};

function inferCurrentStage(mode: string, messages: MessageData[]): number {
  const stages = WORKFLOW_STAGES[mode] || WORKFLOW_STAGES['debate'];
  if (messages.length === 0) return 0;

  const lastRole = messages[messages.length - 1].agent_role?.toLowerCase();

  for (let i = stages.length - 1; i >= 0; i--) {
    if (stages[i].roles.includes(lastRole)) {
      return i;
    }
  }
  return 0;
}

interface WorkflowDiagramProps {
  mode: string;
  messages: MessageData[];
  loading: boolean;
}

export function WorkflowDiagram({ mode, messages, loading }: WorkflowDiagramProps) {
  const stages = WORKFLOW_STAGES[mode] || WORKFLOW_STAGES['debate'];
  const currentStage = inferCurrentStage(mode, messages);

  return (
    <div className="flex items-center justify-center gap-1 py-3 px-4 overflow-x-auto">
      {stages.map((stage, i) => (
        <React.Fragment key={stage.id}>
          {i > 0 && (
            <div
              className={`w-6 h-0.5 shrink-0 transition-colors duration-500 ${
                i <= currentStage ? 'bg-indigo-500/60' : 'bg-white/10'
              }`}
            />
          )}
          <div
            className={`
              flex flex-col items-center gap-1 shrink-0 transition-all duration-500
              ${i === currentStage ? 'scale-110' : i < currentStage ? 'opacity-70' : 'opacity-30'}
            `}
          >
            <div
              className={`
                w-10 h-10 rounded-xl flex items-center justify-center text-lg
                ${
                  i === currentStage
                    ? 'bg-indigo-500/20 border border-indigo-500/40 speaking'
                    : i < currentStage
                      ? 'bg-indigo-500/10 border border-indigo-500/20'
                      : 'bg-white/5 border border-white/10'
                }
              `}
            >
              {i < currentStage ? '✅' : stage.emoji}
            </div>
            <span
              className={`text-[10px] whitespace-nowrap ${
                i === currentStage ? 'text-indigo-300 font-semibold' : 'text-slate-600'
              }`}
            >
              {stage.label}
            </span>
          </div>
        </React.Fragment>
      ))}
      {loading && (
        <span className="ml-2 text-[10px] text-indigo-400/60 animate-pulse shrink-0">
          进行中…
        </span>
      )}
    </div>
  );
}
