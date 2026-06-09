import { motion } from 'framer-motion'

interface EventItem { title: string; agent: string; status: string }

interface Props { events: EventItem[] }

const STATUS_STYLE: Record<string, [string, string]> = {
  done: ['#4ade80', '#4ade8020'], archived: ['#a78bfa', '#a78bfa20'],
  in_progress: ['#fbbf24', '#fbbf2420'], failed: ['#f87171', '#f8717120'],
  pending: ['#9ca3af', '#9ca3af20'], review: ['#c084fc', '#c084fc20'],
  ready: ['#60a5fa', '#60a5fa20'],
}
const STATUS_ZH: Record<string, string> = {
  done: '完成', archived: '已归档', in_progress: '执行中', failed: '失败', pending: '待处理', review: '审查中', ready: '就绪',
}
const AGENT_ZH: Record<string, string> = {
  strategist: '策略', 'executor-a': '文案', 'executor-b': 'PPT', 'executor-c': '数据',
  monitor: '监控', 'reviewer-strict': '严审', 'reviewer-creative': '创审', arbiter: '仲裁', learner: '学习',
}

export function EventStream({ events }: Props) {
  if (events.length === 0) return (
    <div className="rounded-xl p-4 text-center text-white/25 text-xs" style={{ background: 'hsl(240,6%,10%)', border: '1px solid rgba(255,255,255,0.05)' }}>暂无事件</div>
  )
  return (
    <div className="rounded-xl p-4" style={{ background: 'hsl(240,6%,10%)', border: '1px solid rgba(255,255,255,0.05)' }}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[11px] font-semibold text-white/50 tracking-wider">实时任务事件</h2>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" style={{ boxShadow: '0 0 6px rgba(74,222,128,0.5)', animation: 'status-pulse 2s infinite' }} />
          <span className="text-[10px] text-white/35">{events.length}</span>
        </div>
      </div>
      <div className="space-y-0 max-h-[320px] overflow-y-auto scrollbar-thin">
        {events.map((evt, i) => {
          const [color, bg] = STATUS_STYLE[evt.status] || ['#9ca3af', '#9ca3af20']
          const zhStatus = STATUS_ZH[evt.status] || evt.status
          const zhAgent = AGENT_ZH[evt.agent] || evt.agent
          return (
            <div key={i} className="flex items-center gap-2 py-2 border-b border-white/[0.03] last:border-0">
              <span className="text-[9px] text-white/15 tabular-nums w-6 text-right">#{events.length - i}</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded font-medium" style={{ background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.55)' }}>{zhAgent}</span>
              <span className="text-[10px] text-white/60 truncate flex-1">{evt.title}</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded font-medium shrink-0" style={{ background: bg, color }}>{zhStatus}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
