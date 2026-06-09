import { useState, useEffect, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { fetchCommanderStatus, commanderAction, type CommanderStatus } from '../lib/api'

const EMPTY_STATUS: CommanderStatus = {
  status: 'standby',
  scan_count: 0,
  fixes_auto: 0,
  fixes_manual: 0,
  fixes_failed: 0,
  crisis_count: 0,
  crisis_mode: false,
  last_scan: null,
  agent_health: {},
}

export function SupremeCommander() {
  const [status, setStatus] = useState<CommanderStatus>(EMPTY_STATUS)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await fetchCommanderStatus()
      if (data) {
        setStatus(data)
      }
    } catch (e) {
      console.error('Failed to fetch commander status:', e)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 5000)
    return () => {
      clearInterval(id)
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [fetchStatus])

  const handleAction = async (action: 'scan' | 'fix' | 'status') => {
    if (loading) return
    setLoading(true)
    setResult({ message: '执行中...', type: 'info' })

    try {
      const data = await commanderAction(action)

      if (data && data.success) {
        const msg = data.output
          ? `${data.message || '执行成功'}\n${data.output}`
          : (data.message || '执行成功')
        setResult({ message: msg, type: 'success' })
        // 刷新状态
        timeoutRef.current = setTimeout(fetchStatus, 1000)
      } else {
        setResult({ message: data?.error || data?.message || '执行失败（无详细错误）', type: 'error' })
      }
    } catch (e: any) {
      setResult({ message: `请求失败: ${e.message}`, type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const isActive = status.status === 'active'
  const isCrisis = status.crisis_mode

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="surface-card"
    >
      <div className="flex items-center gap-2 mb-4">
        <span className="text-lg">👑</span>
        <h3 className="text-sm font-semibold">至高指挥官 (v3.0)</h3>
        <span
          className={`ml-auto text-2xs px-2 py-0.5 rounded-full font-medium ${
            isCrisis
              ? 'bg-danger/10 text-danger animate-pulse'
              : isActive
              ? 'bg-success/10 text-success'
              : 'bg-text-tertiary/10 text-text-tertiary'
          }`}
        >
          {isCrisis ? '危机模式' : isActive ? '运行中' : '待机'}
        </span>
      </div>

      {/* Status Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-surface-1 rounded-lg p-3">
          <div className="text-2xs text-text-tertiary mb-1">扫描次数</div>
          <div className="text-lg font-bold text-brand-indigo">{status.scan_count}</div>
        </div>
        <div className="bg-surface-1 rounded-lg p-3">
          <div className="text-2xs text-text-tertiary mb-1">自动修复</div>
          <div className="text-lg font-bold text-success">{status.fixes_auto}</div>
        </div>
        <div className="bg-surface-1 rounded-lg p-3">
          <div className="text-2xs text-text-tertiary mb-1">人工确认</div>
          <div className="text-lg font-bold text-warning">{status.fixes_manual}</div>
        </div>
        <div className="bg-surface-1 rounded-lg p-3">
          <div className="text-2xs text-text-tertiary mb-1">危机次数</div>
          <div className={`text-lg font-bold ${status.crisis_count > 0 ? 'text-danger' : 'text-text-tertiary'}`}>
            {status.crisis_count}
          </div>
        </div>
      </div>

      {/* Agent Health */}
      {Object.keys(status.agent_health).length > 0 && (
        <div className="mb-4">
          <div className="text-2xs text-text-tertiary mb-2">Agent 健康</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(status.agent_health).map(([name, isUp]) => (
              <span
                key={name}
                className={`text-2xs px-2 py-1 rounded-full ${
                  isUp ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
                }`}
              >
                {isUp ? '●' : '○'} {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Control Buttons */}
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => handleAction('scan')}
          disabled={loading}
          className="flex-1 px-3 py-2 bg-brand-indigo/10 hover:bg-brand-indigo/20 text-brand-indigo rounded-lg text-2xs font-medium transition-all disabled:opacity-50"
        >
          {loading ? '⏳' : '🔍'} 立即扫描
        </button>
        <button
          onClick={() => handleAction('fix')}
          disabled={loading}
          className="flex-1 px-3 py-2 bg-success/10 hover:bg-success/20 text-success rounded-lg text-2xs font-medium transition-all disabled:opacity-50"
        >
          {loading ? '⏳' : '🔧'} 安全修复
        </button>
        <button
          onClick={() => handleAction('status')}
          disabled={loading}
          className="flex-1 px-3 py-2 bg-surface-2 hover:bg-surface-3 text-text-secondary rounded-lg text-2xs font-medium transition-all disabled:opacity-50"
        >
          {loading ? '⏳' : '📊'} 刷新状态
        </button>
      </div>

      {/* Result Message */}
      {result && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className={`text-2xs px-3 py-2 rounded-lg ${
            result.type === 'success'
              ? 'bg-success/10 text-success'
              : result.type === 'error'
              ? 'bg-danger/10 text-danger'
              : 'bg-brand-indigo/10 text-brand-indigo'
          }`}
        >
          {result.message}
        </motion.div>
      )}

      {/* Last Scan */}
      {status.last_scan && (
        <div className="text-2xs text-text-tertiary mt-3 text-right">
          最后扫描: {new Date(status.last_scan).toLocaleString('zh-CN')}
        </div>
      )}
    </motion.div>
  )
}
