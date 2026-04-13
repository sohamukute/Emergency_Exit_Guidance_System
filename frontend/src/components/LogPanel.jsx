import { useState, useEffect, useRef } from 'react';
import { Terminal, Database, Globe } from 'lucide-react';

export default function LogPanel() {
  const [logs, setLogs] = useState({ sensors: [], api: [] });
  const [activeTab, setActiveTab] = useState('sensors');
  const scrollRef = useRef(null);

  const fetchLogs = async () => {
    try {
      const [sRes, aRes] = await Promise.all([
        fetch('/api/logs/sensors'),
        fetch('/api/logs/api')
      ]);
      const sData = await sRes.json();
      const aData = await aRes.json();
      setLogs({ sensors: sData, api: aData });
    } catch (e) {
      console.error("Log fetch failed", e);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, activeTab]);

  const currentLogs = activeTab === 'sensors' ? logs.sensors : logs.api;

  return (
    <div className="bg-zinc-950 border border-border rounded-xl flex flex-col h-[500px] overflow-hidden shadow-xl">
      <div className="flex bg-zinc-900 border-b border-border p-1">
        <button
          onClick={() => setActiveTab('sensors')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            activeTab === 'sensors' ? 'bg-zinc-800 text-blue-400' : 'text-muted hover:text-white'
          }`}
        >
          <Database size={14} /> SENSOR LOGS
        </button>
        <button
          onClick={() => setActiveTab('api')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            activeTab === 'api' ? 'bg-zinc-800 text-purple-400' : 'text-muted hover:text-white'
          }`}
        >
          <Globe size={14} /> SYSTEM API
        </button>
      </div>

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-[10px] space-y-1.5 scroll-smooth"
      >
        {currentLogs.length === 0 ? (
          <div className="text-zinc-700 italic">No logs captured yet...</div>
        ) : (
          currentLogs.map((log, i) => (
            <div key={i} className="flex gap-3 leading-relaxed border-b border-white/[0.03] pb-1">
              <span className="text-zinc-600 shrink-0">[{log.ts.split('T')[1]}]</span>
              <span className={`font-bold shrink-0 w-12 ${
                log.level === 'ERROR' ? 'text-red-500' : 
                log.level === 'WARN' ? 'text-amber-500' : 'text-zinc-400'
              }`}>
                {log.level}
              </span>
              <span className="text-zinc-300 break-all">{log.msg}</span>
            </div>
          ))
        )}
      </div>

      <div className="bg-zinc-900 border-t border-border px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] text-zinc-500 uppercase tracking-tighter">
          <Terminal size={12} /> Live Terminal Output
        </div>
        <div className="text-[10px] text-zinc-600">
          Showing last 500 entries
        </div>
      </div>
    </div>
  );
}
