import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

function Sparkline({ data, color = 'var(--color-accent)', height = 36, width = 96 }) {
  if (!data || data.length < 2) return null
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((v - min) / range) * height
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={width} height={height} className="overflow-visible opacity-80 group-hover:opacity-100 transition-opacity">
      <defs>
        <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} strokeLinecap="round" strokeLinejoin="round" />
      <polygon fill="url(#sparkFill)" points={`0,${height} ${points} ${width},${height}`} />
    </svg>
  )
}

export default function MetricCard({
  icon: Icon,
  label,
  value,
  trend,
  trendLabel,
  sparkData,
  accent = false,
  delay = 0,
  className,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.4, 0, 0.2, 1] }}
      className={cn('surface-card p-6 group flex flex-col justify-between h-full', className)}
    >
      <div className="flex items-start justify-between mb-4">
        <p className="text-[12px] font-medium text-text-muted">
          {label}
        </p>
        {Icon && (
          <div className="w-8 h-8 rounded-full bg-bg-elevated border border-subtle flex items-center justify-center">
            <Icon className="w-4 h-4 text-text-secondary" />
          </div>
        )}
      </div>

      <div className="flex items-end justify-between mt-auto">
        <div>
          <div className="flex items-baseline gap-3 mb-1">
            <span className={cn(
              'text-3xl font-semibold tracking-tight',
              accent ? 'text-text-primary drop-shadow-[0_0_12px_rgba(200,162,255,0.4)]' : 'text-text-primary'
            )}>
              {value}
            </span>
            {trend !== undefined && (
              <div className={cn(
                'flex items-center gap-1 text-[12px] font-medium px-2 py-0.5 rounded-full border border-subtle backdrop-blur-sm',
                trend >= 0 ? 'text-success bg-success-dim/50' : 'text-danger bg-danger-dim/50',
              )}>
                {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                <span>{Math.abs(trend)}%</span>
              </div>
            )}
          </div>
          {trendLabel && (
            <p className="text-[12px] text-text-dim">{trendLabel}</p>
          )}
        </div>

        {sparkData && (
          <div className="pb-1">
            <Sparkline data={sparkData} />
          </div>
        )}
      </div>
    </motion.div>
  )
}
