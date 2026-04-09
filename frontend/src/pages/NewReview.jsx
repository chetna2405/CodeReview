import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Play, Shuffle, Shield, Brain, Bug, GitFork, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'

const taskIcons = {
  simple_review: Bug,
  logic_review: Brain,
  security_review: Shield,
  cross_file_review: GitFork,
}

const taskDescriptions = {
  simple_review: 'Obvious bugs: off-by-one, null checks, hardcoded secrets, typos',
  logic_review: 'Subtle logic errors: race conditions, timing attacks, resource leaks',
  security_review: 'OWASP Top-10: SQLi, RCE, auth bypass, SSTI, path traversal',
  cross_file_review: 'Cross-file dependency bugs spanning multiple files',
}

const taskDifficulty = {
  simple_review: { label: 'Easy', color: 'text-success bg-success/10 border-success/20' },
  logic_review: { label: 'Medium', color: 'text-warning bg-warning/10 border-warning/20' },
  security_review: { label: 'Hard', color: 'text-error bg-error/10 border-error/20' },
  cross_file_review: { label: 'Hard', color: 'text-error bg-error/10 border-error/20' },
}

export default function NewReview() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState([])
  const [selectedTask, setSelectedTask] = useState('simple_review')
  const [seed, setSeed] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getTasks()
      .then((data) => setTasks(data.tasks || []))
      .catch(() => {})
  }, [])

  const handleStartReview = async () => {
    setLoading(true)
    setError(null)
    try {
      const body = { task_id: selectedTask }
      if (seed) body.seed = parseInt(seed, 10)
      await api.resetEpisode(body)
      navigate('/review')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const taskIds = tasks.length > 0
    ? tasks.map((t) => (typeof t === 'string' ? t : t.id || t.task_id))
    : Object.keys(taskDescriptions)

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="mb-8">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl font-bold tracking-tight"
        >
          <span className="gradient-text">New Review Session</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-sm text-on-surface-variant mt-2"
        >
          Select a task category, configure your settings, and start a new AI code review episode.
        </motion.p>
      </div>

      {/* Task Selection Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {taskIds.map((taskId, i) => {
          const Icon = taskIcons[taskId] || Bug
          const diff = taskDifficulty[taskId] || taskDifficulty.simple_review
          const desc = taskDescriptions[taskId] || 'Code review scenario'
          const isSelected = selectedTask === taskId

          return (
            <motion.button
              key={taskId}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              onClick={() => setSelectedTask(taskId)}
              className={cn(
                'glass-card rounded-xl p-6 text-left transition-all duration-200',
                isSelected
                  ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/20'
                  : 'hover:border-outline-variant/40',
              )}
            >
              <div className="flex items-start gap-4">
                <div className={cn(
                  'w-11 h-11 rounded-lg flex items-center justify-center shrink-0',
                  isSelected ? 'bg-primary/20' : 'bg-surface-container-high',
                )}>
                  <Icon className={cn('w-5 h-5', isSelected ? 'text-primary' : 'text-on-surface-variant')} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <h3 className={cn(
                      'text-sm font-semibold',
                      isSelected ? 'text-primary' : 'text-on-surface',
                    )}>
                      {taskId}
                    </h3>
                    <span className={cn(
                      'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border',
                      diff.color,
                    )}>
                      {diff.label}
                    </span>
                  </div>
                  <p className="text-xs text-on-surface-variant leading-relaxed">{desc}</p>
                </div>
              </div>

              {/* Selected indicator */}
              {isSelected && (
                <motion.div
                  layoutId="task-selected"
                  className="mt-4 h-0.5 rounded-full bg-gradient-to-r from-primary to-secondary"
                />
              )}
            </motion.button>
          )
        })}
      </div>

      {/* Configuration */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="glass-card rounded-xl p-6 mb-6"
      >
        <h3 className="text-sm font-semibold text-on-surface mb-4">Configuration</h3>
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-[11px] font-medium text-on-surface-variant uppercase tracking-widest mb-2">
              Random Seed (optional)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                placeholder="e.g. 42"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                className="w-full px-3 py-2.5 rounded-lg bg-surface-container-low ghost-border text-sm text-on-surface placeholder:text-outline outline-none focus:border-outline-variant/60 focus:ring-1 focus:ring-primary/10 transition-all"
              />
              <button
                onClick={() => setSeed(Math.floor(Math.random() * 10000).toString())}
                className="p-2.5 rounded-lg bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors"
                title="Random seed"
              >
                <Shuffle className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Error */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 px-4 py-3 rounded-lg bg-error/10 border border-error/20 text-sm text-error"
        >
          {error}
        </motion.div>
      )}

      {/* Start Button */}
      <motion.button
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.5 }}
        onClick={handleStartReview}
        disabled={loading}
        className={cn(
          'flex items-center gap-3 px-8 py-3.5 rounded-xl gradient-btn text-sm font-semibold text-white transition-all',
          loading && 'opacity-60 cursor-not-allowed',
        )}
      >
        {loading ? (
          <>
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Starting Episode...
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            Start Review Session
          </>
        )}
      </motion.button>
    </motion.div>
  )
}
