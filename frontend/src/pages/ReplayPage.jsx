import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Play, MessageSquare, CheckCircle2, AlertOctagon, Zap, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'
import { useSettings } from '@/App'
import SeverityBadge from '@/components/review/SeverityBadge'

const actionColors = {
  add_comment: 'bg-info/15 text-info border-info/20',
  retract_comment: 'bg-danger/15 text-danger border-danger/20',
  stand_firm: 'bg-success/15 text-success border-success/20',
  escalate: 'bg-warning/15 text-warning border-warning/20',
  request_clarification: 'bg-accent/15 text-accent border-accent/20',
  finalize_review: 'bg-accent/20 text-accent border-accent/30',
  request_changes: 'bg-warning/20 text-warning border-warning/30',
  approve: 'bg-success/20 text-success border-success/30',
}

export default function ReplayPage() {
  const navigate = useNavigate()
  const { settings } = useSettings()
  const [replay, setReplay] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [inputId, setInputId] = useState('')

  const fetchReplay = (eid) => {
    if (!eid) return
    setLoading(true)
    api.getReplay(eid)
      .then(r => { setReplay(r); setError(null) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (settings.episodeId) {
      fetchReplay(settings.episodeId)
    } else {
      setLoading(false)
    }
  }, [settings.episodeId])

  const handleManualFetch = () => {
    if (inputId.trim()) fetchReplay(inputId.trim())
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
          <Play className="w-6 h-6 text-accent" />
          Episode Replay
        </h1>
        <p className="text-sm text-text-muted mt-1">Turn-by-turn replay of completed episodes.</p>
      </div>

      {/* Episode ID Input */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="surface-card p-4 mb-6"
      >
        <div className="flex gap-2 items-center">
          <input
            type="text"
            placeholder="Enter episode ID..."
            value={inputId || settings.episodeId || ''}
            onChange={e => setInputId(e.target.value)}
            className="flex-1 px-3 py-2 rounded-lg bg-bg-base border border-accent-border text-[12px] text-text-primary font-mono placeholder:text-text-dim outline-none focus:border-accent/40 transition-colors"
          />
          <button onClick={handleManualFetch} className="btn-primary text-[12px] px-4">
            Load Replay
          </button>
        </div>
      </motion.div>

      {error && (
        <div className="mb-4 p-3 rounded-xl bg-danger-dim border border-danger/20 text-[12px] text-danger">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!replay && !error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-20">
          <Play className="w-12 h-12 text-text-dim/20 mb-4" />
          <h2 className="text-lg font-semibold text-text-primary mb-2">No Replay Data</h2>
          <p className="text-sm text-text-muted text-center max-w-md">
            Complete an episode first, then view the turn-by-turn replay here.
          </p>
        </motion.div>
      )}

      {/* Timeline */}
      {replay && replay.turns && (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-6 top-0 bottom-0 w-px bg-accent-border/40" />

          <div className="space-y-3">
            {replay.turns.map((turn, i) => {
              const isTerminal = ['finalize_review', 'request_changes', 'approve'].includes(turn.action_type)
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className={cn(
                    'relative pl-14',
                    isTerminal && 'mb-2',
                  )}
                >
                  {/* Step number chip */}
                  <div className={cn(
                    'absolute left-3 w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold z-10 border',
                    isTerminal ? 'bg-accent/20 text-accent border-accent/40' : 'bg-bg-secondary text-text-muted border-subtle',
                  )}>
                    {turn.turn || i + 1}
                  </div>

                  <div className={cn(
                    'surface-card p-4',
                    isTerminal && 'border-accent/30 glow-accent',
                  )}>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      {/* Action badge */}
                      <span className={cn('badge border text-[10px]', actionColors[turn.action_type] || 'badge-info')}>
                        {turn.action_type?.replace(/_/g, ' ')}
                      </span>

                      {turn.severity && <SeverityBadge severity={turn.severity} />}
                      {turn.line_number && <span className="text-[10px] font-mono text-text-dim">L{turn.line_number}</span>}

                      <span className="ml-auto text-[11px] font-mono text-text-secondary tabular-nums">
                        reward: {(turn.reward || 0).toFixed(4)}
                      </span>
                    </div>

                    {turn.message && (
                      <p className="text-[12px] text-text-secondary leading-relaxed mb-2">{turn.message}</p>
                    )}

                    {/* Author response */}
                    {turn.author_response && (
                      <div className="mt-2 ml-3 pl-3 border-l-2 border-accent/20">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <User className="w-3 h-3 text-accent/60" />
                          <span className="text-[10px] font-medium text-accent/70">Author</span>
                        </div>
                        <p className="text-[11px] text-text-muted italic leading-relaxed">{turn.author_response}</p>
                      </div>
                    )}

                    {turn.is_done && (
                      <div className="flex items-center gap-1.5 mt-2 text-[10px] font-medium text-success">
                        <CheckCircle2 className="w-3 h-3" /> Episode Complete
                      </div>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}
    </motion.div>
  )
}
