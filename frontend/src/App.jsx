import { useApiData } from './hooks/useApiData';
import AlertBanner from './components/AlertBanner';
import FloorMap from './components/FloorMap';
import NodeCard from './components/NodeCard';
import SimControls from './components/SimControls';
import LogPanel from './components/LogPanel';
import { statusColors } from './utils/colors';
import { Shield, Activity, Map as MapIcon, Sliders as SlidersIcon, Terminal } from 'lucide-react';

function App() {
  const { data, error } = useApiData();

  if (error) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-8 text-center">
        <div className="bg-red-900/20 border border-red-500/30 p-8 rounded-2xl max-w-md">
          <Shield size={48} className="text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-red-100 mb-2">Backend Offline</h1>
          <p className="text-red-300/70 text-sm mb-6">Unable to connect to AEGIS logic service at :5000</p>
          <code className="block bg-black/40 p-3 rounded font-mono text-xs text-red-400">{error}</code>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center justify-center gap-4 text-muted">
        <Activity size={32} className="animate-spin text-blue-500" />
        <span className="text-sm font-medium tracking-widest uppercase animate-pulse">Initializing AEGIS System...</span>
      </div>
    );
  }

  const bColors = statusColors(data.building_status);

  return (
    <div className="min-h-screen bg-surface selection:bg-blue-500/30">
      <AlertBanner alerts={data.alerts} />

      {/* Header */}
      <header className="border-b border-border/60 bg-card/30 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-screen-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-900/50">
              <Shield className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight leading-none uppercase">AEGIS</h1>
              <p className="text-[10px] text-muted font-bold tracking-widest leading-none mt-1">EMERGENCY EXIT GUIDANCE SYSTEM v2.0</p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-muted font-bold tracking-tighter uppercase whitespace-nowrap">BUILDING STATUS</span>
              <div className="flex items-center gap-2 mt-0.5">
                <div className={`w-2.5 h-2.5 rounded-full ${bColors.dot} ${data.building_status === 'CRITICAL' || data.building_status === 'DANGER' ? 'animate-ping' : ''}`} />
                <span className={`text-sm font-black tracking-tight ${bColors.text}`}>{data.building_status}</span>
              </div>
            </div>
            
            <div className="h-10 w-px bg-border/40 hidden sm:block" />
            
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-[10px] text-muted font-bold tracking-tighter uppercase">SYSTEM TIME</span>
              <span className="text-sm font-mono font-medium text-zinc-300 mt-0.5">{data.ts?.split('T')[1]}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column - Visual Map */}
        <div className="lg:col-span-8 flex flex-col gap-8">
          <section className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <MapIcon size={18} className="text-blue-400" />
              <h2 className="text-sm font-bold uppercase tracking-tight text-zinc-100">Floor Overview & Signage Routing</h2>
            </div>
            <FloorMap nodes={data.nodes} signs={data.signs} />
          </section>

          <section className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Terminal size={18} className="text-zinc-400" />
              <h2 className="text-sm font-bold uppercase tracking-tight text-zinc-100">System Logs & Event Stream</h2>
            </div>
            <LogPanel />
          </section>
        </div>

        {/* Right Column - Controls & Cards */}
        <div className="lg:col-span-4 flex flex-col gap-8">
          
          <section className="space-y-4">
             <div className="flex items-center gap-2 mb-2">
              <SlidersIcon size={18} className="text-blue-400" />
              <h2 className="text-sm font-bold uppercase tracking-tight text-zinc-100">Sensor Overrides</h2>
            </div>
            <SimControls nodes={data.nodes} />
          </section>

          <section className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={18} className="text-zinc-400" />
              <h2 className="text-sm font-bold uppercase tracking-tight text-zinc-100">Live Node Telemetry</h2>
            </div>
            <div className="grid grid-cols-1 gap-4 overflow-y-auto max-h-[800px] pr-2 custom-scrollbar">
              {Object.values(data.nodes).sort((a,b) => b.floor - a.floor).map(n => (
                <NodeCard key={n.node_id} node={n} gpio={data.gpio_leds[n.node_id]} />
              ))}
            </div>
          </section>
        </div>

      </main>

      <footer className="max-w-screen-2xl mx-auto px-6 py-12 border-t border-border/20 text-center">
        <p className="text-[10px] text-zinc-600 font-bold tracking-widest">
           3-FLOOR ARCHITECTURE • HYBRID HARDWARE MODEL • DESIGNED FOR HIGH RELIABILITY
        </p>
      </footer>
    </div>
  );
}

export default App;
