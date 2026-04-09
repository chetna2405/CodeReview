import { motion } from 'framer-motion'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Line,
  ComposedChart,
} from 'recharts'

const sampleData = [
  { date: 'Jan 28', value: 280, baseline: 300 },
  { date: 'Feb 04', value: 310, baseline: 295 },
  { date: 'Feb 11', value: 290, baseline: 300 },
  { date: 'Feb 18', value: 340, baseline: 305 },
  { date: 'Feb 25', value: 380, baseline: 310 },
  { date: 'Mar 04', value: 350, baseline: 305 },
  { date: 'Mar 11', value: 390, baseline: 310 },
  { date: 'Mar 18', value: 420, baseline: 315 },
  { date: 'Mar 25', value: 380, baseline: 310 },
  { date: 'Apr 01', value: 400, baseline: 320 },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-panel border border-surface-border p-2 text-[10px] font-mono">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-semibold">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

export default function MissionChart({ data, title = 'Mission Activity Overview' }) {
  const chartData = data || sampleData

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.35 }}
      className="tactical-panel"
    >
      <div className="tactical-panel-header">{title}</div>

      <div className="p-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(42, 42, 42, 0.6)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#555555', fontFamily: 'JetBrains Mono' }}
              axisLine={{ stroke: '#2a2a2a' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#555555', fontFamily: 'JetBrains Mono' }}
              axisLine={false}
              tickLine={false}
              domain={['dataMin - 50', 'dataMax + 50']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="value"
              name="Activity"
              stroke="#ff6a00"
              strokeWidth={2}
              fill="rgba(255, 106, 0, 0.08)"
              dot={{ r: 3, fill: '#ff6a00', stroke: '#ff6a00' }}
              activeDot={{ r: 5, fill: '#ff6a00', stroke: '#0a0a0a', strokeWidth: 2 }}
            />
            <Line
              type="monotone"
              dataKey="baseline"
              name="Baseline"
              stroke="#555555"
              strokeWidth={1}
              strokeDasharray="6 3"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  )
}
