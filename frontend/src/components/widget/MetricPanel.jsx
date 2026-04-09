import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

export default function MetricPanel({ label, value, sub, icon: Icon, accent, delay = 0, className }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={cn('tactical-panel p-0', className)}
    >
      <div className="p-4">
        {Icon && (
          <div className="mb-3">
            <Icon className={cn('w-4 h-4', accent ? 'text-tactical' : 'text-text-dim')} />
          </div>
        )}

        <p className="text-[10px] font-mono font-semibold text-text-dim uppercase tracking-[0.15em] mb-1">
          {label}
        </p>

        <div className="flex items-baseline gap-2">
          <span className={cn(
            'text-2xl font-mono font-bold tracking-tight',
            accent ? 'text-tactical' : 'text-text-bright'
          )}>
            {value}
          </span>
          {sub && (
            <span className="text-[10px] font-mono text-text-dim uppercase tracking-wider">
              {sub}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}
