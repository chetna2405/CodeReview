import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Trophy, TrendingUp, TrendingDown, Target, Zap, ShieldCheck, BarChart3, Award } from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RTooltip, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  AreaChart, Area,
} from 'recharts'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'
import MetricCard from '@/components/widget/MetricCard'

const Tip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="surface-inner px-3 py-2 text-[11px]">
      <p className="text-text-muted mb-1 font-medium">{label}</p>
      {payload.map((p, i) => <p key={i} style={{ color: p.color }} className="font-semibold">{p.name}: {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}</p>)}
    </div>
  )
}

export default function MissionMetrics() {
  const [leaderboard, setLeaderboard] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { api.getLeaderboard().then(setLeaderboard).catch(() => {}).finally(() => setLoading(false)) }, [])

  const runs = leaderboard?.runs || []
  const topRun = runs[0]

  const barData = runs.slice(0, 6).map(r => ({
    model: r.model?.split('-').slice(0, 2).join('-') || '?',
    simple: r.scores?.simple_review || 0,
    logic: r.scores?.logic_review || 0,
    security: r.scores?.security_review || 0,
  }))

  const radarData = topRun?.category_scores
    ? Object.entries(topRun.category_scores).filter(([_, v]) => v !== null).map(([k, v]) => ({ s: k.charAt(0).toUpperCase() + k.slice(1), v, f: 1 }))
    : [{ s: 'Security', v: 0.61, f: 1 }, { s: 'Logic', v: 0.55, f: 1 }, { s: 'Style', v: 0.72, f: 1 }, { s: 'Cross-File', v: 0.38, f: 1 }]

  if (loading) return <div className="space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}</div>

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Intelligence Report</h1>
        <p className="text-sm text-text-muted mt-1">Performance analytics and model benchmarks.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <MetricCard icon={Trophy} label="Top Model" value={topRun?.model?.split('-')[0] || 'N/A'} accent delay={0} sparkData={[0.8, 0.85, 0.88, 0.91, 0.93, 0.96]} />
        <MetricCard icon={Target} label="Best Score" value={topRun?.mean?.toFixed(4) || '—'} delay={0.05} sparkData={[0.5, 0.6, 0.65, 0.7, 0.75, 0.8]} />
        <MetricCard icon={Zap} label="Total Runs" value={runs.length.toString()} delay={0.1} sparkData={[1, 2, 3, 4, 5, runs.length]} />
        <MetricCard icon={ShieldCheck} label="Avg Security" value={topRun?.category_scores?.security?.toFixed(2) || '—'} delay={0.15} sparkData={[0.4, 0.5, 0.55, 0.6, 0.58, 0.61]} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 mb-5">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="xl:col-span-8 surface-card overflow-hidden">
          <div className="px-5 py-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-accent" />
            <h3 className="text-[13px] font-semibold text-text-primary">Performance by Category</h3>
          </div>
          <div className="px-4 pb-4 h-72">
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} barGap={2}>
                  <defs>
                    <linearGradient id="barAccent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#C8A2FF" stopOpacity={0.9} />
                      <stop offset="100%" stopColor="#C8A2FF" stopOpacity={0.4} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(200,162,255,0.06)" vertical={false} />
                  <XAxis dataKey="model" tick={{ fontSize: 10, fill: '#71717A' }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: '#71717A' }} axisLine={false} tickLine={false} />
                  <RTooltip content={<Tip />} />
                  <Bar dataKey="simple" name="Simple" fill="url(#barAccent)" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="logic" name="Logic" fill="#A1A1AA" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="security" name="Security" fill="#FCA5A5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-full">
                <BarChart3 className="w-10 h-10 text-text-dim/20 mb-3" />
                <p className="text-[13px] text-text-muted font-medium">No benchmark data yet</p>
                <p className="text-[11px] text-text-dim mt-1">Run a baseline to populate analytics.</p>
              </div>
            )}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="xl:col-span-4 surface-card overflow-hidden">
          <div className="px-5 py-4 flex items-center gap-2">
            <Award className="w-4 h-4 text-accent" />
            <h3 className="text-[13px] font-semibold text-text-primary">Skill Radar</h3>
          </div>
          <div className="px-4 pb-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                <PolarGrid stroke="rgba(200,162,255,0.08)" />
                <PolarAngleAxis dataKey="s" tick={{ fontSize: 10, fill: '#A1A1AA' }} />
                <PolarRadiusAxis angle={90} domain={[0, 1]} tick={{ fontSize: 9, fill: '#52525B' }} />
                <Radar dataKey="v" stroke="#C8A2FF" fill="#C8A2FF" fillOpacity={0.12} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Leaderboard */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="surface-card overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-accent-border">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-accent" />
            <h3 className="text-[13px] font-semibold text-text-primary">Leaderboard</h3>
          </div>
          <span className="text-[11px] text-text-dim">{runs.length} runs</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead><tr className="text-[10px] text-text-dim uppercase tracking-[0.12em] border-b border-accent-border/50">
              <th className="text-left px-5 py-2.5">Rank</th><th className="text-left px-4 py-2.5">Model</th>
              <th className="text-right px-4 py-2.5">Mean</th><th className="text-right px-4 py-2.5 hidden md:table-cell">Simple</th>
              <th className="text-right px-4 py-2.5 hidden md:table-cell">Logic</th><th className="text-right px-4 py-2.5 hidden md:table-cell">Security</th>
              <th className="text-right px-5 py-2.5">Delta</th>
            </tr></thead>
            <tbody className="divide-y divide-accent-border/30">
              {runs.length > 0 ? runs.map((r, i) => {
                const d = r.delta_from_last_run || {}
                const td = Object.values(d).reduce((a, b) => a + (b || 0), 0)
                return (
                  <motion.tr key={`${r.model}-${i}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.45 + i * 0.03 }} className="hover:bg-bg-hover/20 transition-colors">
                    <td className="px-5 py-3">{i < 3 ? <div className={cn('w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold', i === 0 ? 'bg-accent/15 text-accent' : 'bg-bg-secondary text-text-dim')}>{i + 1}</div> : <span className="text-text-dim ml-1.5">{i + 1}</span>}</td>
                    <td className="px-4 py-3"><span className="text-text-primary font-medium">{r.model || '?'}</span></td>
                    <td className="px-4 py-3 text-right font-bold text-text-primary tabular-nums">{(r.mean || 0).toFixed(4)}</td>
                    <td className="px-4 py-3 text-right hidden md:table-cell text-text-muted tabular-nums">{(r.scores?.simple_review || 0).toFixed(4)}</td>
                    <td className="px-4 py-3 text-right hidden md:table-cell text-text-muted tabular-nums">{(r.scores?.logic_review || 0).toFixed(4)}</td>
                    <td className="px-4 py-3 text-right hidden md:table-cell text-text-muted tabular-nums">{(r.scores?.security_review || 0).toFixed(4)}</td>
                    <td className="px-5 py-3 text-right">{td !== 0 ? <span className={cn('inline-flex items-center gap-0.5 font-semibold tabular-nums', td > 0 ? 'text-success' : 'text-danger')}>{td > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}{Math.abs(td).toFixed(4)}</span> : <span className="text-text-dim">—</span>}</td>
                  </motion.tr>
                )
              }) : (
                <tr><td colSpan={7} className="py-16 text-center">
                  <Trophy className="w-10 h-10 text-text-dim/20 mx-auto mb-3" />
                  <p className="text-[13px] text-text-muted font-medium">No leaderboard data yet</p>
                  <p className="text-[11px] text-text-dim mt-1">Run a baseline to populate the rankings.</p>
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  )
}
