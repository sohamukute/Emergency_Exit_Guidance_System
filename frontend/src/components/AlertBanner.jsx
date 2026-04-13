import { AlertTriangle, X } from 'lucide-react'

export default function AlertBanner({ alerts }) {
  if (!alerts || alerts.length === 0) return null

  return (
    <div className="w-full bg-red-900/80 border-b border-red-600/60 backdrop-blur-sm">
      <div className="max-w-screen-2xl mx-auto px-4 py-2 flex flex-wrap gap-2 items-center">
        <AlertTriangle className="text-red-300 shrink-0" size={18} />
        <span className="text-red-200 font-semibold text-sm mr-2">ALERTS:</span>
        {alerts.map((a, i) => (
          <span
            key={i}
            className="px-3 py-1 rounded-full bg-red-800/60 border border-red-500/50 text-red-100 text-xs font-medium animate-pulse"
          >
            {a}
          </span>
        ))}
      </div>
    </div>
  )
}
