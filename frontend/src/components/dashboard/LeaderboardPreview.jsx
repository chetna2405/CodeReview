import { motion } from 'framer-motion'
import { Trophy, TrendingUp, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'

const mockLeaderboard = [
  { rank: 1, model: 'GPT-4o-Celestial', reviews: 982, mean: 0.96, delta: +0.04 },
  { rank: 2, model: 'Claude-3.5-Sonnet', reviews: 845, mean: 0.91, delta: +0.02 },
  { rank: 3, model: 'Qwen2.5-72B', reviews: 721, mean: 0.88, delta: -0.01 },
  { rank: 4, model: 'Gemini-2.0-Flash', reviews: 654, mean: 0.85, delta: +0.06 },
]

const trophyColors = ['text-warning', 'text-on-surface-variant', 'text-[#cd7f32]']

export default function LeaderboardPreview() {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
      className="glass-card rounded-xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-surface-container-high/50">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-warning" />
          <h3 className="text-sm font-semibold text-on-surface">Leaderboard</h3>
        </div>
        <button
          onClick={() => navigate('/metrics')}
          className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
        >
          Full Board
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Entries */}
      <div className="px-6 py-3 space-y-2">
        {mockLeaderboard.map((entry, i) => (
          <motion.div
            key={entry.model}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.6 + i * 0.08 }}
            className="flex items-center gap-3 py-2.5 group"
          >
            {/* Rank */}
            <div className="w-7 text-center">
              {entry.rank <= 3 ? (
                <Trophy className={cn('w-4 h-4 mx-auto', trophyColors[entry.rank - 1])} />
              ) : (
                <span className="text-xs font-bold text-outline tabular-nums">{entry.rank}</span>
              )}
            </div>

            {/* Avatar + Name */}
            <div className="flex items-center gap-2.5 flex-1 min-w-0">
              <div className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0',
                i === 0 ? 'bg-gradient-to-br from-primary to-secondary text-white'
                  : 'bg-surface-container-highest text-on-surface-variant'
              )}>
                {entry.model.charAt(0)}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-on-surface truncate">{entry.model}</p>
                <p className="text-[10px] text-on-surface-variant">{entry.reviews} Reviews</p>
              </div>
            </div>

            {/* Score + Delta */}
            <div className="text-right shrink-0">
              <p className="text-sm font-bold text-on-surface tabular-nums">{entry.mean.toFixed(2)}</p>
              <p className={cn(
                'text-[10px] font-semibold tabular-nums',
                entry.delta >= 0 ? 'text-success' : 'text-error'
              )}>
                {entry.delta >= 0 ? '↑' : '↓'} {Math.abs(entry.delta).toFixed(2)}
              </p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Your Rank */}
      <div className="mx-6 mb-4 mt-2 px-4 py-3 rounded-lg bg-primary/5 border border-primary/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary" />
            <span className="text-xs font-semibold text-primary">Your Rank</span>
          </div>
          <span className="text-xs font-bold text-on-surface">Position #12 (Top 5%)</span>
        </div>
      </div>
    </motion.div>
  )
}
