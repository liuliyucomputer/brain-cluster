export interface TaskItem {
  id: string; title: string; assignee: string; status: string
  created_at: number; started_at: number | null; completed_at: number | null
  failures: number; heartbeat: number | null; worker_pid: number | null
  result: string | null; duration: number | null
}

export interface ActivityItem {
  task_id: string; title: string; assignee: string; status: string
  time: number; duration: number | null; result: string | null; failures: number
}

export interface PipelineStage { count: number; tasks: TaskItem[] }

export interface AgentDetail {
  total: number; active: number; last_heartbeat: number | null; done: number; failures: number
}

export interface ExtensionInfo {
  name: string; integrated: boolean; tools: string[]; verified: boolean
}

export interface MonitorData {
  agents: Record<string, any>
  health: { gateway_ok: boolean; ports_ok: number; score: number }
  memory: any
  pipeline: any
  recent_events: any[]
  services: any
  tasks_by_status: Record<string, number>
  timestamp: string
}

export interface ClusterStatsV2 {
  overview: { total: number; active: number; done: number; done_today: number; avg_duration: number }
  services: Record<string, boolean>
  agents: Record<string, AgentDetail>
  pipeline: Record<string, PipelineStage>
  activity: ActivityItem[]
  timeline: { created_24h: number; completed_24h: number; active_24h: number }
  letta_sync_files: number
  kanban: { by_status: Record<string, number>; by_agent: Record<string, number> }
  extensions: { lines: Record<string, ExtensionInfo>; updated: string | null } | null
}

const BASE = '/api'

export async function fetchStatsV2(): Promise<ClusterStatsV2> {
  const res = await fetch(`${BASE}/stats`); if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json()
}

export async function fetchMonitor(): Promise<MonitorData | null> {
  try { const res = await fetch(`${BASE}/monitor`); return res.ok ? res.json() : null } catch { return null }
}

// ── Eyes Tools ─────────────────────────────────────────────

export interface EyesTool {
  name: string; zh: string; category: string; stars: string
  status: string; desc: string; dir: string; color: string
}

export interface EyesCategory {
  zh: string; en: string
}

export interface EyesStatusLabel {
  zh: string; en: string; cls: string
}

export interface EyesToolsData {
  tools: EyesTool[]
  categories: Record<string, EyesCategory>
  status_labels: Record<string, EyesStatusLabel>
}

export async function fetchEyesTools(): Promise<EyesToolsData | null> {
  try { const res = await fetch(`${BASE}/eyes/tools`); return res.ok ? res.json() : null } catch { return null }
}

// ── Supreme Commander ──────────────────────────────────────

export interface CommanderStatus {
  status: string
  scan_count: number
  fixes_auto: number
  fixes_manual: number
  fixes_failed: number
  crisis_count: number
  crisis_mode: boolean
  last_scan: string | null
  agent_health: Record<string, boolean>
}

export async function fetchCommanderStatus(): Promise<CommanderStatus | null> {
  try { const res = await fetch(`${BASE}/commander/status`); return res.ok ? res.json() : null } catch { return null }
}

export async function commanderAction(action: 'scan' | 'fix' | 'status'): Promise<{success: boolean; message?: string; error?: string; output?: string} | null> {
  try {
    const res = await fetch(`${BASE}/commander/${action}`, { method: 'POST' })
    return res.ok ? res.json() : null
  } catch { return null }
}
