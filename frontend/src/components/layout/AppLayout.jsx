import { useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AppLayout({ children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const toggleSidebar = () => setSidebarCollapsed(prev => !prev)

  return (
    <div className="flex h-screen bg-bg-base overflow-hidden">
      <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
      
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto">
        <Header onMenuClick={toggleSidebar} sidebarCollapsed={sidebarCollapsed} />
        
        <main className="p-6 lg:p-10 max-w-[1400px] w-full mx-auto relative">
          {children}
        </main>
      </div>
    </div>
  )
}
