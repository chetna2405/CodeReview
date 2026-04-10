import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Crosshair, Shield, BarChart3, Settings, ChevronLeft, ChevronRight,
  Award, Play
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/new-review', label: 'Deploy Agent', icon: Crosshair },
  { path: '/review', label: 'Active Ops', icon: Shield },
  { path: '/grader', label: 'Grader', icon: Award },
  { path: '/replay', label: 'Replay', icon: Play },
  { path: '/metrics', label: 'Intelligence', icon: BarChart3 },
]

export default function Sidebar({ collapsed, onToggle }) {
  const location = useLocation()

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 240 }}
      className="shrink-0 flex flex-col bg-bg-primary border-r border-subtle relative h-full z-40 transition-shadow"
      style={{ overflow: 'visible' }} // Allow toggle button to overflow
    >
      {/* Logo Area */}
      <div className={cn("flex items-center px-4 h-16 shrink-0 mt-2", collapsed ? "justify-center" : "gap-3")}>
        <div className="w-8 h-8 rounded-xl bg-bg-elevated border border-subtle flex items-center justify-center shrink-0">
          <Shield className="w-4 h-4 text-accent" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, width: 0 }} 
              animate={{ opacity: 1, width: 'auto' }} 
              exit={{ opacity: 0, width: 0 }}
              style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
            >
              <h1 className="text-[14px] font-semibold text-text-primary tracking-tight">CodeReview Ops</h1>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1.5 px-3 mt-6">
        <AnimatePresence>
          {!collapsed && (
             <motion.p 
               initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
               className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2 px-2 whitespace-nowrap"
             >
               Menu
             </motion.p>
          )}
        </AnimatePresence>
        
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={cn(
                'group relative flex items-center px-3 py-2.5 rounded-xl text-[13px] font-medium transition-colors duration-200',
                collapsed ? 'justify-center' : 'gap-3',
                isActive ? 'text-text-primary bg-bg-secondary border border-subtle' : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover border border-transparent',
              )}
              title={collapsed ? item.label : undefined}
            >
              <item.icon className={cn('w-[18px] h-[18px] shrink-0', isActive ? 'text-accent' : 'text-text-muted group-hover:text-text-primary')} />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span 
                    initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }} exit={{ opacity: 0, width: 0 }}
                    style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </NavLink>
          )
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="px-3 pb-6 flex flex-col gap-2">
        <NavLink
          to="/settings"
          className={({ isActive }) => cn(
            'flex items-center px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all border',
            collapsed ? 'justify-center' : 'gap-3',
            isActive ? 'text-text-primary bg-bg-secondary border-subtle' : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover border-transparent',
          )}
          title={collapsed ? "Settings" : undefined}
        >
          <Settings className="w-[18px] h-[18px] shrink-0 text-text-muted" />
          <AnimatePresence>
            {!collapsed && (
              <motion.span 
                 initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }} exit={{ opacity: 0, width: 0 }}
                 style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
              >
                Settings
              </motion.span>
            )}
          </AnimatePresence>
        </NavLink>

        <AnimatePresence>
          {!collapsed && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} 
              style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
              className="px-3 pt-2"
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-success drop-shadow-[0_0_8px_rgba(134,239,172,0.6)]" />
                <span className="text-[12px] font-medium text-text-muted">
                  System Online
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3.5 top-16 w-7 h-7 rounded-full bg-bg-primary border border-subtle flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-all shadow-sm z-50 hidden md:flex"
      >
        {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>
    </motion.aside>
  )
}
