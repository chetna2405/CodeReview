import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Search, Bell, RefreshCw, Menu, Terminal } from 'lucide-react'
import { cn } from '@/lib/utils'

const pathNames = {
  '/': 'Overview',
  '/new-review': 'Agent Network',
  '/review': 'Active Ops',
  '/metrics': 'Intelligence',
  '/settings': 'Systems',
}

export default function TopCommandBar({ onMenuClick }) {
  const location = useLocation()
  const [utcTime, setUtcTime] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      const formatted = now.toUTCString().replace('GMT', 'UTC')
      setUtcTime(formatted)
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="sticky top-0 z-30 h-12 flex items-center gap-4 px-5 bg-surface-base border-b border-surface-border">
      {/* Mobile menu */}
      <button
        onClick={onMenuClick}
        className="lg:hidden p-1.5 text-text-dim hover:text-tactical transition-colors"
      >
        <Menu className="w-4 h-4" />
      </button>

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 font-mono text-[11px] tracking-wider uppercase">
        <span className="text-text-muted font-semibold">Tactical Command</span>
        <span className="text-text-dim">/</span>
        <span className="text-tactical font-bold">
          {pathNames[location.pathname] || 'Page'}
        </span>
      </div>

      <div className="flex-1" />

      {/* UTC Timestamp */}
      <div className="hidden md:flex items-center gap-2 text-[10px] font-mono text-text-dim uppercase tracking-wider">
        <span>LAST UPDATE:</span>
        <span className="text-text-muted">{utcTime}</span>
      </div>

      {/* Sync */}
      <button className="p-1.5 text-text-dim hover:text-tactical transition-colors" title="Sync">
        <RefreshCw className="w-3.5 h-3.5" />
      </button>

      {/* Notifications */}
      <button className="relative p-1.5 text-text-dim hover:text-tactical transition-colors">
        <Bell className="w-3.5 h-3.5" />
        <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-tactical rounded-full" />
      </button>

      {/* Command Palette Trigger */}
      <button
        className={cn(
          'hidden sm:flex items-center gap-2 px-3 py-1.5',
          'bg-surface-panel border border-surface-border',
          'text-[10px] font-mono text-text-dim',
          'hover:border-tactical/30 hover:text-text-muted transition-all'
        )}
      >
        <Terminal className="w-3 h-3" />
        <span className="tracking-wider">/</span>
      </button>

      {/* User */}
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 bg-surface-elevated border border-surface-border flex items-center justify-center">
          <span className="text-[9px] font-mono font-bold text-tactical">OP</span>
        </div>
        <span className="hidden lg:block text-[10px] font-mono text-text-muted uppercase tracking-wider">
          ···
        </span>
      </div>
    </header>
  )
}
