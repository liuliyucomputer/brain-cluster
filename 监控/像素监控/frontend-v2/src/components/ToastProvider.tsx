import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export interface Toast {
  id: string
  title: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  duration?: number // ms, 0 = sticky
}

interface ToastContextType {
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

let toastId = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((t: Omit<Toast, 'id'>) => {
    const id = `toast-${++toastId}`
    setToasts(prev => [...prev, { ...t, id }])
    const dur = t.duration ?? (t.type === 'error' ? 0 : 3000)
    if (dur > 0) setTimeout(() => removeToast(id), dur)
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}

      {/* Toast container — fixed top-right */}
      <div className="fixed top-14 right-4 z-[200] flex flex-col gap-2 max-w-[360px] pointer-events-none">
        <AnimatePresence>
          {toasts.map(toast => {
            const colorMap = {
              info:    { bg: 'var(--brand-indigo)', dot: '#6366f1' },
              success: { bg: 'var(--success)',        dot: '#10b981' },
              warning: { bg: 'var(--warning)',        dot: '#f59e0b' },
              error:   { bg: 'var(--danger)',         dot: '#ef4444' },
            }
            const c = colorMap[toast.type]
            return (
              <motion.div
                key={toast.id}
                className="pointer-events-auto surface-card p-3 flex items-start gap-3 cursor-pointer"
                style={{ boxShadow: `0 0 0 1px hsl(${c.bg} / 0.15), 0 4px 20px rgba(0,0,0,0.5), inset 0 0.5px 0 rgba(255,255,255,0.04)` }}
                initial={{ opacity: 0, x: 60, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, scale: 0.95 }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                onClick={() => removeToast(toast.id)}
              >
                <div
                  className="w-1.5 h-1.5 rounded-full mt-0.5 shrink-0"
                  style={{ backgroundColor: c.dot, boxShadow: `0 0 6px ${c.dot}80` }}
                />
                <div className="min-w-0">
                  <div className="text-xs font-medium text-text-primary">{toast.title}</div>
                  {toast.message && <div className="text-2xs text-text-secondary mt-0.5">{toast.message}</div>}
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
