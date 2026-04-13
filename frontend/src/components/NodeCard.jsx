import { Thermometer, Wind, Users, Video, Info } from 'lucide-react';
import { statusColors, fmtNum } from '../utils/colors';

export default function NodeCard({ node, gpio }) {
  const colors = statusColors(node.status);
  
  return (
    <div className={`p-4 rounded-xl border transition-all duration-300 ${colors.bg} ${colors.border}`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h4 className="font-bold text-sm tracking-tight">{node.label}</h4>
          <span className="text-[10px] text-muted flex items-center gap-1 uppercase tracking-widest leading-none mt-1">
            Floor {node.floor} • {node.source}
          </span>
        </div>
        <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${colors.text} border ${colors.border}`}>
          {node.status}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <DataPoint icon={<Thermometer size={14} />} label="Temp" value={fmtNum(node.temp)} unit="°C" />
        <DataPoint icon={<Wind size={14} />} label="Smoke" value={fmtNum(node.smoke, 2)} unit="V" />
        <DataPoint icon={<Users size={14} />} label="Crowd" value={node.crowd} unit="/ 10" />
        <DataPoint icon={<Video size={14} />} label="Risk" value={fmtNum(node.risk, 0)} unit="%" highlight={node.risk > 40} />
      </div>

      {node.has_gpio_led && gpio && (
        <div className="mt-2 pt-3 border-t border-border/50 flex items-center justify-between">
          <span className="text-[10px] text-muted font-bold uppercase tracking-tighter">GPIO LED</span>
          <div className="flex gap-2">
            <div className={`w-3 h-3 rounded-full ${gpio.green_on ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-zinc-800'} ${gpio.blink_hz === 1 ? 'animate-blink' : ''}`} />
            <div className={`w-3 h-3 rounded-full ${gpio.red_on ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]' : 'bg-zinc-800'} ${gpio.blink_hz === 2 ? 'animate-blink' : ''}`} />
          </div>
        </div>
      )}
      
      {node.node_id === 'exit_A' && (
        <div className="mt-3 aspect-video bg-black rounded-lg overflow-hidden border border-border group relative">
          <img 
            src={`/api/video/exit_A?t=${Date.now()}`} 
            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" 
            alt="Real Webcam"
          />
          <div className="absolute top-2 left-2 bg-black/60 px-1.5 py-0.5 rounded text-[8px] font-mono text-white flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" /> LIVE
          </div>
        </div>
      )}
    </div>
  );
}

function DataPoint({ icon, label, value, unit, highlight }) {
  return (
    <div className="bg-card/40 p-2 rounded-lg border border-border/40">
      <div className="flex items-center gap-1.5 text-muted mb-1">
        {icon}
        <span className="text-[10px] uppercase font-bold tracking-tighter leading-none">{label}</span>
      </div>
      <div className={`text-sm font-mono whitespace-nowrap ${highlight ? 'text-red-400 font-bold' : ''}`}>
        {value} <span className="text-[10px] opacity-60 font-sans">{unit}</span>
      </div>
    </div>
  );
}
