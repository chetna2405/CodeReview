import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Search, Bell, Menu } from 'lucide-react'

const pathNames = {
  '/': 'Command Center',
  '/new-review': 'Deploy Agent',
  '/review': 'Active Operations',
  '/metrics': 'Intelligence',
  '/settings': 'Settings',
}

export default function Header({ onMenuClick, sidebarCollapsed }) {
  const location = useLocation()
  const [utcTime, setUtcTime] = useState('')

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      setUtcTime(now.toISOString().replace('T', ' ').slice(0, 19) + ' UTC')
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="sticky top-0 z-30 bg-bg-base/80 backdrop-blur-xl border-b border-subtle h-16 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-4">
        {/* Only show menu toggle on mobile */}
        <button onClick={onMenuClick} className="md:hidden p-1.5 text-text-muted hover:text-text-primary transition-colors">
          <Menu className="w-5 h-5" />
        </button>

        <span className="text-[14px] text-text-primary font-medium tracking-tight">
          {pathNames[location.pathname] || 'Dashboard'}
        </span>
      </div>

      <div className="flex items-center gap-6">
        <span className="hidden md:block text-[12px] text-text-muted font-mono">{utcTime}</span>

        <div className="flex items-center gap-4 border-l border-subtle pl-6">
          <button className="text-text-muted hover:text-text-primary transition-colors">
            <Search className="w-4 h-4" />
          </button>
          <button className="relative text-text-muted hover:text-text-primary transition-colors">
            <Bell className="w-4 h-4" />
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-accent rounded-full border-2 border-bg-base" />
          </button>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-bg-elevated to-bg-tertiary border border-subtle flex items-center justify-center cursor-pointer hover:border-accent/40 transition-colors">
            <span className="text-[11px] font-bold text-text-primary">CR</span>
          </div>
        </div>
      </div>
    </header>
  )
}
