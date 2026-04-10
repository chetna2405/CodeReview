import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Zap, Target, Layers, ArrowRight } from 'lucide-react'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'
import MetricCard from '@/components/widget/MetricCard'
import ActivityFeed from '@/components/widget/ActivityFeed'
import RadarWidget from '@/components/widget/RadarWidget'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

const trendData = [
  { d: 'W1', v: 280, b: 300 }, { d: 'W2', v: 310, b: 295 }, { d: 'W3', v: 340, b: 300 },
  { d: 'W4', v: 320, b: 305 }, { d: 'W5', v: 380, b: 310 }, { d: 'W6', v: 350, b: 305 },
  { d: 'W7', v: 420, b: 315 }, { d: 'W8', v: 400, b: 320 },
]

const skillData = [
  { s: 'Security', v: 0.82 }, { s: 'Logic', v: 0.71 },
  { s: 'Style', v: 0.89 }, { s: 'Cross-File', v: 0.56 }, { s: 'Perf', v: 0.74 },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="surface-inner px-3 py-2 text-[12px] shadow-xl">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-medium">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

const topAgentsMock = [
  { name: 'GPT-4o', score: 0.96, reviews: 982, trend: +4.2 },
  { name: 'Claude-3.5', score: 0.91, reviews: 845, trend: +2.1 },
  { name: 'Qwen2.5-72B', score: 0.88, reviews: 721, trend: -0.8 },
  { name: 'Gemini-2.0', score: 0.85, reviews: 654, trend: +5.9 },
]

export default function CommandCenter() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [healthData, setHealthData] = useState(null)
  const [leaderboard, setLeaderboard] = useState([])

  useEffect(() => {
    Promise.allSettled([api.getTasks(), api.getLeaderboard(), api.health()])
      .then((results) => {
        if (results[1].status === 'fulfilled') {
          setLeaderboard(results[1].value)
        }
        if (results[2].status === 'fulfilled') {
          setHealthData(results[2].value)
        }
      })
      .finally(() => setLoading(false))
  }, [])

  // If leaderboard is empty, show the mock but explicitly labeled to prevent deception.
  const displayAgents = leaderboard.length > 0 
    ? leaderboard.map(l => ({ name: l.model, score: l.mean, reviews: '-', trend: 0 }))
    : topAgentsMock.map(a => ({ ...a, name: `${a.name} (Simulated)` }))

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="max-w-[1400px]"
    >
      <div className="mb-8 pl-1">
        <h1 className="text-2xl font-medium tracking-tight text-text-primary">Overview</h1>
        <p className="text-[13px] text-text-muted mt-1">Intelligence and operation metrics.</p>
      </div>

      {/* Row 1: Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          icon={Shield} 
          label="Total Reviews" 
          value={healthData ? healthData.total_episodes_completed.toLocaleString() : "1,284*"} 
          trend={healthData && healthData.total_episodes_completed > 0 ? 100 : 0}
          trendLabel={healthData ? "Live production total" : "Projected capability"} 
          sparkData={[40, 42, 38, 45, 50, 48, 55, 60]} delay={0}
        />
        <MetricCard
          icon={Zap} 
          label="Active Episodes" 
          value={healthData ? healthData.active_sessions.toString() : "0"} 
          trend={0}
          sparkData={[8, 10, 9, 12, 11, 14, 13, 14]} delay={0.05}
        />
        <MetricCard
          icon={Target} 
          label="Avg Accuracy" 
          value={healthData && healthData.mean_composite_score !== null ? `${(healthData.mean_composite_score * 100).toFixed(1)}%` : "0.0%"} 
          trend={0}
          sparkData={[92, 90, 88, 93, 94, 91, 95, 94.2]} accent delay={0.1}
        />
        <MetricCard
          icon={Layers} 
          label="Tasks Loaded" 
          value={healthData ? Object.values(healthData.scenarios_loaded).reduce((a, b) => a + b, 0).toString() : "72+"}
          trendLabel="Dynamically structured" sparkData={[72, 72, 72, 72, 72, 72, 72, 72]} delay={0.15}
        />
      </div>

      {/* Row 2: Two Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        
        {/* Left Col */}
        <div className="flex flex-col gap-6">
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="surface-card flex-1 flex flex-col"
          >
            <div className="px-6 py-5 flex items-center justify-between border-b border-subtle">
              <div>
                <h3 className="text-[14px] font-medium text-text-primary">Activity Trend</h3>
                <p className="text-[12px] text-text-muted mt-0.5">Aggregated weekly volume</p>
              </div>
            </div>
            <div className="p-6 flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="accentGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#C8A2FF" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#C8A2FF" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                  <XAxis dataKey="d" tick={{ fontSize: 11, fill: '#70707D' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#70707D' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="v" name="Activity" stroke="#C8A2FF" strokeWidth={2} fill="url(#accentGrad)" activeDot={{ r: 4, fill: '#C8A2FF', stroke: '#050507', strokeWidth: 2 }} />
                  <Area type="monotone" dataKey="b" name="Baseline" stroke="#4B4B57" strokeWidth={1.5} strokeDasharray="4 4" fill="none" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
          
          <ActivityFeed delay={0.25} />
        </div>

        {/* Right Col */}
        <div className="flex flex-col gap-6">
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="surface-card"
          >
             <div className="px-6 py-5 flex items-center justify-between border-b border-subtle">
              <div>
                <h3 className="text-[14px] font-medium text-text-primary">Top Agents</h3>
                <p className="text-[12px] text-text-muted mt-0.5">Best performing models</p>
              </div>
              <button onClick={() => navigate('/metrics')} className="text-[12px] text-text-secondary hover:text-text-primary flex items-center gap-1 transition-colors">
                Report <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="p-2 space-y-1">
              {displayAgents.map((a, i) => (
                <div
                  key={a.name}
                  className="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-bg-elevated transition-colors cursor-default"
                >
                  <div className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-medium shrink-0',
                    i === 0 ? 'bg-accent/10 border border-accent/20 text-accent' : 'text-text-muted'
                  )}>
                    {i + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-[13px] font-medium text-text-primary">{a.name}</p>
                  </div>
                  <p className="text-[12px] text-text-muted">{a.reviews} rev</p>
                  <div className="w-16 text-right">
                    <p className="text-[13px] font-medium text-text-primary">{a.score.toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          <RadarWidget delay={0.35} />
        </div>
      </div>
    </motion.div>
  )
}
