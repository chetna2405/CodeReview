import { Routes, Route } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import AppLayout from './components/layout/AppLayout'
import CommandCenter from './pages/CommandCenter'
import AgentNetwork from './pages/AgentNetwork'
import IntelReview from './pages/IntelReview'
import MissionMetrics from './pages/MissionMetrics'

export default function App() {
  return (
    <AppLayout>
      <AnimatePresence mode="wait">
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/new-review" element={<AgentNetwork />} />
          <Route path="/review" element={<IntelReview />} />
          <Route path="/metrics" element={<MissionMetrics />} />
        </Routes>
      </AnimatePresence>
    </AppLayout>
  )
}
