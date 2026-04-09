import { motion } from 'framer-motion'

const sampleLogs = [
  { time: '14:33', agent: 'GPT-4o', action: 'reviewed', target: 'auth.py', severity: 'warning' },
  { time: '14:28', agent: 'Claude', action: 'merged', target: 'PR #398', severity: 'success' },
  { time: '14:25', agent: 'Gemini', action: 'scanned', target: 'routes.ts', severity: 'info' },
  { time: '14:22', agent: 'Qwen', action: 'flagged', target: 'middleware', severity: 'critical' },
  { time: '14:19', agent: 'GPT-4o', action: 'resolved', target: 'db.js', severity: 'success' },
]

const dotColors = {
  critical: 'bg-danger',
  warning: 'bg-warning',
  success: 'bg-success',
  info: 'bg-info',
}

export default function ActivityFeed({ title = 'Live Stream', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="surface-card flex flex-col overflow-hidden"
    >
      <div className="flex items-center justify-between px-6 py-5 border-b border-subtle">
        <div>
          <h3 className="text-[14px] font-medium text-text-primary">{title}</h3>
        </div>
        <span className="badge badge-accent bg-accent/10">Active</span>
      </div>

      <div className="p-2">
        {sampleLogs.map((log, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + 0.1 + i * 0.05 }}
            className="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-bg-elevated transition-colors"
          >
            <div className={`w-2 h-2 rounded-full ${dotColors[log.severity]}`} />
            <div className="flex-1 text-[13px]">
              <span className="font-medium text-text-primary">{log.agent}</span>
              <span className="text-text-muted mx-1.5">{log.action}</span>
              <span className="text-text-primary">{log.target}</span>
            </div>
            <span className="text-[12px] text-text-dim font-mono">{log.time}</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
