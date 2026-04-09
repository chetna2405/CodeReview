import { useState } from 'react'
import { motion } from 'framer-motion'
import OpsSidebar from './OpsSidebar'
import TopCommandBar from './TopCommandBar'

export default function TacticalLayout({ children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const toggleSidebar = () => setSidebarCollapsed((prev) => !prev)

  return (
    <div className="min-h-screen bg-surface-base">
      <OpsSidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />

      <motion.div
        animate={{ marginLeft: sidebarCollapsed ? 60 : 220 }}
        transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
        className="min-h-screen flex flex-col max-lg:!ml-0"
      >
        <TopCommandBar onMenuClick={toggleSidebar} />
        <main className="flex-1 p-4 lg:p-5">
          {children}
        </main>
      </motion.div>
    </div>
  )
}
