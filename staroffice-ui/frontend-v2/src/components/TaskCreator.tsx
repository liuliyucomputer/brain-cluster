import { useState } from 'react'

const AGENTS = [
  { key: 'strategist', zh: '策略' },
  { key: 'executor-a', zh: '文案' },
  { key: 'executor-b', zh: 'PPT' },
  { key: 'executor-c', zh: '数据' },
  { key: 'monitor', zh: '监控' },
  { key: 'reviewer-strict', zh: '严审' },
  { key: 'reviewer-creative', zh: '创审' },
  { key: 'arbiter', zh: '仲裁' },
  { key: 'learner', zh: '学习' },
]

export function TaskCreator() {
  const [title, setTitle] = useState('')
  const [assignee, setAssignee] = useState('strategist')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  const submit = async () => {
    if (!title.trim()) return
    setSending(true)
    setResult(null)
    try {
      const r = await fetch('/api/tasks/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), assignee, body: body.trim() }),
      })
      const d = await r.json()
      if (d.ok) {
        setResult(`\u2713 已创建: ${d.task_id} \u2192 ${d.assignee}`)
        setTitle(''); setBody('')
      } else {
        setResult(`\u2717 ${d.msg}`)
      }
    } catch {
      setResult('\u2717 网络错误')
    }
    setSending(false)
  }

  return (
    <div className="surface-card p-4">
      <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider mb-3">发布任务 / Create Task</h2>

      <div className="space-y-2">
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="任务标题..."
          className="w-full bg-surface-0 border border-border-default rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-brand-indigo/40 focus:ring-1 focus:ring-brand-indigo/20 transition-all"
          onKeyDown={e => e.key === 'Enter' && submit()}
        />

        <div className="flex gap-2">
          <select
            value={assignee}
            onChange={e => setAssignee(e.target.value)}
            className="bg-surface-0 border border-border-default rounded-lg px-3 py-2 text-xs text-text-secondary focus:outline-none focus:border-brand-indigo/40"
          >
            {AGENTS.map(a => <option key={a.key} value={a.key}>{a.zh} ({a.key})</option>)}
          </select>

          <button
            onClick={submit}
            disabled={sending || !title.trim()}
            className="flex-1 rounded-lg px-4 py-2 text-xs font-medium bg-brand-indigo/15 text-brand-indigo border border-brand-indigo/20 hover:bg-brand-indigo/25 disabled:opacity-30 transition-colors"
          >
            {sending ? '创建中...' : '发布任务'}
          </button>
        </div>

        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          placeholder="任务详细描述（可选）..."
          rows={2}
          className="w-full bg-surface-0 border border-border-default rounded-lg px-3 py-2 text-xs text-text-secondary placeholder:text-text-tertiary focus:outline-none focus:border-brand-indigo/40 focus:ring-1 focus:ring-brand-indigo/20 resize-none transition-all"
        />

        {result && (
          <div className={`text-2xs px-2 py-1.5 rounded ${result.startsWith('\u2713') ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
            {result}
          </div>
        )}
      </div>
    </div>
  )
}
