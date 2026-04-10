import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Award, BarChart3, Target, AlertOctagon, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'

const scoreColor = (v) => {
  if (v >= 0.7) return 'text-success'
  if (v >= 0.4) return 'text-warning'
  return 'text-danger'
}

const barColor = (v) => {
  if (v >= 0.7) return 'bg-success'
  if (v >= 0.4) return 'bg-warning'
  return 'bg-danger'
}

const barBg = (v) => {
  if (v >= 0.7) return 'bg-success/10'
  if (v >= 0.4) return 'bg-warning/10'
  return 'bg-danger/10'
}

function ScoreBar({ label, value, delay = 0 }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      className="flex items-center gap-3"
    >
      <span className="text-[12px] text-text-muted w-40 shrink-0">{label}</span>
      <div className={cn('flex-1 h-3 rounded-full overflow-hidden', barBg(value || 0))}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, delay: delay + 0.2, ease: 'easeOut' }}
          className={cn('h-full rounded-full', barColor(value || 0))}
        />
      </div>
      <span className={cn('text-[13px] font-semibold tabular-nums w-14 text-right', scoreColor(value || 0))}>
        {(value || 0).toFixed(4)}
      </span>
    </motion.div>
  )
}

const verdictConfig = {
  finalize_review: { label: 'Finalized', class: 'badge-accent' },
  request_changes: { label: 'Changes Requested', class: 'badge-warning' },
  approve: { label: 'Approved', class: 'badge-success' },
  timeout: { label: 'Timeout', class: 'badge-critical' },
}

export default function GraderPage() {
  const navigate = useNavigate()
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getGrader()
      .then(r => { setResults(r); setError(null) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}
      </div>
    )
  }

  if (error || !results) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-20">
        <AlertOctagon className="w-12 h-12 text-text-dim/30 mb-4" />
        <h2 className="text-lg font-semibold text-text-primary mb-2">No Grader Results</h2>
        <p className="text-sm text-text-muted text-center max-w-md mb-6">
          {error || 'Complete an episode first, then view your results here.'}
        </p>
        <button onClick={() => navigate('/new-review')} className="btn-primary">
          Start Episode
        </button>
      </motion.div>
    )
  }

  const vCfg = verdictConfig[results.verdict] || { label: results.verdict, class: 'badge-info' }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary flex items-center gap-3">
          <Award className="w-6 h-6 text-accent" />
          Grader Results
        </h1>
        <p className="text-sm text-text-muted mt-1">Detailed breakdown of your code review performance.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Composite Score */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="surface-card p-8 text-center glow-accent lg:col-span-1"
        >
          <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">Composite Score</p>
          <p className={cn('text-5xl font-bold tabular-nums mb-2', scoreColor(results.composite_score))}>
            {(results.composite_score || 0).toFixed(4)}
          </p>
          <span className={cn('badge', vCfg.class)}>{vCfg.label}</span>
        </motion.div>

        {/* Issues Summary */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="surface-card p-6 lg:col-span-2"
        >
          <h3 className="text-[14px] font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-accent" /> Detection Summary
          </h3>
          <div className="grid grid-cols-3 gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-text-primary tabular-nums">{results.issues_found ?? 0}</p>
              <p className="text-[11px] text-text-muted mt-1">Issues Found</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-text-primary tabular-nums">{results.issues_total ?? 0}</p>
              <p className="text-[11px] text-text-muted mt-1">Total Issues</p>
            </div>
            <div className="text-center">
              <p className={cn('text-3xl font-bold tabular-nums', (results.false_positives || 0) > 0 ? 'text-danger' : 'text-success')}>
                {results.false_positives ?? 0}
              </p>
              <p className="text-[11px] text-text-muted mt-1">False Positives</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Score Components */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="surface-card p-6"
      >
        <h3 className="text-[14px] font-semibold text-text-primary mb-5 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-accent" /> Score Components
        </h3>
        <div className="space-y-4">
          <ScoreBar label="F1 Score (45%)" value={results.f1_score} delay={0.25} />
          <ScoreBar label="Precision" value={results.precision} delay={0.3} />
          <ScoreBar label="Recall" value={results.recall} delay={0.35} />
          <ScoreBar label="Severity Accuracy (25%)" value={results.severity_accuracy} delay={0.4} />
          <ScoreBar label="Comment Similarity (15%)" value={results.comment_similarity} delay={0.45} />
          <ScoreBar label="Message Quality (15%)" value={results.message_quality_score} delay={0.5} />
        </div>
      </motion.div>
    </motion.div>
  )
}
