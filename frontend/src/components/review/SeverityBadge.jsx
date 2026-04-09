import { cn } from '@/lib/utils'

const config = {
  critical: { className: 'badge-critical', label: 'CRITICAL' },
  major: { className: 'badge-warning', label: 'MAJOR' },
  minor: { className: 'badge-info', label: 'MINOR' },
  nit: { className: 'badge-accent', label: 'NIT' },
}

export default function SeverityBadge({ severity, className: extraClass }) {
  const c = config[severity] || config.major
  return (
    <span className={cn('badge', c.className, extraClass)}>
      {c.label}
    </span>
  )
}
