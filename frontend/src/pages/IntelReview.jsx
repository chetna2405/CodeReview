import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  FileCode, MessageSquare, Send, CheckCircle2, AlertTriangle, ThumbsUp,
  Crosshair, HelpCircle, GitPullRequest, User
} from 'lucide-react'
import { cn } from '@/lib/utils'
import SeverityBadge from '@/components/review/SeverityBadge'
import { api } from '@/lib/api'
import { useSettings } from '@/App'

export default function IntelReview() {
  const navigate = useNavigate()
  const { settings, setSettings } = useSettings()
  const [state, setState] = useState(null)
  const [observation, setObservation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [commentForm, setCommentForm] = useState({ line_number: '', severity: 'major', message: '' })
  const [error, setError] = useState(null)

  useEffect(() => { loadState() }, [])

  const loadState = async () => {
    try {
      const s = await api.getState()
      setState(s)
      setLoading(false)
    } catch {
      setError(null)
      setLoading(false)
    }
  }

  const handleAction = async (action) => {
    setActionLoading(true); setError(null)
    try {
      const r = await api.step(action)
      setObservation(r)
      // Save episode_id to settings
      const eid = r?.metadata?.episode_id
      if (eid && eid !== settings.episodeId) {
        setSettings(prev => ({ ...prev, episodeId: eid }))
      }
      await loadState()
      // Auto-navigate to grader on terminal action
      if (r?.done) {
        setTimeout(() => navigate('/grader'), 1200)
      }
    } catch (e) { setError(e.message) }
    finally { setActionLoading(false) }
  }

  const handleAddComment = () => {
    if (!commentForm.line_number || !commentForm.message) return
    handleAction({
      action_type: 'add_comment',
      line_number: parseInt(commentForm.line_number, 10),
      severity: commentForm.severity,
      message: commentForm.message,
    })
    setCommentForm({ line_number: '', severity: 'major', message: '' })
  }

  const parseDiffLines = (t) => {
    if (!t) return []
    return t.split('\n').map((line, i) => ({
      number: i + 1, content: line,
      type: line.startsWith('+') ? 'added' : line.startsWith('-') ? 'removed' : line.startsWith('@@') ? 'meta' : 'context',
    }))
  }

  if (loading) return <div className="space-y-3">{[...Array(5)].map((_, i) => <div key={i} className="skeleton h-14 rounded-xl" />)}</div>

  const diffLines = parseDiffLines(state?.diff_text || observation?.diff_text)
  const isActive = state && !state.is_done
  const comments = state?.comments_so_far || observation?.existing_comments || []
  const authorResponses = state?.author_responses || observation?.author_responses || []

  // Empty state
  if (!state || (!state.task_id && !state.scenario_id)) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-20">
        <div className="w-20 h-20 rounded-2xl bg-accent-muted flex items-center justify-center mb-6">
          <ShieldIcon className="w-10 h-10 text-accent opacity-50" />
        </div>
        <h2 className="text-xl font-semibold text-text-primary mb-2">No Active Operations</h2>
        <p className="text-sm text-text-muted text-center max-w-md mb-6">
          Deploy your first review agent to begin analyzing pull requests and generating intelligence reports.
        </p>
        <button onClick={() => navigate('/new-review')} className="btn-primary flex items-center gap-2">
          <Crosshair className="w-4 h-4" /> Deploy Agent
        </button>
      </motion.div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Active Operations</h1>
          <div className="flex items-center gap-3 mt-1 text-[12px] text-text-muted">
            <span>Task: <span className="text-text-primary font-medium">{state.task_id || 'N/A'}</span></span>
            <span className="text-text-dim">·</span>
            <span>Turn {state.turn || 0}/{state.max_steps || 10}</span>
            <span className="text-text-dim">·</span>
            <span className={state.is_done ? 'text-success font-medium' : 'text-accent font-medium'}>
              {state.is_done ? 'Complete' : 'In Progress'}
            </span>
          </div>
        </div>
        {isActive && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleAction({ action_type: 'request_clarification', question: 'Could you clarify?' })}
              disabled={actionLoading}
              className="btn-secondary flex items-center gap-2 text-[12px]"
            >
              <HelpCircle className="w-3.5 h-3.5" /> Clarify
            </button>
            <button
              onClick={() => handleAction({ action_type: 'request_changes', reason: 'Issues found' })}
              disabled={actionLoading}
              className="btn-secondary flex items-center gap-2 text-[12px]"
            >
              <GitPullRequest className="w-3.5 h-3.5" /> Request Changes
            </button>
            <button
              onClick={() => handleAction({ action_type: 'finalize_review', reason: 'Review complete' })}
              disabled={actionLoading}
              className="btn-secondary flex items-center gap-2 text-[12px]"
            >
              <AlertTriangle className="w-3.5 h-3.5" /> Finalize
            </button>
            <button
              onClick={() => handleAction({ action_type: 'approve' })}
              disabled={actionLoading}
              className="btn-primary flex items-center gap-2 text-[12px]"
            >
              <ThumbsUp className="w-3.5 h-3.5" /> Approve
            </button>
          </div>
        )}
      </div>

      {error && <div className="mb-4 p-3 rounded-xl bg-danger-dim border border-danger/20 text-[12px] text-danger">{error}</div>}

      {/* PR Info */}
      {(observation?.pr_description || state?.pr_description) && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="surface-card p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <GitPullRequest className="w-3.5 h-3.5 text-accent" />
            <span className="text-[12px] font-medium text-text-primary">PR Description</span>
          </div>
          <p className="text-[12px] text-text-muted leading-relaxed">{observation?.pr_description || state?.pr_description}</p>
          {(observation?.commit_message || state?.commit_message) && (
            <p className="text-[11px] text-text-dim mt-2 font-mono">commit: {observation?.commit_message || state?.commit_message}</p>
          )}
        </motion.div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Diff */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="xl:col-span-8 surface-card flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-accent-border">
            <FileCode className="w-3.5 h-3.5 text-accent" />
            <span className="text-[12px] font-mono text-text-muted">{state?.file_path || observation?.file_path || 'diff_output.py'}</span>
          </div>
          <div className="flex-1 overflow-auto max-h-[520px]">
            {diffLines.length > 0 ? (
              <table className="w-full text-[12px] font-mono"><tbody>
                {diffLines.map(line => (
                  <tr key={line.number} className={cn('hover:bg-bg-hover/30 transition-colors', line.type === 'added' && 'diff-added', line.type === 'removed' && 'diff-removed', line.type === 'meta' && 'diff-meta')}>
                    <td className="select-none px-3 py-0 text-right w-12 text-text-dim/50 text-[10px]">{line.number}</td>
                    <td className="select-none px-1 py-0 w-5 text-center text-[10px]">
                      {line.type === 'added' && <span className="text-success">+</span>}
                      {line.type === 'removed' && <span className="text-danger">−</span>}
                    </td>
                    <td className="px-3 py-0.5 whitespace-pre-wrap break-all text-text-secondary">{line.content}</td>
                  </tr>
                ))}
              </tbody></table>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-text-dim">
                <FileCode className="w-10 h-10 mb-3 opacity-20" />
                <p className="text-[13px] font-medium text-text-muted">No diff available</p>
                <p className="text-[11px] text-text-dim mt-1">The operation will populate data here.</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Comment Panel */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="xl:col-span-4 space-y-4">
          {isActive && (
            <div className="surface-card p-5">
              <p className="text-[13px] font-semibold text-text-primary mb-3 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-accent" /> Add Finding
              </p>
              <div className="space-y-2.5">
                <div className="flex gap-2">
                  <input type="number" placeholder="Line" value={commentForm.line_number} onChange={e => setCommentForm(p => ({ ...p, line_number: e.target.value }))} className="w-20 px-3 py-2 rounded-lg bg-bg-base border border-accent-border text-[12px] text-text-primary placeholder:text-text-dim outline-none focus:border-accent/40 transition-colors" />
                  <select value={commentForm.severity} onChange={e => setCommentForm(p => ({ ...p, severity: e.target.value }))} className="flex-1 px-3 py-2 rounded-lg bg-bg-base border border-accent-border text-[12px] text-text-primary outline-none focus:border-accent/40 transition-colors">
                    <option value="critical">Critical</option><option value="major">Major</option><option value="minor">Minor</option><option value="nit">Nit</option>
                  </select>
                </div>
                <textarea placeholder="Describe the issue..." value={commentForm.message} onChange={e => setCommentForm(p => ({ ...p, message: e.target.value }))} rows={3} maxLength={500} className="w-full px-3 py-2 rounded-lg bg-bg-base border border-accent-border text-[12px] text-text-primary placeholder:text-text-dim outline-none resize-none focus:border-accent/40 transition-colors" />
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-text-dim">{commentForm.message.length}/500</span>
                </div>
                <button onClick={handleAddComment} disabled={actionLoading || !commentForm.line_number || !commentForm.message} className={cn('btn-primary w-full flex items-center justify-center gap-2', (!commentForm.line_number || !commentForm.message) && 'opacity-40 cursor-not-allowed')}>
                  <Send className="w-3.5 h-3.5" /> Submit
                </button>
              </div>
            </div>
          )}

          <div className="surface-card overflow-hidden">
            <div className="px-5 py-3 border-b border-accent-border">
              <p className="text-[13px] font-semibold text-text-primary">Findings ({comments.length})</p>
            </div>
            {comments.length > 0 ? (
              <div className="divide-y divide-accent-border/50 max-h-[400px] overflow-y-auto">
                {comments.map((c, i) => (
                  <div key={c.comment_id || i} className="px-5 py-3">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge severity={c.severity || 'major'} />
                      <span className="text-[10px] font-mono text-text-dim">Line {c.line_number}</span>
                      {c.comment_id && <span className="text-[9px] font-mono text-text-dim/50">#{c.comment_id}</span>}
                    </div>
                    <p className="text-[12px] text-text-secondary leading-relaxed">{c.message}</p>

                    {/* Author response bubble for this comment */}
                    {authorResponses[i] && (
                      <div className="mt-2 ml-3 pl-3 border-l-2 border-accent/20">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <User className="w-3 h-3 text-accent/60" />
                          <span className="text-[10px] font-medium text-accent/70">Author</span>
                        </div>
                        <p className="text-[11px] text-text-muted italic leading-relaxed">{authorResponses[i]}</p>
                      </div>
                    )}

                    {isActive && (
                      <div className="flex gap-3 mt-2">
                        <button onClick={() => handleAction({ action_type: 'stand_firm', comment_id: c.comment_id })} className="text-[10px] font-semibold text-success hover:underline">Stand Firm</button>
                        <button onClick={() => handleAction({ action_type: 'retract_comment', comment_id: c.comment_id })} className="text-[10px] font-semibold text-danger hover:underline">Retract</button>
                        <button onClick={() => handleAction({ action_type: 'escalate', comment_id: c.comment_id, severity: 'critical' })} className="text-[10px] font-semibold text-accent hover:underline">Escalate</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center py-10 text-text-dim">
                <MessageSquare className="w-6 h-6 mb-2 opacity-20" />
                <p className="text-[12px] text-text-muted">No findings yet</p>
                <p className="text-[11px] text-text-dim mt-0.5">Add comments to flag issues in the diff.</p>
              </div>
            )}
          </div>

          {state?.is_done && state?.final_score !== null && (
            <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="surface-card p-5 text-center glow-accent">
              <CheckCircle2 className="w-8 h-8 text-success mx-auto mb-2" />
              <p className="text-[13px] font-semibold text-text-primary mb-1">Mission Complete</p>
              <p className="text-3xl font-bold text-accent tabular-nums">{(state.final_score || 0).toFixed(4)}</p>
              <p className="text-[11px] text-text-dim mt-1">Composite Score</p>
              <button onClick={() => navigate('/grader')} className="btn-secondary mt-3 text-[12px]">
                View Grader Results →
              </button>
            </motion.div>
          )}
        </motion.div>
      </div>
    </motion.div>
  )
}

function ShieldIcon(props) {
  return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></svg>
}
