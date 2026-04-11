import { useState, createContext, useContext } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import AppLayout from './components/layout/AppLayout'
import CommandCenter from './pages/CommandCenter'
import AgentNetwork from './pages/AgentNetwork'
import IntelReview from './pages/IntelReview'
import MissionMetrics from './pages/MissionMetrics'
import SettingsPage from './pages/SettingsPage'
import GraderPage from './pages/GraderPage'
import ReplayPage from './pages/ReplayPage'

// Shared settings context
const SettingsContext = createContext()
export const useSettings = () => useContext(SettingsContext)

export default function App() {
  const [settings, setSettings] = useState({
    taskId: 'simple_review',
    seed: 42,
    modelLabel: 'rule-based',
    episodeId: null,
  })

  const navigate = useNavigate()

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('demo') === 'replay' && urlParams.get('episode_id')) {
      const eid = urlParams.get('episode_id')
      setSettings(s => ({ ...s, episodeId: eid }))
      navigate(`/grader?episode_id=${eid}`, { replace: true })
    }
  }, [navigate])

  return (
    <SettingsContext.Provider value={{ settings, setSettings }}>
      <AppLayout>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/new-review" element={<AgentNetwork />} />
            <Route path="/review" element={<IntelReview />} />
            <Route path="/metrics" element={<MissionMetrics />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/grader" element={<GraderPage />} />
            <Route path="/replay" element={<ReplayPage />} />
          </Routes>
        </AnimatePresence>
      </AppLayout>
    </SettingsContext.Provider>
  )
}
