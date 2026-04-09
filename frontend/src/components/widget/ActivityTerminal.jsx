import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

const sampleLogs = [
  { time: '25/06/2025 08:12', text: 'Agent <hl>dr4g0n_V3in</hl> extracted high-value target in <br>Cairo</br>' },
  { time: '24/06/2025 22:55', text: 'Agent <hl>sn4ke_Sh4de</hl> lost communication in <br>Havana</br>' },
  { time: '24/06/2025 21:33', text: 'Agent <hl>ph4nt0m_R4ven</hl> initiated surveillance in <br>Tokyo</br>' },
  { time: '24/06/2025 19:45', text: 'Agent <hl>v0id_Walk3r</hl> compromised security in <br>Moscow</br> with agent <hl>d4rk_M4trix</hl>' },
  { time: '24/06/2025 17:20', text: 'Agent <hl>cyb3r_Ph03nix</hl> deployed payload to <br>Berlin</br> sector' },
  { time: '24/06/2025 15:08', text: 'Agent <hl>gh0st_R1der</hl> extracted credentials from <br>London</br> node' },
]

function parseLogText(raw) {
  const parts = []
  let remaining = raw
  const regex = /<(hl|br)>(.*?)<\/\1>/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: raw.slice(lastIndex, match.index) })
    }
    parts.push({
      type: match[1] === 'hl' ? 'highlight' : 'bright',
      content: match[2],
    })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < raw.length) {
    parts.push({ type: 'text', content: raw.slice(lastIndex) })
  }
  return parts
}

export default function ActivityTerminal({ logs, title = 'Activity Log' }) {
  const entries = logs || sampleLogs
  const scrollRef = useRef(null)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="tactical-panel flex flex-col h-full"
    >
      <div className="tactical-panel-header">{title}</div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-0">
        {entries.map((entry, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 + i * 0.06 }}
            className="py-3 border-l-2 border-tactical/30 pl-4 relative"
          >
            {/* Timeline dot */}
            <div className="absolute -left-[5px] top-4 w-2 h-2 bg-tactical" />

            <p className="text-[10px] font-mono text-tactical/70 tracking-wider mb-1">
              {entry.time}
            </p>
            <p className="text-[12px] font-mono text-text-muted leading-relaxed">
              {parseLogText(entry.text).map((part, j) => {
                if (part.type === 'highlight') {
                  return <span key={j} className="text-tactical font-semibold">{part.content}</span>
                }
                if (part.type === 'bright') {
                  return <span key={j} className="text-text-bright font-semibold">{part.content}</span>
                }
                return <span key={j}>{part.content}</span>
              })}
            </p>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
