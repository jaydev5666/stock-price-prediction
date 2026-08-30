import React from 'react';
import { Cpu, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function TrainingProgress({ job, onDismiss }) {
  if (!job) return null;

  const isFailed = job.status === 'failed';
  const isDone = job.status === 'done';
  const progress = Math.min(100, Math.max(5, job.progress || 5));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 text-slate-200 relative">
        
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className={`p-3 rounded-xl border ${
            isFailed
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
              : isDone
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
          }`}>
            {isFailed ? (
              <AlertCircle className="w-6 h-6" />
            ) : isDone ? (
              <CheckCircle2 className="w-6 h-6" />
            ) : (
              <Cpu className="w-6 h-6 animate-pulse" />
            )}
          </div>

          <div>
            <h3 className="text-base font-bold text-white">
              {isFailed
                ? `Training Failed for ${job.ticker}`
                : isDone
                ? `Model Trained for ${job.ticker}`
                : `Training LSTM Model for ${job.ticker}`}
            </h3>
            <p className="text-xs text-slate-400">
              {isFailed
                ? 'An error occurred during asynchronous training'
                : isDone
                ? 'Model ready & forecast generated'
                : 'Asynchronous background neural network optimization'}
            </p>
          </div>
        </div>

        {/* Progress Bar & Stage Message */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold">
            <span className="text-slate-300 flex items-center gap-1.5">
              {!isDone && !isFailed && <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />}
              {job.stage || 'Initializing training worker...'}
            </span>
            <span className="text-cyan-400 font-mono">{progress}%</span>
          </div>

          <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden border border-slate-700/50 p-0.5">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                isFailed
                  ? 'bg-rose-500'
                  : isDone
                  ? 'bg-emerald-500'
                  : 'bg-gradient-to-r from-cyan-500 to-blue-500 animate-pulse'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Pipeline Details */}
        <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80 space-y-1.5 text-xs text-slate-400">
          <div className="flex items-center justify-between">
            <span>Job ID:</span>
            <span className="font-mono text-slate-300">{job.job_id}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Architecture:</span>
            <span className="text-slate-300">2-Layer Stacked LSTM (64/32 units)</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Lookback Window:</span>
            <span className="text-slate-300">60 Historical Trading Days</span>
          </div>
        </div>

        {/* Error message if failed */}
        {isFailed && job.error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300 leading-relaxed">
            {job.error}
          </div>
        )}

        {/* Dismiss Button */}
        {(isFailed || isDone) && (
          <div className="flex justify-end pt-1">
            <button
              onClick={onDismiss}
              className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs transition cursor-pointer"
            >
              Close
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
