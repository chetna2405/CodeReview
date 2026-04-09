import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3,
  Trophy,
  TrendingUp,
  TrendingDown,
  Award,
  Zap,
  Target,
  ShieldCheck,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, AreaChart, Area, Cell,
} from 'recharts'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'

const trophyColors = ['text-warning', 'text-on-surface-variant', 'text-[#cd7f32]']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card rounded-lg px-3 py-2 text-xs">
      <p className="font-semibold text-on-surface mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="tabular-nums">
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
        </p>
      ))}
    </div>
  )
}

export default function Metrics() {
  const [leaderboard, setLeaderboard] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getLeaderboard()
      .then((data) => setLeaderboard(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const runs = leaderboard?.runs || []

  // Bar chart data — scores per task for each model
  const barData = runs.slice(0, 6).map((run) => ({
    model: run.model?.split('-').slice(0, 2).join('-') || 'Unknown',
    simple: run.scores?.simple_review || 0,
    logic: run.scores?.logic_review || 0,
    security: run.scores?.security_review || 0,
    mean: run.mean || 0,
  }))

  // Area chart — score trend (using index as time)
  const trendData = runs.map((run, i) => ({
    index: i + 1,
    mean: run.mean || 0,
    model: run.model || 'Run ' + (i + 1),
  }))

  // Radar chart — category scores from top model
  const topRun = runs[0]
  const radarData = topRun?.category_scores
    ? Object.entries(topRun.category_scores)
        .filter(([_, v]) => v !== null)
        .map(([key, value]) => ({
          subject: key.charAt(0).toUpperCase() + key.slice(1),
          score: value,
          fullMark: 1,
        }))
    : [
        { subject: 'Security', score: 0.61, fullMark: 1 },
        { subject: 'Logic', score: 0.55, fullMark: 1 },
        { subject: 'Style', score: 0.72, fullMark: 1 },
        { subject: 'Cross-File', score: 0.38, fullMark: 1 },
      ]

  // Quick stat cards
  const quickStats = [
    { icon: Trophy, label: 'Top Model', value: topRun?.model || 'N/A', color: 'text-warning' },
    { icon: Target, label: 'Best Score', value: topRun?.mean?.toFixed(4) || '—', color: 'text-success' },
    { icon: Zap, label: 'Total Runs', value: runs.length.toString(), color: 'text-primary' },
    { icon: ShieldCheck, label: 'Avg Security', value: topRun?.category_scores?.security?.toFixed(2) || '—', color: 'text-secondary' },
  ]

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton h-20 rounded-xl" />
        ))}
      </div>
    )
  }

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
          <span className="gradient-text">Metrics & Leaderboard</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-sm text-on-surface-variant mt-2"
        >
          Performance analytics and model comparison across all review categories.
        </motion.p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {quickStats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="glass-card rounded-xl p-5"
          >
            <stat.icon className={cn('w-5 h-5 mb-3', stat.color)} />
            <p className="text-[10px] font-medium text-on-surface-variant uppercase tracking-widest mb-1">
              {stat.label}
            </p>
            <p className="text-lg font-bold text-on-surface truncate">{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
        {/* Score Trend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="xl:col-span-2 glass-card rounded-xl overflow-hidden"
        >
          <div className="px-6 py-4 bg-surface-container-high/50">
            <h3 className="text-sm font-semibold text-on-surface flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Performance by Category
            </h3>
          </div>
          <div className="p-6 h-80">
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} barGap={2}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(70,70,93,0.15)" />
                  <XAxis
                    dataKey="model"
                    tick={{ fontSize: 11, fill: '#aaa8c3' }}
                    axisLine={{ stroke: 'rgba(70,70,93,0.15)' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tick={{ fontSize: 11, fill: '#aaa8c3' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Bar dataKey="simple" name="Simple" fill="#a3a6ff" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="logic" name="Logic" fill="#ff67ad" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="security" name="Security" fill="#ef81c4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-on-surface-variant text-sm">
                No leaderboard data. Run a baseline first.
              </div>
            )}
          </div>
        </motion.div>

        {/* Radar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card rounded-xl overflow-hidden"
        >
          <div className="px-6 py-4 bg-surface-container-high/50">
            <h3 className="text-sm font-semibold text-on-surface flex items-center gap-2">
              <Award className="w-4 h-4 text-secondary" />
              Skill Breakdown
            </h3>
          </div>
          <div className="p-6 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
                <PolarGrid stroke="rgba(70,70,93,0.2)" />
                <PolarAngleAxis
                  dataKey="subject"
                  tick={{ fontSize: 11, fill: '#aaa8c3' }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 1]}
                  tick={{ fontSize: 10, fill: '#74738c' }}
                />
                <Radar
                  name="Score"
                  dataKey="score"
                  stroke="#a3a6ff"
                  fill="#a3a6ff"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Full Leaderboard Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="glass-card rounded-xl overflow-hidden"
      >
        <div className="flex items-center justify-between px-6 py-4 bg-surface-container-high/50">
          <h3 className="text-sm font-semibold text-on-surface flex items-center gap-2">
            <Trophy className="w-4 h-4 text-warning" />
            Full Leaderboard
          </h3>
          <span className="text-[10px] font-medium text-on-surface-variant uppercase tracking-widest">
            {runs.length} runs · Public set only
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] font-medium text-on-surface-variant uppercase tracking-widest">
                <th className="text-left px-6 py-3">Rank</th>
                <th className="text-left px-4 py-3">Model</th>
                <th className="text-right px-4 py-3">Mean</th>
                <th className="text-right px-4 py-3 hidden md:table-cell">Simple</th>
                <th className="text-right px-4 py-3 hidden md:table-cell">Logic</th>
                <th className="text-right px-4 py-3 hidden md:table-cell">Security</th>
                <th className="text-right px-6 py-3">Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/10">
              {runs.length > 0 ? (
                runs.map((run, i) => {
                  const delta = run.delta_from_last_run || {}
                  const totalDelta = Object.values(delta).reduce((a, b) => a + (b || 0), 0)
                  return (
                    <motion.tr
                      key={`${run.model}-${i}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.55 + i * 0.04 }}
                      className="hover:bg-surface-container/30 transition-colors"
                    >
                      <td className="px-6 py-3.5">
                        {i < 3 ? (
                          <Trophy className={cn('w-4 h-4', trophyColors[i])} />
                        ) : (
                          <span className="text-xs font-bold text-outline tabular-nums">{i + 1}</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <div className={cn(
                            'w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0',
                            i === 0 ? 'bg-gradient-to-br from-primary to-secondary text-white' : 'bg-surface-container-highest text-on-surface-variant'
                          )}>
                            {(run.model || '?').charAt(0)}
                          </div>
                          <span className="font-medium text-on-surface">{run.model || 'Unknown'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <span className="font-bold text-on-surface tabular-nums">
                          {(run.mean || 0).toFixed(4)}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right hidden md:table-cell">
                        <span className="text-on-surface-variant tabular-nums">
                          {(run.scores?.simple_review || 0).toFixed(4)}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right hidden md:table-cell">
                        <span className="text-on-surface-variant tabular-nums">
                          {(run.scores?.logic_review || 0).toFixed(4)}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right hidden md:table-cell">
                        <span className="text-on-surface-variant tabular-nums">
                          {(run.scores?.security_review || 0).toFixed(4)}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        {totalDelta !== 0 ? (
                          <span className={cn(
                            'inline-flex items-center gap-0.5 text-xs font-semibold tabular-nums',
                            totalDelta > 0 ? 'text-success' : 'text-error',
                          )}>
                            {totalDelta > 0 ? (
                              <TrendingUp className="w-3.5 h-3.5" />
                            ) : (
                              <TrendingDown className="w-3.5 h-3.5" />
                            )}
                            {Math.abs(totalDelta).toFixed(4)}
                          </span>
                        ) : (
                          <span className="text-xs text-outline">—</span>
                        )}
                      </td>
                    </motion.tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-on-surface-variant">
                    <Trophy className="w-8 h-8 mx-auto mb-3 opacity-30" />
                    <p className="text-sm">No leaderboard data yet</p>
                    <p className="text-xs mt-1">Run a baseline to populate the leaderboard</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  )
}
