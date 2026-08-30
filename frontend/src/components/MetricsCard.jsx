import React from 'react';
import { Award, BarChart3, TrendingUp, HelpCircle, Layers, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function MetricsCard({ metrics, ticker }) {
  if (!metrics) return null;

  const rmse = metrics.rmse;
  const mae = metrics.mae;
  const baselineRmse = metrics.baseline_rmse;
  const baselineMae = metrics.baseline_mae;
  const dirAcc = metrics.directional_accuracy;
  const improvement = metrics.rmse_improvement_pct;

  const beatsBaseline = improvement !== null && improvement !== undefined && improvement > 0;

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
      {/* Card Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-indigo-500/10 rounded-lg text-indigo-400 border border-indigo-500/20">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Validation Quality & Baseline Comparison</h3>
            <p className="text-xs text-slate-400">Evaluated on held-out chronological test split</p>
          </div>
        </div>

        {/* Status Badge */}
        {improvement !== null && improvement !== undefined && (
          <span
            className={`px-2.5 py-1 text-xs font-semibold rounded-full border flex items-center gap-1.5 ${
              beatsBaseline
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            }`}
          >
            {beatsBaseline ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" /> Outperforming Baseline (+{improvement}%)
              </>
            ) : (
              <>
                <AlertTriangle className="w-3.5 h-3.5" /> Random-Walk Baseline Parity
              </>
            )}
          </span>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        
        {/* LSTM RMSE */}
        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            LSTM RMSE
          </span>
          <div className="text-lg font-extrabold text-cyan-400 font-mono">
            ${rmse.toFixed(2)}
          </div>
          <span className="text-[10px] text-slate-500 block">Root Mean Squared Error</span>
        </div>

        {/* Baseline RMSE */}
        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Naive Baseline RMSE
          </span>
          <div className="text-lg font-extrabold text-slate-300 font-mono">
            ${baselineRmse.toFixed(2)}
          </div>
          <span className="text-[10px] text-slate-500 block">Predicting Tomorrow = Today</span>
        </div>

        {/* LSTM MAE */}
        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            LSTM MAE
          </span>
          <div className="text-lg font-extrabold text-indigo-400 font-mono">
            ${mae.toFixed(2)}
          </div>
          <span className="text-[10px] text-slate-500 block">Mean Absolute Error</span>
        </div>

        {/* Directional Accuracy */}
        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Directional Accuracy
          </span>
          <div className="text-lg font-extrabold text-emerald-400 font-mono">
            {dirAcc ? `${dirAcc.toFixed(1)}%` : '50.0%'}
          </div>
          <span className="text-[10px] text-slate-500 block">Up/Down Sign Agreement</span>
        </div>

      </div>

      {/* Educational Note on Baseline */}
      <div className="text-xs text-slate-400 bg-slate-950/40 p-3 rounded-xl border border-slate-800/50 flex items-start gap-2.5">
        <HelpCircle className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
        <p className="leading-relaxed">
          <strong className="text-slate-300">Why Baseline Comparison Matters:</strong> Financial prices often resemble martingales where the single best naive forecast is the previous day's close. Showing this baseline comparison tests whether the recurrent neural network captures genuine sequential structure beyond trivial persistence.
        </p>
      </div>
    </div>
  );
}
