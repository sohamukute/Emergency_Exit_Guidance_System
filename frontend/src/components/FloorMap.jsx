import React from 'react';
import { statusColors } from '../utils/colors';

const SIGN_COLORS = {
  safe:    'text-emerald-500 fill-emerald-500',
  caution: 'text-amber-500 fill-amber-500',
  blocked: 'text-red-500 fill-red-500',
  stairs:  'text-blue-500 fill-blue-500 animate-pulse',
};

function SignIcon({ state, className }) {
  if (state === 'blocked') {
    return <svg viewBox="0 0 24 24" className={`w-6 h-6 ${className} stroke-current fill-none`} strokeWidth="3"><path d="M18 6L6 18M6 6l12 12" /></svg>;
  }
  if (state === 'stairs') {
    return (
      <svg viewBox="0 0 24 24" className={`w-6 h-6 ${className} fill-current`}>
        <path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM11 14h2v3h-2v-3zm0-7h2v5h-2V7z" />
      </svg>
    );
  }
  // arrow toward side
  const rotate = className.includes('rotate-180') ? 'rotate-180' : '';
  return (
    <svg viewBox="0 0 24 24" className={`w-6 h-6 ${className} fill-current`}>
      <path d="M16.01 11H4v2h12.01v3L20 12l-3.99-4v3z" />
    </svg>
  );
}

export default function FloorMap({ nodes, signs }) {
  if (!nodes || !signs) return <div className="animate-pulse bg-card h-96 rounded-xl border border-border" />;

  const floors = [
    { id: 2, name: 'Floor 2 (Physical Hardware)', nodes: ['exit_A', 'mid_F2', 'exit_B'], signs: ['1L', '1R', '2L', '2R'] },
    { id: 1, name: 'Floor 1 (Simulated)', nodes: ['exit_C', 'mid_F1', 'exit_D'], signs: ['3L', '3R', '4L', '4R'] },
    { id: 0, name: 'Ground Floor (Simulated)', nodes: ['exit_E', 'main_exit', 'exit_F'], signs: ['5L', '5R', '6L', '6R'] },
  ];

  return (
    <div className="flex flex-col gap-8">
      {floors.map((floor) => (
        <div key={floor.id} className="relative bg-card/50 border border-border/50 rounded-2xl p-6 overflow-hidden">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-muted text-sm font-medium uppercase tracking-wider">{floor.name}</h3>
            {floor.id > 0 && (
              <div className="flex items-center gap-1 text-[10px] text-blue-400/80 border border-blue-400/30 px-2 py-0.5 rounded bg-blue-400/10">
                <span>STAIRWELL CONNECTION</span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-4 max-w-4xl mx-auto relative">
            {/* Floor nodes */}
            {floor.nodes.map((nid, i) => {
              const node = nodes[nid];
              const colors = statusColors(node?.status);
              return (
                <React.Fragment key={nid}>
                  {/* The Node Block */}
                  <div className={`relative flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all duration-300 min-w-32 ${colors.border} ${colors.bg}`}>
                    <div className={`w-3 h-3 rounded-full mb-2 ${colors.dot} shadow-[0_0_12px_rgba(0,0,0,0.5)] ${node?.status === 'CRITICAL' ? 'animate-ping' : ''}`} />
                    <span className="text-xs font-bold whitespace-nowrap">{node?.label}</span>
                    <span className={`text-[10px] font-medium mt-1 ${colors.text}`}>{node?.status}</span>
                  </div>

                  {/* The Inter-Node Signs Area */}
                  {i < floor.nodes.length - 1 && (
                    <div className="flex-1 flex justify-center items-center gap-4 relative">
                      <div className="h-0.5 bg-border flex-1" />
                      <div className="flex flex-col gap-2 scale-110">
                        {/* 1L/1R, 3L/3R, 5L/5R style layout */}
                        <div className="flex gap-4">
                          <SignIcon state={signs[floor.signs[i*2]]} className={`${SIGN_COLORS[signs[floor.signs[i*2]]]} rotate-180`} />
                          <SignIcon state={signs[floor.signs[i*2 + 1]]} className={`${SIGN_COLORS[signs[floor.signs[i*2 + 1]]]}`} />
                        </div>
                      </div>
                      <div className="h-0.5 bg-border flex-1" />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Vertical Stairwell links indicator */}
          {floor.id > 0 && (
            <div className="absolute left-1/2 bottom-0 w-0.5 h-4 bg-gradient-to-t from-blue-500/50 to-transparent -translate-x-1/2" />
          )}
          {floor.id < 2 && (
            <div className="absolute left-1/2 top-0 w-0.5 h-4 bg-gradient-to-b from-blue-500/50 to-transparent -translate-x-1/2" />
          )}
        </div>
      ))}
    </div>
  );
}
