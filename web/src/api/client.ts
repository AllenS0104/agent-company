import type { DiscussResponse, ThreadItem, MessageData, ModeInfo, MemoryItem, MemorySummary } from '../types';

const BASE = '/api';

async function fetchJson<T = unknown>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export async function postDiscuss(body: {
  topic: string;
  mode?: string;
  max_rounds?: number;
  extended_agents?: boolean;
  provider?: string;
  model?: string;
}): Promise<DiscussResponse> {
  return fetchJson<DiscussResponse>(`${BASE}/discuss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function getThreads(): Promise<ThreadItem[]> {
  return fetchJson<ThreadItem[]>(`${BASE}/threads`);
}

export async function getThreadMessages(threadId: string): Promise<MessageData[]> {
  return fetchJson<MessageData[]>(`${BASE}/threads/${threadId}/messages`);
}

export async function getModes(): Promise<ModeInfo[]> {
  const data = await fetchJson<{ modes: ModeInfo[] }>(`${BASE}/modes`);
  return data.modes;
}

export async function getProviders(): Promise<string[]> {
  const data = await fetchJson<{ providers: string[] }>(`${BASE}/providers`);
  return data.providers;
}

export async function getRoles(): Promise<string[]> {
  const data = await fetchJson<{ roles: string[] }>(`${BASE}/roles`);
  return data.roles;
}

export async function exportThread(threadId: string): Promise<Blob> {
  const res = await fetch(`${BASE}/threads/${threadId}/export`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.blob();
}

export async function getConfig(): Promise<any> {
  return fetchJson(`${BASE}/config`);
}

export async function updateConfig(cfg: Record<string, string>): Promise<any> {
  return fetchJson(`${BASE}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cfg),
  });
}

export async function getMemories(keyword = '', limit = 20, tags: string[] = []): Promise<MemoryItem[]> {
  const params = new URLSearchParams();
  if (keyword) params.set('keyword', keyword);
  if (tags.length > 0) params.set('tags', tags.join(','));
  params.set('limit', String(limit));
  const data = await fetchJson<{ memories: MemoryItem[] }>(`${BASE}/memory?${params}`);
  return data.memories;
}

export async function getMemorySummary(): Promise<MemorySummary> {
  return fetchJson<MemorySummary>(`${BASE}/memory/summary`);
}

export async function getRelatedMemories(topic: string, limit = 5): Promise<MemoryItem[]> {
  const params = new URLSearchParams({ topic, limit: String(limit) });
  const data = await fetchJson<{ memories: MemoryItem[] }>(`${BASE}/memory/related?${params}`);
  return data.memories;
}

export async function requestDeviceCode(): Promise<{
  device_code: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
}> {
  return fetchJson(`${BASE}/auth/github/device-code`, { method: 'POST' });
}

export async function pollGitHubToken(deviceCode: string): Promise<{
  status: 'success' | 'pending' | 'slow_down' | 'expired' | 'error';
  access_token?: string;
  user?: { login: string; avatar_url: string; name: string };
  interval?: number;
  error?: string;
}> {
  return fetchJson(`${BASE}/auth/github/poll-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_code: deviceCode }),
  });
}
