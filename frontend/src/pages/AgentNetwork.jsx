import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shuffle, Shield, Brain, Bug, GitFork, Zap, Crosshair, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'

const taskConfigs = {
  simple_review: {
    icon: Bug, label: 'Simple Review', codename: 'Sector Alpha',
    risk: 'LOW', riskClass: 'badge-success',
    desc: 'Off-by-one errors, null checks, hardcoded secrets, and typos.',
  },
  logic_review: {
    icon: Brain, label: 'Logic Review', codename: 'Sector Bravo',
    risk: 'MEDIUM', riskClass: 'badge-warning',
    desc: 'Race conditions, timing attacks, and resource leaks.',
  },
  security_review: {
    icon: Shield, label: 'Security Review', codename: 'Sector Charlie',
    risk: 'HIGH', riskClass: 'badge-critical',
    desc: 'OWASP Top-10: SQLi, RCE, auth bypass, SSTI, path traversal.',
  },
  cross_file_review: {
    icon: GitFork, label: 'Cross-File Review', codename: 'Sector Delta',
    risk: 'HIGH', riskClass: 'badge-critical',
    desc: 'Cross-file dependency bugs spanning multiple source files.',
  },
}

export default function AgentNetwork() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState([])
  const [selectedTask, setSelectedTask] = useState('simple_review')
  const [seed, setSeed] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getTasks().then(d => setTasks(d.tasks || [])).catch(() => {})
  }, [])

  const handleDeploy = async () => {
    setLoading(true); setError(null)
    try {
      const body = { task_id: selectedTask }
      if (seed) body.seed = parseInt(seed, 10)
      await api.resetEpisode(body)
      navigate('/review')
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  const taskIds = tasks.length > 0 ? tasks.map(t => typeof t === 'string' ? t : t.id || t.task_id) : Object.keys(taskConfigs)

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Deploy Review Agent</h1>
        <p className="text-sm text-text-muted mt-1">Select a review sector, configure parameters, and deploy.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Task Selection */}
        <div className="lg:col-span-8 space-y-3">
          <p className="text-[11px] font-medium text-text-muted uppercase tracking-[0.12em] mb-1">Select Review Type</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {taskIds.map((taskId, i) => {
              const c = taskConfigs[taskId] || taskConfigs.simple_review
              const Icon = c.icon
              const sel = selectedTask === taskId
              return (
                <motion.button
                  key={taskId}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  onClick={() => setSelectedTask(taskId)}
                  data-demo-target={taskId}
                  className={cn(
                    'surface-card text-left p-5 cursor-pointer transition-all duration-200',
                    sel ? 'border-accent/40 glow-accent' : 'hover:border-accent-hover',
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center shrink-0', sel ? 'bg-accent/15' : 'bg-bg-secondary')}>
                      <Icon className={cn('w-5 h-5', sel ? 'text-accent' : 'text-text-dim')} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn('text-[13px] font-semibold', sel ? 'text-accent' : 'text-text-primary')}>{c.label}</span>
                        <span className={cn('badge', c.riskClass)}>{c.risk}</span>
                      </div>
                      <p className="text-[11px] text-text-dim mb-1">{c.codename}</p>
                      <p className="text-[12px] text-text-muted leading-relaxed">{c.desc}</p>
                    </div>
                  </div>
                </motion.button>
              )
            })}
          </div>
        </div>

        {/* Right: Config + Deploy */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="lg:col-span-4 space-y-4"
        >
          <div className="surface-card p-5">
            <p className="text-[11px] font-medium text-text-muted uppercase tracking-[0.12em] mb-3">Configuration</p>
            <label className="text-[12px] text-text-secondary font-medium mb-1.5 block">Random Seed</label>
            <div className="flex gap-2 mb-4">
              <input
                type="number" placeholder="Auto" value={seed}
                onChange={e => setSeed(e.target.value)}
                className="flex-1 px-3 py-2.5 rounded-lg bg-bg-base border border-accent-border text-[13px] text-text-primary placeholder:text-text-dim outline-none focus:border-accent/40 transition-colors"
              />
              <button onClick={() => setSeed(Math.floor(Math.random() * 10000).toString())} className="btn-secondary px-3">
                <Shuffle className="w-4 h-4" />
              </button>
            </div>

            {error && (
              <div className="mb-3 p-3 rounded-lg bg-danger-dim border border-danger/20 text-[12px] text-danger">{error}</div>
            )}

            <button onClick={handleDeploy} disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              {loading ? (
                <><div className="w-4 h-4 border-2 border-bg-base/30 border-t-bg-base rounded-full animate-spin" /> Deploying...</>
              ) : (
                <><Zap className="w-4 h-4" /> Deploy Agent</>
              )}
            </button>
          </div>

          {/* Mission Brief */}
          <div className="surface-card p-5">
            <p className="text-[11px] font-medium text-text-muted uppercase tracking-[0.12em] mb-3">Mission Brief</p>
            <div className="space-y-2 text-[12px]">
              <div className="flex justify-between"><span className="text-text-muted">Sector</span><span className="text-text-primary font-medium">{(taskConfigs[selectedTask] || taskConfigs.simple_review).codename}</span></div>
              <div className="flex justify-between"><span className="text-text-muted">Max Turns</span><span className="text-text-primary font-medium">10</span></div>
              <div className="flex justify-between"><span className="text-text-muted">Multi-Turn</span><span className="text-success font-medium">Enabled</span></div>
              <div className="flex justify-between"><span className="text-text-muted">Persona</span><span className="text-accent font-medium">Active</span></div>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}
