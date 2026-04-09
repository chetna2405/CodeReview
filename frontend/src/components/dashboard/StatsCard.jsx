import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

export default function StatsCard({ icon: Icon, label, value, suffix, trend, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.4, 0, 0.2, 1] }}
      className="glass-card rounded-xl p-6 group cursor-default"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        {trend !== undefined && (
          <span
            className={cn(
              'text-xs font-semibold px-2 py-0.5 rounded-full',
              trend >= 0
                ? 'text-success bg-success/10'
                : 'text-error bg-error/10',
            )}
          >
            {trend >= 0 ? '+' : ''}
            {trend}%
          </span>
        )}
      </div>

      <p className="text-[11px] font-medium text-on-surface-variant uppercase tracking-widest mb-1">
        {label}
      </p>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold text-on-surface tracking-tight">
          {value}
        </span>
        {suffix && (
          <span className="text-sm font-medium text-on-surface-variant">{suffix}</span>
        )}
      </div>
    </motion.div>
  )
}
