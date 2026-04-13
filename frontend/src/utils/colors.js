// Status colour helpers shared across components
export const STATUS_COLORS = {
  SAFE:         { bg: 'bg-emerald-500/20', border: 'border-emerald-500/40', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  CAUTION:      { bg: 'bg-amber-500/20',   border: 'border-amber-500/40',   text: 'text-amber-400',   dot: 'bg-amber-400'   },
  DANGER:       { bg: 'bg-red-700/20',     border: 'border-red-600/40',     text: 'text-red-400',     dot: 'bg-red-500'     },
  CRITICAL:     { bg: 'bg-red-900/30',     border: 'border-red-800/60',     text: 'text-red-300',     dot: 'bg-red-300'     },
  SENSOR_ERROR: { bg: 'bg-orange-900/20',  border: 'border-orange-600/40',  text: 'text-orange-400',  dot: 'bg-orange-400'  },
  BOOTING:      { bg: 'bg-slate-700/20',   border: 'border-slate-500/40',   text: 'text-slate-400',   dot: 'bg-slate-400'   },
}

export function statusColors(status) {
  return STATUS_COLORS[status] ?? STATUS_COLORS.BOOTING
}

export function fmtNum(v, decimals = 1) {
  if (v == null) return '—'
  return Number(v).toFixed(decimals)
}
