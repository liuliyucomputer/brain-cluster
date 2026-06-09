import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface MemFile { label: string; name: string; path: string; size_kb: number; modified: string }
interface Category { key: string; zh: string; icon: string; color: string; desc: string; files: MemFile[] }

const CATEGORY_DEFS: Omit<Category, 'files'>[] = [
  { key: 'daily',       zh: '每日记忆', icon: '\ud83d\udcc5', color: '#6366f1', desc: '每日工作日志，自动追加不覆盖' },
  { key: 'project',     zh: '项目记忆', icon: '\ud83e\udde0', color: '#10b981', desc: '工作区长期记忆和约定' },
  { key: 'maintenance', zh: '维护日志', icon: '\ud83d\udd27', color: '#f59e0b', desc: '系统修复记录和维护历史' },
  { key: 'user',        zh: '用户记忆', icon: '\ud83d\udc64', color: '#a855f7', desc: '跨项目的个人习惯和偏好' },
]

export function MemoryManager() {
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [activeCat, setActiveCat] = useState<string | null>(null)

  const fetchList = useCallback(async () => {
    try {
      const r = await fetch('/api/memory/list'); const d = await r.json()
      const files: MemFile[] = d.files || []
      const cats: Category[] = CATEGORY_DEFS.map(def => ({ ...def, files: [] as MemFile[] }))
      for (const f of files) {
        if (f.name.match(/^\d{4}-\d{2}-\d{2}\.md$/)) cats[0].files.push(f)
        else if (f.name === 'MAINTENANCE_LOG.md') cats[2].files.push(f)
        else if (f.label === '项目记忆') cats[1].files.push(f)
        else if (f.label === '用户记忆') cats[3].files.push(f)
      }
      cats[1].files.push(...files.filter(f => !cats.some(c => c.files.includes(f))))
      setCategories(cats.filter(c => c.files.length > 0))
    } catch {}
  }, [])

  useEffect(() => { fetchList() }, [fetchList])

  const readFile = async (path: string) => {
    setSelectedFile(path); setStatus(null)
    try {
      const r = await fetch(`/api/memory/read?path=${encodeURIComponent(path)}`)
      const d = await r.json()
      if (d.ok) { setContent(d.content); setEditing(false) }
      else setStatus(`读取失败: ${d.msg}`)
    } catch { setStatus('网络错误') }
  }

  const saveEdit = async () => {
    if (!selectedFile) return
    setStatus('保存中...')
    try {
      const r = await fetch('/api/memory/update', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content: editContent }),
      })
      const d = await r.json()
      if (d.ok) { setContent(editContent); setEditing(false); setStatus('已保存') }
      else setStatus(`保存失败: ${d.msg}`)
    } catch { setStatus('网络错误') }
  }

  const deleteFile = async (path: string) => {
    const name = path.split(/[/\\]/).pop() || path
    if (!confirm(`确定删除 ${name}？此操作不可恢复。`)) return
    setStatus('删除中...')
    try {
      const r = await fetch('/api/memory/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path }) })
      const d = await r.json()
      if (d.ok) { setSelectedFile(null); setContent(''); fetchList(); setStatus('已删除') }
      else setStatus(`删除失败: ${d.msg}`)
    } catch { setStatus('网络错误') }
  }

  const totalFiles = categories.reduce((s, c) => s + c.files.length, 0)
  const activeCategory = categories.find(c => c.key === activeCat)

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">记忆管理</h2>
        <div className="flex items-center gap-2">
          <span className="text-2xs text-text-tertiary">{totalFiles} 文件</span>
          <span className="text-2xs text-text-tertiary/50">{categories.length} 分类</span>
        </div>
      </div>

      {/* Category cards */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        {categories.map(cat => {
          const isActive = activeCat === cat.key
          return (
            <motion.div
              key={cat.key}
              className={`rounded-lg border cursor-pointer transition-all p-3 ${
                isActive
                  ? 'border-border-accent bg-surface-2'
                  : 'border-border-default bg-surface-0/40 hover:bg-surface-2/50'
              }`}
              style={{ borderLeftColor: isActive ? cat.color : 'transparent', borderLeftWidth: '2px' }}
              onClick={() => { setActiveCat(isActive ? null : cat.key); setSelectedFile(null) }}
              whileHover={{ scale: 1.01 }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">{cat.icon}</span>
                  <span className="text-xs font-medium text-text-primary">{cat.zh}</span>
                </div>
                <span className="text-2xs px-1.5 py-0.5 rounded" style={{ backgroundColor: `${cat.color}15`, color: `${cat.color}cc` }}>
                  {cat.files.length}
                </span>
              </div>
              <p className="text-2xs text-text-tertiary leading-relaxed">{cat.desc}</p>
            </motion.div>
          )
        })}
      </div>

      {/* File list for active category */}
      <AnimatePresence>
        {activeCat && !selectedFile && activeCategory && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border-default pt-2 mb-2">
              <div className="text-2xs text-text-tertiary mb-1.5 px-1">
                {activeCategory.zh} ({activeCategory.files.length} 文件)
              </div>
              <div className="space-y-0.5 max-h-[200px] overflow-y-auto scrollbar-thin">
                {activeCategory.files.map(f => (
                  <div
                    key={f.path}
                    onClick={() => readFile(f.path)}
                    className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-surface-2 cursor-pointer group"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs">{'\ud83d\udcc4'}</span>
                      <span className="text-xs text-text-secondary truncate">{f.name}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 opacity-50 group-hover:opacity-100 transition-opacity">
                      <span className="text-2xs text-text-tertiary">{f.size_kb}KB</span>
                      <span className="text-2xs text-text-tertiary/50">{f.modified.slice(5, 16)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File viewer/editor */}
      <AnimatePresence>
        {selectedFile && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="border-t border-border-default pt-2">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <button onClick={() => setSelectedFile(null)} className="text-xs text-text-tertiary hover:text-text-secondary transition-colors">
                  &larr; 返回
                </button>
                <span className="text-xs text-text-secondary truncate max-w-[160px]">{selectedFile.split(/[/\\]/).pop()}</span>
              </div>
              <div className="flex items-center gap-1">
                {!editing ? (
                  <>
                    <button onClick={() => { setEditContent(content); setEditing(true) }}
                      className="text-2xs text-brand-indigo/70 hover:text-brand-indigo px-2 py-0.5 rounded border border-brand-indigo/15 hover:border-brand-indigo/30 transition-colors">
                      编辑
                    </button>
                    <button onClick={() => deleteFile(selectedFile)}
                      className="text-2xs text-danger/60 hover:text-danger px-2 py-0.5 rounded border border-danger/15 hover:border-danger/30 transition-colors">
                      删除
                    </button>
                  </>
                ) : (
                  <>
                    <button onClick={saveEdit}
                      className="text-2xs text-success/60 hover:text-success px-2 py-0.5 rounded border border-success/15 hover:border-success/30 transition-colors">
                      保存
                    </button>
                    <button onClick={() => setEditing(false)}
                      className="text-2xs text-text-tertiary hover:text-text-secondary px-2 py-0.5 rounded border border-border-default hover:border-border-hover transition-colors">
                      取消
                    </button>
                  </>
                )}
              </div>
            </div>

            {editing ? (
              <textarea
                value={editContent}
                onChange={e => setEditContent(e.target.value)}
                className="w-full bg-surface-0 border border-border-default rounded-lg p-3 font-mono text-xs text-text-secondary leading-relaxed focus:outline-none focus:border-brand-indigo/40 focus:ring-1 focus:ring-brand-indigo/20 resize-y transition-all"
                rows={12}
              />
            ) : (
              <pre className="bg-surface-0 rounded-lg p-3 font-mono text-xs text-text-secondary leading-relaxed max-h-[280px] overflow-y-auto scrollbar-thin whitespace-pre-wrap">
                {content.slice(0, 4000)}
                {content.length > 4000 && <span className="text-text-tertiary/50">{'\n'}... 共 {content.length} 字符</span>}
              </pre>
            )}

            {status && (
              <div className={`text-2xs px-2 py-1 mt-1.5 rounded ${
                status.includes('失败') || status.includes('错误')
                  ? 'bg-danger/10 text-danger'
                  : status.includes('已')
                    ? 'bg-success/10 text-success'
                    : 'bg-surface-2 text-text-tertiary'
              }`}>{status}</div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
