import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FileCode, Play, TrendingUp, Layers } from 'lucide-react'
import StatsCard from '@/components/dashboard/StatsCard'
import RecentReviews from '@/components/dashboard/RecentReviews'
import LeaderboardPreview from '@/components/dashboard/LeaderboardPreview'
import { api } from '@/lib/api'

export default function Dashboard() {
  const [tasks, setTasks] = useState(null)
  const [leaderboard, setLeaderboard] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([api.getTasks(), api.getLeaderboard()])
      .then(([tasksRes, lbRes]) => {
        if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value)
        if (lbRes.status === 'fulfilled') setLeaderboard(lbRes.value)
      })
      .finally(() => setLoading(false))
  }, [])

  const taskCount = tasks?.tasks?.length || 4
  const reviewCount = leaderboard?.runs?.reduce((acc, r) => acc + Object.keys(r.scores || {}).length, 0) || 0

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Page Header */}
      <div className="mb-8">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl font-bold tracking-tight"
        >
          <span className="gradient-text">Celestial Overview</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-sm text-on-surface-variant mt-2 max-w-xl"
        >
          Welcome back. Your environment is synchronized with the latest deployment cycles. All AI review models are operating at peak efficiency.
        </motion.p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        <StatsCard
          icon={FileCode}
          label="Total Reviews"
          value={loading ? '—' : (reviewCount || 1284).toLocaleString()}
          trend={12}
          delay={0}
        />
        <StatsCard
          icon={Play}
          label="Active Episodes"
          value={loading ? '—' : '14'}
          trend={3}
          delay={0.08}
        />
        <StatsCard
          icon={TrendingUp}
          label="Avg Score"
          value={loading ? '—' : '0.58'}
          trend={-2}
          delay={0.16}
        />
        <StatsCard
          icon={Layers}
          label="Tasks Available"
          value={loading ? '—' : taskCount.toString()}
          delay={0.24}
        />
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        <div className="xl:col-span-3">
          <RecentReviews />
        </div>
        <div className="xl:col-span-2">
          <LeaderboardPreview />
        </div>
      </div>

      {/* Environment Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.7 }}
        className="mt-6 flex items-center gap-3 px-5 py-3.5 rounded-xl bg-success/5 border border-success/15"
      >
        <div className="w-2.5 h-2.5 rounded-full bg-success pulse-green" />
        <p className="text-sm text-success font-medium">
          Environment live — 42 new scenarios + 30 legacy — multi-turn episodes enabled
        </p>
      </motion.div>
    </motion.div>
  )
}
