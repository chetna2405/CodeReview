import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  FileCode,
  MessageSquare,
  Send,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldAlert,
  ArrowUpCircle,
  RotateCcw,
  ThumbsUp,
} from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { cn } from '@/lib/utils'
import SeverityBadge from '@/components/review/SeverityBadge'
import { api } from '@/lib/api'

// Custom dark theme for syntax highlighting matching our design
const codeTheme = {
  'pre[class*="language-"]': {
    background: 'transparent',
    color: '#e5e3ff',
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    fontSize: '13px',
    lineHeight: '1.7',
    margin: 0,
    padding: 0,
    overflow: 'auto',
  },
  'code[class*="language-"]': {
    background: 'transparent',
    color: '#e5e3ff',
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    fontSize: '13px',
  },
  comment: { color: '#74738c' },
  keyword: { color: '#a3a6ff' },
  string: { color: '#ffa5d9' },
  function: { color: '#ff67ad' },
  number: { color: '#6ee7b7' },
  operator: { color: '#aaa8c3' },
  punctuation: { color: '#74738c' },
  'class-name': { color: '#a3a6ff' },
  builtin: { color: '#ef81c4' },
  boolean: { color: '#6ee7b7' },
}

export default function ReviewDetail() {
  const [state, setState] = useState(null)
  const [observation, setObservation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [commentForm, setCommentForm] = useState({ line_number: '', severity: 'major', message: '' })
  const [error, setError] = useState(null)

  useEffect(() => {
    loadState()
  }, [])

  const loadState = async () => {
    try {
      const s = await api.getState()
      setState(s)
      setLoading(false)
    } catch (err) {
      setError('No active episode. Start a new review from the New Review page.')
      setLoading(false)
    }
  }

  const handleAction = async (action) => {
    setActionLoading(true)
    setError(null)
    try {
      const result = await api.step(action)
      setObservation(result)
      await loadState()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
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

  const handleFinalize = () => {
    handleAction({ action_type: 'finalize_review', reason: 'Review complete' })
  }

  const handleApprove = () => {
    handleAction({ action_type: 'approve' })
  }

  // Parse diff lines for rendering
  const parseDiffLines = (diffText) => {
    if (!diffText) return []
    return diffText.split('\n').map((line, i) => ({
      number: i + 1,
      content: line,
      type: line.startsWith('+') ? 'added' : line.startsWith('-') ? 'removed' : line.startsWith('@@') ? 'meta' : 'context',
    }))
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="skeleton h-16 rounded-xl" />
        ))}
      </div>
    )
  }

  const diffLines = parseDiffLines(state?.diff_text || observation?.diff_text)
  const isActive = state && !state.is_done
  const comments = state?.comments_so_far || observation?.existing_comments || []

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-2xl font-bold tracking-tight"
          >
            <span className="gradient-text">Review Detail</span>
          </motion.h1>
          {state && (
            <div className="flex items-center gap-3 mt-2">
              <span className="text-xs font-mono text-on-surface-variant">
                Task: {state.task_id || 'N/A'}
              </span>
              <span className="text-outline-variant">·</span>
              <span className="text-xs text-on-surface-variant">
                Turn {state.turn || 0} / {state.max_steps || 10}
              </span>
              <span className="text-outline-variant">·</span>
              <span className={cn(
                'text-xs font-semibold',
                state.is_done ? 'text-success' : 'text-primary'
              )}>
                {state.is_done ? 'Completed' : 'In Progress'}
              </span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        {isActive && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleFinalize}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-on-surface-variant ghost-border hover:border-warning/40 hover:text-warning transition-all"
            >
              <AlertTriangle className="w-4 h-4" />
              Finalize Review
            </button>
            <button
              onClick={handleApprove}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg gradient-btn text-sm font-semibold text-white"
            >
              <ThumbsUp className="w-4 h-4" />
              Approve
            </button>
          </div>
        )}
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-6 px-4 py-3 rounded-lg bg-error/10 border border-error/20 text-sm text-error"
        >
          {error}
        </motion.div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Diff Viewer — 2 cols */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="xl:col-span-2 glass-card rounded-xl overflow-hidden"
        >
          <div className="flex items-center gap-2 px-5 py-3 bg-surface-container-high/50">
            <FileCode className="w-4 h-4 text-primary" />
            <span className="text-xs font-mono text-on-surface">
              {state?.file_path || observation?.file_path || 'diff_output.py'}
            </span>
          </div>

          <div className="overflow-auto max-h-[600px]">
            {diffLines.length > 0 ? (
              <table className="w-full text-[13px] font-mono">
                <tbody>
                  {diffLines.map((line) => (
                    <tr
                      key={line.number}
                      className={cn(
                        'hover:bg-surface-container/50 transition-colors',
                        line.type === 'added' && 'diff-added',
                        line.type === 'removed' && 'diff-removed',
                        line.type === 'meta' && 'bg-primary/5',
                      )}
                    >
                      <td className="select-none px-3 py-0 text-right w-12 text-outline-variant/60 text-[11px]">
                        {line.number}
                      </td>
                      <td className="select-none px-1 py-0 w-5 text-center">
                        {line.type === 'added' && <span className="text-secondary text-xs">+</span>}
                        {line.type === 'removed' && <span className="text-error text-xs">−</span>}
                      </td>
                      <td className="px-3 py-0.5 whitespace-pre-wrap break-all">
                        <span className={cn(
                          line.type === 'meta' && 'text-primary font-semibold',
                          line.type === 'context' && 'text-on-surface-variant',
                        )}>
                          {line.content}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
                <FileCode className="w-12 h-12 mb-4 opacity-30" />
                <p className="text-sm font-medium">No active diff</p>
                <p className="text-xs mt-1">Start a new review to see the code diff here</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Comment Panel — 1 col */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          {/* Add Comment Form */}
          {isActive && (
            <div className="glass-card rounded-xl p-5">
              <h3 className="text-sm font-semibold text-on-surface mb-4 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-primary" />
                Add Comment
              </h3>

              <div className="space-y-3">
                <div className="flex gap-3">
                  <input
                    type="number"
                    placeholder="Line #"
                    value={commentForm.line_number}
                    onChange={(e) => setCommentForm(prev => ({ ...prev, line_number: e.target.value }))}
                    className="w-20 px-3 py-2 rounded-lg bg-surface-container-low ghost-border text-sm text-on-surface placeholder:text-outline outline-none focus:border-outline-variant/60 transition-all"
                  />
                  <select
                    value={commentForm.severity}
                    onChange={(e) => setCommentForm(prev => ({ ...prev, severity: e.target.value }))}
                    className="flex-1 px-3 py-2 rounded-lg bg-surface-container-low ghost-border text-sm text-on-surface outline-none focus:border-outline-variant/60 transition-all"
                  >
                    <option value="critical">Critical</option>
                    <option value="major">Major</option>
                    <option value="minor">Minor</option>
                    <option value="nit">Nit</option>
                  </select>
                </div>

                <textarea
                  placeholder="Describe the issue..."
                  value={commentForm.message}
                  onChange={(e) => setCommentForm(prev => ({ ...prev, message: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container-low ghost-border text-sm text-on-surface placeholder:text-outline outline-none resize-none focus:border-outline-variant/60 transition-all"
                />

                <button
                  onClick={handleAddComment}
                  disabled={actionLoading || !commentForm.line_number || !commentForm.message}
                  className={cn(
                    'w-full flex items-center justify-center gap-2 py-2.5 rounded-lg gradient-btn text-sm font-semibold text-white',
                    (!commentForm.line_number || !commentForm.message) && 'opacity-40 cursor-not-allowed',
                  )}
                >
                  <Send className="w-4 h-4" />
                  Submit Comment
                </button>
              </div>
            </div>
          )}

          {/* Existing Comments */}
          <div className="glass-card rounded-xl overflow-hidden">
            <div className="px-5 py-3 bg-surface-container-high/50">
              <h3 className="text-sm font-semibold text-on-surface">
                Comments ({comments.length})
              </h3>
            </div>

            {comments.length > 0 ? (
              <div className="divide-y divide-outline-variant/10">
                {comments.map((comment, i) => (
                  <motion.div
                    key={comment.comment_id || i}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="px-5 py-3.5"
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <SeverityBadge severity={comment.severity || 'major'} />
                      <span className="text-[10px] font-mono text-outline">
                        Line {comment.line_number}
                      </span>
                      {comment.comment_id && (
                        <span className="text-[10px] font-mono text-outline-variant">
                          #{comment.comment_id}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      {comment.message}
                    </p>

                    {/* Action buttons */}
                    {isActive && (
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={() => handleAction({ action_type: 'stand_firm', comment_id: comment.comment_id })}
                          className="text-[10px] font-medium text-success hover:text-success/80 transition-colors"
                        >
                          Stand Firm
                        </button>
                        <button
                          onClick={() => handleAction({ action_type: 'retract_comment', comment_id: comment.comment_id })}
                          className="text-[10px] font-medium text-error hover:text-error/80 transition-colors"
                        >
                          Retract
                        </button>
                        <button
                          onClick={() => handleAction({ action_type: 'escalate', comment_id: comment.comment_id, severity: 'critical' })}
                          className="text-[10px] font-medium text-warning hover:text-warning/80 transition-colors"
                        >
                          Escalate
                        </button>
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-on-surface-variant">
                <MessageSquare className="w-8 h-8 mb-3 opacity-30" />
                <p className="text-xs">No comments yet</p>
              </div>
            )}
          </div>

          {/* Score if done */}
          {state?.is_done && state?.final_score !== null && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-card rounded-xl p-5 text-center"
            >
              <CheckCircle2 className="w-8 h-8 text-success mx-auto mb-3" />
              <p className="text-sm font-semibold text-on-surface mb-1">Review Complete</p>
              <p className="text-3xl font-bold text-success tabular-nums">
                {(state.final_score || 0).toFixed(4)}
              </p>
              <p className="text-[10px] text-on-surface-variant mt-1 uppercase tracking-widest">
                Composite Score
              </p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </motion.div>
  )
}
