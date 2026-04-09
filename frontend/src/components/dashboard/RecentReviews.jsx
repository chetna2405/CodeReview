import { motion } from 'framer-motion'
import { ArrowRight, Shield, AlertTriangle, FileCode } from 'lucide-react'
import { cn } from '@/lib/utils'
import SeverityBadge from '@/components/review/SeverityBadge'

const mockReviews = [
  {
    id: 'pr-402',
    title: 'PR #402: Auth Middleware Refactor',
    difficulty: 'hard',
    score: 0.92,
    scenario: 'security_review',
    description: 'Potential privilege escalation path identified in the original ternary logic.',
    icon: Shield,
  },
  {
    id: 'pr-398',
    title: 'PR #398: Dashboard Responsive Grid',
    difficulty: 'medium',
    score: 0.74,
    scenario: 'logic_review',
    description: 'Race condition in viewport resize handler causes intermittent layout shifts.',
    icon: AlertTriangle,
  },
  {
    id: 'pr-385',
    title: 'PR #385: Update Logo Manifest',
    difficulty: 'easy',
    score: 0.99,
    scenario: 'simple_review',
    description: 'Unused variable and missing null check in asset loader.',
    icon: FileCode,
  },
]

const difficultyColors = {
  easy: 'text-success bg-success/10 border-success/20',
  medium: 'text-warning bg-warning/10 border-warning/20',
  hard: 'text-error bg-error/10 border-error/20',
}

export default function RecentReviews() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="glass-card rounded-xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-surface-container-high/50">
        <h3 className="text-sm font-semibold text-on-surface">Recent Analysis Sessions</h3>
        <button className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors">
          View Archive
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* List */}
      <div className="divide-y divide-outline-variant/10">
        {mockReviews.map((review, i) => (
          <motion.div
            key={review.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.4 + i * 0.1 }}
            className="flex items-start gap-4 px-6 py-4 hover:bg-surface-container/30 transition-colors cursor-pointer group"
          >
            {/* Icon */}
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
              <review.icon className="w-4.5 h-4.5 text-primary" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h4 className="text-sm font-semibold text-on-surface truncate group-hover:text-primary transition-colors">
                  {review.title}
                </h4>
                <span
                  className={cn(
                    'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0',
                    difficultyColors[review.difficulty]
                  )}
                >
                  {review.difficulty}
                </span>
              </div>
              <p className="text-xs text-on-surface-variant line-clamp-1">{review.description}</p>
            </div>

            {/* Score */}
            <div className="text-right shrink-0">
              <p className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider mb-0.5">
                Composite Score
              </p>
              <p className={cn(
                'text-lg font-bold tabular-nums',
                review.score >= 0.9 ? 'text-success' : review.score >= 0.7 ? 'text-primary' : 'text-warning'
              )}>
                {review.score.toFixed(2)}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
