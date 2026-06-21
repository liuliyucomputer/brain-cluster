import { motion } from 'framer-motion'

interface Extension {
  name: string; integrated: boolean; tools: string[]; verified: boolean
}

interface Props {
  extensions: Record<string, Extension> | null
}

const EXT_ZH: Record<string, [string, string]> = {
  skills:     ['CodeBuddy技能', '6个自动化技能：批量GitHub、财务分析、PPT生成、简历筛选、工作报告、小红书创作'],
  publisher:  ['发布管线', '小红书发布工具链 (xhs_publisher.py)，支持自动填表+手动点击发布'],
  connectors: ['21连接器', 'MCP协议连接器，覆盖腾讯文档/飞书/钉钉/企微/GitHub等21个平台'],
  agentteam:  ['Agent团队(12)', '12个协作角色：协调/委派/规划/集群/编排/观察/共识/反馈/综合/路由/质量/应急'],
  codewhale:  ['codeWhale', '代码执行器，处理编码任务和复杂计算'],
  finance:    ['金融自动化', '财务分析引擎，支持三张报表+50+比率+杜邦分析+趋势预测'],
}

export function ExtensionsPanel({ extensions }: Props) {
  if (!extensions || Object.keys(extensions).length === 0) {
    return <div className="surface-card p-4 text-center text-text-tertiary text-xs">暂无扩展数据</div>
  }

  const entries = Object.entries(extensions)
  const verified = entries.filter(([, e]) => e.verified).length

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">扩展模块 / Extensions</h2>
        <span className="text-2xs text-text-tertiary">{verified}/{entries.length} 已验证</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {entries.map(([key, ext], i) => {
          const zh = EXT_ZH[key] || [ext.name.replace('_', ' '), '']
          return (
            <motion.div
              key={key}
              className="rounded-lg border border-border-default bg-surface-0/40 p-3 hover:bg-surface-2/50 transition-colors cursor-default"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-text-primary">{zh[0]}</span>
                <span className={`text-2xs px-1.5 py-0.5 rounded ${
                  ext.verified ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                }`}>
                  {ext.verified ? '已验证' : '待接入'}
                </span>
              </div>
              {zh[1] && (
                <p className="text-2xs text-text-tertiary leading-relaxed mb-1.5">{zh[1]}</p>
              )}
              {ext.tools.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {ext.tools.slice(0, 3).map(t => (
                    <span key={t} className="text-2xs text-text-tertiary px-1 py-0.5 rounded bg-surface-2">{t}</span>
                  ))}
                  {ext.tools.length > 3 && (
                    <span className="text-2xs text-text-tertiary/50">+{ext.tools.length - 3}</span>
                  )}
                </div>
              )}
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
