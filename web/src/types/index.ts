export interface MessageData {
  agent_role: string;
  msg_type: string;
  content: string;
  claim: string;
  evidence: string;
  risk: string;
  next_step: string;
}

export interface DecisionData {
  summary: string;
  chosen_option: string;
  reasoning: string;
  status: string;
}

export interface TaskData {
  objective: string;
  definition_of_done: string;
  assignee_roles: string[];
  status: string;
}

export interface DiscussResponse {
  success: boolean;
  thread_id: string;
  messages: MessageData[];
  decision: DecisionData | null;
  tasks: TaskData[];
  error: string;
}

export interface ThreadItem {
  id: string;
  topic: string;
  mode: string;
  status: string;
}

export interface ModeInfo {
  id: string;
  name: string;
  desc: string;
}

export interface MemoryItem {
  id: number;
  type: string;
  title: string;
  content: string;
  tags: string[];
  importance: number;
  created_at: string;
}

export interface MemorySummary {
  total: number;
  active: number;
  archived: number;
  by_type: Record<string, number>;
  by_importance: Record<string, number>;
  all_tags: string[];
  latest_at: string | null;
}

export const ROLE_CONFIG: Record<string, { emoji: string; color: string; label: string }> = {
  idea:       { emoji: '💡', color: '#facc15', label: 'Idea' },
  architect:  { emoji: '🏗️', color: '#60a5fa', label: 'Architect' },
  coder:      { emoji: '💻', color: '#4ade80', label: 'Coder' },
  reviewer:   { emoji: '🔍', color: '#f87171', label: 'Reviewer' },
  qa:         { emoji: '🧪', color: '#c084fc', label: 'QA' },
  security:   { emoji: '🔒', color: '#ef4444', label: 'Security' },
  perf:       { emoji: '⚡', color: '#22d3ee', label: 'Perf' },
  docs:       { emoji: '📝', color: '#e2e8f0', label: 'Docs' },
  planner:    { emoji: '📋', color: '#fbbf24', label: 'Planner' },
  moderator:  { emoji: '🎙️', color: '#06b6d4', label: 'Moderator' },
  judge:      { emoji: '⚖️', color: '#f8fafc', label: 'Judge' },
};
