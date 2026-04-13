import { useState, useEffect } from 'react';
import { Sliders, RefreshCw } from 'lucide-react';

export default function SimControls({ nodes }) {
  const [activeNode, setActiveNode] = useState(null);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(false);

  // Initial fetch of slider states
  useEffect(() => {
    fetch('/api/sliders')
      .then(r => r.json())
      .then(d => {
        setValues(d);
        if (!activeNode) setActiveNode(Object.keys(d)[0]);
      });
  }, []);

  const handleOverride = async (nid, field, val) => {
    // Update local state immediately for snappy feel
    setValues(prev => ({
      ...prev,
      [nid]: { ...prev[nid], [field]: val }
    }));

    try {
      await fetch('/api/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nid, field, value: val })
      });
    } catch (e) {
      console.error("Override failed", e);
    }
  };

  const currentValues = values[activeNode] || {};

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Sliders size={18} className="text-blue-400" />
          <h3 className="font-bold text-sm tracking-tight">Manual Simulation Controls</h3>
        </div>
        <div className="text-[10px] text-muted-foreground bg-secondary px-2 py-0.5 rounded">
          OPERATOR OVERRIDE
        </div>
      </div>

      {/* Node Selector Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {Object.keys(values).sort().map(nid => (
          <button
            key={nid}
            onClick={() => setActiveNode(nid)}
            className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all ${activeNode === nid
                ? 'bg-blue-600 text-white shadow-md shadow-blue-900/40'
                : 'bg-card border border-border text-muted hover:border-muted'
              }`}
          >
            {nid}
          </button>
        ))}
      </div>

      {activeNode ? (
        <div className="space-y-6">
          <SliderRow
            label="Ambient Temperature"
            icon="🌡️"
            unit="°C"
            value={currentValues.temp}
            min={0} max={100} step={0.5}
            onChange={(v) => handleOverride(activeNode, 'temp', v)}
          />
          <SliderRow
            label="Smoke Voltage (ADC)"
            icon="💨"
            unit="V"
            value={currentValues.smoke}
            min={0} max={5} step={0.05}
            onChange={(v) => handleOverride(activeNode, 'smoke', v)}
          />
          <SliderRow
            label="Crowd Concentration"
            icon="👥"
            unit="/10"
            value={currentValues.crowd}
            min={0} max={10} step={1}
            onChange={(v) => handleOverride(activeNode, 'crowd', v)}
          />

          <div className="bg-zinc-900/50 p-3 rounded-lg border border-border/40">
            <p className="text-[9px] text-muted-foreground leading-relaxed italic">
              * Simulated nodes take values directly from these sliders.
              Real nodes (exit_A, B, F2) only use the Crowd slider; temp/smoke are hardware-driven.
            </p>
          </div>
        </div>
      ) : (
        <div className="h-40 flex items-center justify-center text-muted text-xs animate-pulse">
          Loading simulator nodes...
        </div>
      )}
    </div>
  );
}

function SliderRow({ label, icon, unit, value, min, max, step, onChange }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-tight">
        <span className="text-muted flex items-center gap-1.5">{icon} {label}</span>
        <span className="text-blue-400">{value} <span className="opacity-50">{unit}</span></span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value || 0}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400 outline-none transition-all"
      />
      <div className="flex justify-between text-[8px] text-muted-foreground/40 font-mono">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
