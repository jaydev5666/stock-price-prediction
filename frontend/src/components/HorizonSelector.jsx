import React from 'react';
import { Sparkles, RefreshCw, Cpu, Clock } from 'lucide-react';

const HORIZONS = [
  { label: '7 Days', days: 7, desc: 'Short-term forecast' },
  { label: '14 Days', days: 14, desc: '2-week projection' },
  { label: '30 Days', days: 30, desc: 'Monthly outlook' },
];

export default function HorizonSelector({
  selectedHorizon,
  onSelectHorizon,
  onPredict,
  onRetrain,
  isLoading,
  isPredicting
}) {
  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-cyan-500/10 rounded-lg text-cyan-400 border border-cyan-500/20">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">LSTM Forecast Horizon</h3>
            <p className="text-xs text-slate-400">Select multi-step projection window</p>
          </div>
        </div>
      </div>

      {/* Horizon Buttons */}
      <div className="grid grid-cols-3 gap-2.5">
        {HORIZONS.map((h) => {
          const isActive = selectedHorizon === h.days;
          return (
            <button
              key={h.days}
              onClick={() => onSelectHorizon(h.days)}
              disabled={isLoading || isPredicting}
              className={`p-3 rounded-xl border text-left transition relative cursor-pointer ${
                isActive
                  ? 'bg-gradient-to-b from-cyan-950/60 to-slate-900 border-cyan-500/60 text-white shadow-lg shadow-cyan-500/10'
                  : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 hover:bg-slate-900/50'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-sm font-bold ${isActive ? 'text-cyan-400' : 'text-slate-200'}`}>
                  {h.label}
                </span>
                {isActive && (
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-sm shadow-cyan-400" />
                )}
              </div>
              <span className="text-[11px] text-slate-500 block">{h.desc}</span>
            </button>
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center gap-2.5 pt-1">
        <button
          onClick={() => onPredict(false)}
          disabled={isLoading || isPredicting}
          className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/25 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          {isPredicting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin text-white" />
              <span>Forecasting with LSTM...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-cyan-200" />
              <span>Generate {selectedHorizon}-Day Forecast</span>
            </>
          )}
        </button>

        <button
          onClick={() => onRetrain()}
          disabled={isLoading || isPredicting}
          title="Force fresh LSTM model training on latest 5-year history"
          className="w-full sm:w-auto py-3 px-4 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white font-medium text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
          <span className="whitespace-nowrap">Retrain Model</span>
        </button>
      </div>
    </div>
  );
}
