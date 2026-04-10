import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Settings, Save, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { useSettings } from '@/App'
import { cn } from '@/lib/utils'

export default function SettingsPage() {
  const { settings, setSettings } = useSettings()
  const [tasks, setTasks] = useState([])
  const [health, setHealth] = useState(null)
  const [localSettings, setLocalSettings] = useState({ ...settings })
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      api.getTasks().then(d => setTasks(d.tasks || [])),
      api.health().then(h => setHealth(h)),
    ]).finally(() => setLoading(false))
  }, [])

  const selectedTaskData = tasks.find(t => (t.id || t.task_id) === localSettings.taskId)

  const handleSave = () => {
    setSettings(localSettings)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary flex items-center gap-3">
          <Settings className="w-6 h-6 text-accent" />
          Settings
        </h1>
        <p className="text-sm text-text-muted mt-1">Configure episode parameters and review environment settings.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Configuration */}
        <div className="space-y-5">
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="surface-card p-6"
          >
            <h3 className="text-[14px] font-semibold text-text-primary mb-4">Episode Configuration</h3>

            {/* Task Selector */}
            <div className="mb-4">
              <label className="text-[12px] text-text-secondary font-medium mb-1.5 block">Task</label>
              <select
                value={localSettings.taskId}
                onChange={e => setLocalSettings(s => ({ ...s, taskId: e.target.value }))}
                className="w-full px-3 py-2.5 rounded-lg bg-bg-base border border-accent-border text-[13px] text-text-primary outline-none focus:border-accent/40 transition-colors"
              >
                {tasks.map(t => (
                  <option key={t.id || t.task_id} value={t.id || t.task_id}>
                    {(t.id || t.task_id)} — {t.difficulty}
                  </option>
                ))}
              </select>
            </div>

            {/* Seed */}
            <div className="mb-4">
              <label className="text-[12px] text-text-secondary font-medium mb-1.5 block">Random Seed</label>
              <input
                type="number"
                value={localSettings.seed}
                onChange={e => setLocalSettings(s => ({ ...s, seed: parseInt(e.target.value, 10) || 0 }))}
                className="w-full px-3 py-2.5 rounded-lg bg-bg-base border border-accent-border text-[13px] text-text-primary outline-none focus:border-accent/40 transition-colors"
              />
            </div>

            {/* Model Label */}
            <div className="mb-4">
              <label className="text-[12px] text-text-secondary font-medium mb-1.5 block">Model</label>
              <input
                type="text"
                value={localSettings.modelLabel}
                readOnly
                className="w-full px-3 py-2.5 rounded-lg bg-bg-secondary border border-accent-border text-[13px] text-text-muted outline-none cursor-not-allowed"
              />
            </div>

            {/* Max Steps (read-only) */}
            <div className="mb-5">
              <label className="text-[12px] text-text-secondary font-medium mb-1.5 block">Max Steps</label>
              <input
                type="number"
                value={selectedTaskData?.max_steps || 10}
                readOnly
                className="w-full px-3 py-2.5 rounded-lg bg-bg-secondary border border-accent-border text-[13px] text-text-muted outline-none cursor-not-allowed"
              />
            </div>

            <button onClick={handleSave} className="btn-primary w-full flex items-center justify-center gap-2">
              {saved ? (
                <><CheckCircle2 className="w-4 h-4" /> Saved!</>
              ) : (
                <><Save className="w-4 h-4" /> Save Settings</>
              )}
            </button>
          </motion.div>
        </div>

        {/* Right: Status */}
        <div className="space-y-5">
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="surface-card p-6"
          >
            <h3 className="text-[14px] font-semibold text-text-primary mb-4">Environment Status</h3>

            <div className="space-y-3 text-[13px]">
              {/* HF Token Status */}
              <div className="flex items-center justify-between py-2 border-b border-accent-border/30">
                <span className="text-text-muted">HF Token</span>
                {health?.hf_token_present ? (
                  <span className="badge badge-success flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3" /> Token present
                  </span>
                ) : (
                  <span className="badge badge-critical flex items-center gap-1.5">
                    <XCircle className="w-3 h-3" /> Token missing
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between py-2 border-b border-accent-border/30">
                <span className="text-text-muted">Status</span>
                <span className={cn('font-medium', health?.status === 'ok' ? 'text-success' : 'text-danger')}>
                  {health?.status || 'unknown'}
                </span>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-accent-border/30">
                <span className="text-text-muted">Uptime</span>
                <span className="text-text-primary font-mono text-[12px]">
                  {health?.uptime_seconds ? `${Math.round(health.uptime_seconds)}s` : '—'}
                </span>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-accent-border/30">
                <span className="text-text-muted">Episodes Started</span>
                <span className="text-text-primary font-medium">{health?.total_episodes_started ?? '—'}</span>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-accent-border/30">
                <span className="text-text-muted">Episodes Completed</span>
                <span className="text-text-primary font-medium">{health?.total_episodes_completed ?? '—'}</span>
              </div>

              <div className="flex items-center justify-between py-2">
                <span className="text-text-muted">Mean Score</span>
                <span className="text-accent font-semibold">
                  {health?.mean_composite_score != null ? health.mean_composite_score.toFixed(4) : '—'}
                </span>
              </div>
            </div>
          </motion.div>

          {/* Scenarios Loaded */}
          {health?.scenarios_loaded && (
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              className="surface-card p-6"
            >
              <h3 className="text-[14px] font-semibold text-text-primary mb-4">Scenarios Loaded</h3>
              <div className="space-y-2">
                {Object.entries(health.scenarios_loaded).map(([task, count]) => (
                  <div key={task} className="flex items-center justify-between text-[12px]">
                    <span className="text-text-muted font-mono">{task}</span>
                    <span className="badge badge-accent">{count}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
