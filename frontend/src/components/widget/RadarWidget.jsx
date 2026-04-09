import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

export default function RadarWidget({ title = 'Threat Radar', delay = 0 }) {
  const canvasRef = useRef(null)
  const animRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const size = 180
    canvas.width = size
    canvas.height = size
    const cx = size / 2
    const cy = size / 2
    const radius = 80
    let angle = 0

    const draw = () => {
      ctx.clearRect(0, 0, size, size)

      // Concentric circles
      for (let r = 25; r <= radius; r += 25) {
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)'
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Cross lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)'
      ctx.beginPath()
      ctx.moveTo(cx - radius, cy); ctx.lineTo(cx + radius, cy)
      ctx.moveTo(cx, cy - radius); ctx.lineTo(cx, cy + radius)
      ctx.stroke()

      // Sweep
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.arc(cx, cy, radius, angle - 0.6, angle)
      ctx.closePath()
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius)
      grad.addColorStop(0, 'rgba(200, 162, 255, 0.15)')
      grad.addColorStop(1, 'rgba(200, 162, 255, 0)')
      ctx.fillStyle = grad
      ctx.fill()

      // Sweep line
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle))
      ctx.strokeStyle = 'rgba(200, 162, 255, 0.4)'
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Center
      ctx.beginPath()
      ctx.arc(cx, cy, 2, 0, Math.PI * 2)
      ctx.fillStyle = '#C8A2FF'
      ctx.fill()

      angle += 0.015
      animRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animRef.current)
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="surface-card flex flex-col overflow-hidden"
    >
      <div className="px-6 py-5 border-b border-subtle">
        <h3 className="text-[14px] font-medium text-text-primary">{title}</h3>
        <p className="text-[12px] text-text-muted mt-0.5">Real-time heuristics</p>
      </div>

      <div className="p-6 flex flex-col items-center justify-center">
        <canvas ref={canvasRef} style={{ width: 180, height: 180 }} />
        
        <div className="w-full mt-6 space-y-2 text-[12px] text-text-muted bg-bg-primary rounded-xl p-4 border border-subtle">
          <p><span className="text-accent">›</span> Scanning active PRs</p>
          <p><span className="text-accent">›</span> Sweep interval: 4.0s</p>
          <p><span className="text-success">›</span> Perimeter secure</p>
        </div>
      </div>
    </motion.div>
  )
}
