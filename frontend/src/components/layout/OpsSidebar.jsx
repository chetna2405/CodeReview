import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Monitor,
  Network,
  Shield,
  Brain,
  Settings,
  ChevronLeft,
  ChevronRight,
  Wifi,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { path: '/', label: 'Command Center', icon: Monitor },
  { path: '/new-review', label: 'Agent Network', icon: Network },
  { path: '/review', label: 'Operations', icon: Shield },
  { path: '/metrics', label: 'Intelligence', icon: Brain },
  { path: '/settings', label: 'Systems', icon: Settings },
]

export default function OpsSidebar({ collapsed, onToggle }) {
  const location = useLocation()
  const [uptime, setUptime] = useState('00:00:00')
  const [uptimeSeconds, setUptimeSeconds] = useState(0)

  useEffect(() => {
    const start = Date.now()
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - start) / 1000)
      setUptimeSeconds(elapsed)
      const h = String(Math.floor(elapsed / 3600)).padStart(2, '0')
      const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0')
      const s = String(elapsed % 60).padStart(2, '0')
      setUptime(`${h}:${m}:${s}`)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 z-40 lg:hidden"
            onClick={onToggle}
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 60 : 220 }}
        transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
        className={cn(
          'fixed left-0 top-0 bottom-0 z-50 flex flex-col',
          'bg-surface-panel border-r border-surface-border',
          'max-lg:shadow-2xl',
          collapsed ? 'max-lg:-translate-x-full' : 'max-lg:translate-x-0',
        )}
      >
        {/* ── Logo Area ── */}
        <div className="flex items-center gap-2.5 px-4 h-14 border-b border-surface-border shrink-0">
          <div className="w-7 h-7 flex items-center justify-center shrink-0">
            <Shield className="w-5 h-5 text-tactical" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <h1 className="text-xs font-bold tracking-wider text-tactical font-mono uppercase">
                  CODEREVIEW OPS
                </h1>
                <p className="text-[9px] font-mono text-text-dim tracking-widest">
                  v2.1.7 CLASSIFIED
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Navigation ── */}
        <nav className="flex-1 flex flex-col gap-0.5 py-3 px-2 mt-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={cn(
                  'group relative flex items-center gap-3 px-3 py-2.5',
                  'text-[11px] font-mono font-semibold tracking-wider uppercase',
                  'transition-all duration-150',
                  isActive
                    ? 'nav-active'
                    : 'nav-item text-text-muted hover:text-text-bright',
                )}
              >
                <item.icon className={cn('w-4 h-4 shrink-0', isActive && 'text-surface-base')} />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -6 }}
                      transition={{ duration: 0.12 }}
                      className="truncate"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </NavLink>
            )
          })}
        </nav>

        {/* ── System Status (Bottom) ── */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-4 pb-4 space-y-2"
            >
              <div className="border-t border-surface-border pt-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-status-online blink-online" />
                  <span className="text-[10px] font-mono font-bold text-text-bright uppercase tracking-widest">
                    System Online
                  </span>
                </div>

                <div className="space-y-1 text-[9px] font-mono text-text-dim uppercase tracking-wider">
                  <p>UPTIME: {uptime}</p>
                  <p>AGENTS: 847 ACTIVE</p>
                  <p>MISSIONS: 23 ONGOING</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Collapse Toggle ── */}
        <button
          onClick={onToggle}
          className="absolute -right-3 top-16 w-5 h-5 bg-surface-panel border border-surface-border flex items-center justify-center text-text-dim hover:text-tactical hover:border-tactical transition-all duration-150 max-lg:hidden"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </motion.aside>
    </>
  )
}
