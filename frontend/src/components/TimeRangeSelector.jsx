import React from 'react';
import { Calendar } from 'lucide-react';

const RANGES = [
  { label: '1M', value: '1m' },
  { label: '6M', value: '6m' },
  { label: '1Y', value: '1y' },
  { label: '5Y', value: '5y' },
];

export default function TimeRangeSelector({ selectedRange, onSelectRange, isLoading }) {
  return (
    <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 p-1 rounded-xl">
      <div className="px-2 text-slate-500 flex items-center">
        <Calendar className="w-3.5 h-3.5" />
      </div>
      {RANGES.map((r) => {
        const active = r.value === selectedRange;
        return (
          <button
            key={r.value}
            onClick={() => onSelectRange(r.value)}
            disabled={isLoading}
            className={`px-3 py-1.2 text-xs font-semibold rounded-lg transition cursor-pointer ${
              active
                ? 'bg-slate-800 text-cyan-400 border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            {r.label}
          </button>
        );
      })}
    </div>
  );
}
