import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine
} from 'recharts';
import { TrendingUp, TrendingDown, Clock, Sparkles } from 'lucide-react';

const CustomTooltip = ({ active, payload, label, currency = 'USD' }) => {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0]?.payload;
  if (!data) return null;

  const isForecast = !!data.isForecast;

  return (
    <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-3 shadow-2xl text-xs space-y-2 max-w-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 font-semibold text-slate-300">
        <span>{data.date}</span>
        {isForecast ? (
          <span className="text-[10px] bg-cyan-500/20 text-cyan-300 px-1.5 py-0.5 rounded font-medium border border-cyan-500/30 flex items-center gap-1">
            <Sparkles className="w-2.5 h-2.5" /> LSTM Forecast
          </span>
        ) : (
          <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
            Historical Actual
          </span>
        )}
      </div>

      {isForecast ? (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Predicted Close:</span>
            <span className="text-cyan-400 font-bold font-mono">
              ${data.predictedClose?.toFixed(2)} {currency}
            </span>
          </div>
          {data.lowerBound !== undefined && data.upperBound !== undefined && (
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Uncertainty Range:</span>
              <span className="text-slate-400 font-mono">
                ${data.lowerBound?.toFixed(2)} - ${data.upperBound?.toFixed(2)}
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Close:</span>
            <span className="text-white font-bold font-mono">
              ${data.close?.toFixed(2)}
            </span>
          </div>
          {data.open !== undefined && (
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-slate-400 pt-1">
              <div>Open: <span className="text-slate-200 font-mono">${data.open?.toFixed(2)}</span></div>
              <div>High: <span className="text-slate-200 font-mono">${data.high?.toFixed(2)}</span></div>
              <div>Low: <span className="text-slate-200 font-mono">${data.low?.toFixed(2)}</span></div>
              <div>Vol: <span className="text-slate-200 font-mono">{formatVolume(data.volume)}</span></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

function formatVolume(val) {
  if (!val) return '0';
  if (val >= 1e9) return (val / 1e9).toFixed(2) + 'B';
  if (val >= 1e6) return (val / 1e6).toFixed(2) + 'M';
  if (val >= 1e3) return (val / 1e3).toFixed(1) + 'K';
  return val.toString();
}

export default function StockChart({
  historyData,
  forecastData,
  ticker,
  currency = 'USD'
}) {
  const points = historyData?.points || [];
  const predictions = forecastData?.predictions || [];

  // Compute stats
  const stats = useMemo(() => {
    if (!points || points.length === 0) return null;
    const first = points[0];
    const last = points[points.length - 1];
    const change = last.close - first.close;
    const changePct = (change / first.close) * 100;
    const isPositive = change >= 0;

    let minPrice = Infinity;
    let maxPrice = -Infinity;
    points.forEach((p) => {
      if (p.low < minPrice) minPrice = p.low;
      if (p.high > maxPrice) maxPrice = p.high;
    });

    return {
      currentPrice: last.close,
      change,
      changePct,
      isPositive,
      minPrice,
      maxPrice,
      lastDate: last.date
    };
  }, [points]);

  // Combine historical and prediction points for unified chart plotting
  const chartData = useMemo(() => {
    if (!points || points.length === 0) return [];

    const combined = points.map((p) => ({
      date: p.date,
      close: p.close,
      open: p.open,
      high: p.high,
      low: p.low,
      volume: p.volume,
      isForecast: false
    }));

    if (predictions && predictions.length > 0) {
      const lastHist = combined[combined.length - 1];
      // Set predictedClose on the last historical point so the forecast line connects smoothly
      lastHist.predictedClose = lastHist.close;
      lastHist.lowerBound = lastHist.close;
      lastHist.upperBound = lastHist.close;

      predictions.forEach((pred) => {
        combined.push({
          date: pred.date,
          close: null,
          predictedClose: pred.predicted_close,
          lowerBound: pred.lower_bound,
          upperBound: pred.upper_bound,
          isForecast: true
        });
      });
    }

    return combined;
  }, [points, predictions]);

  // Determine Y-axis domain
  const yDomain = useMemo(() => {
    if (!chartData || chartData.length === 0) return ['auto', 'auto'];

    let min = Infinity;
    let max = -Infinity;

    chartData.forEach((d) => {
      if (d.close !== null && d.close !== undefined) {
        if (d.close < min) min = d.close;
        if (d.close > max) max = d.close;
      }
      if (d.predictedClose !== null && d.predictedClose !== undefined) {
        if (d.predictedClose < min) min = d.predictedClose;
        if (d.predictedClose > max) max = d.predictedClose;
      }
      if (d.lowerBound !== null && d.lowerBound !== undefined && d.lowerBound < min) {
        min = d.lowerBound;
      }
      if (d.upperBound !== null && d.upperBound !== undefined && d.upperBound > max) {
        max = d.upperBound;
      }
    });

    const padding = (max - min) * 0.08 || 1;
    return [Math.floor(Math.max(0, min - padding)), Math.ceil(max + padding)];
  }, [chartData]);

  if (!points || points.length === 0) {
    return (
      <div className="h-96 flex flex-col items-center justify-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-2xl">
        <Clock className="w-8 h-8 mb-2 animate-spin text-cyan-400" />
        <p className="text-sm">Loading market price history...</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-extrabold text-white tracking-tight">{ticker}</h2>
            <span className="text-xs text-slate-400 font-medium bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
              {historyData?.name || ticker}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">Last updated: {stats?.lastDate}</p>
        </div>

        {stats && (
          <div className="flex items-baseline gap-3">
            <div className="text-2xl font-black text-white font-mono">
              ${stats.currentPrice.toFixed(2)}
            </div>
            <div
              className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-lg border ${
                stats.isPositive
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
            >
              {stats.isPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
              <span>
                {stats.isPositive ? '+' : ''}
                {stats.change.toFixed(2)} ({stats.isPositive ? '+' : ''}
                {stats.changePct.toFixed(2)}%)
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Chart Legend Summary */}
      <div className="flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-blue-500 inline-block rounded" />
          <span className="text-slate-300">Historical Close</span>
        </div>
        {predictions && predictions.length > 0 && (
          <>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-t-2 border-dashed border-cyan-400 inline-block" />
              <span className="text-cyan-300 font-medium">LSTM Forecast ({forecastData?.horizon_days}d)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-2 bg-cyan-500/20 border border-cyan-500/40 inline-block rounded-xs" />
              <span className="text-slate-400">95% Uncertainty Band</span>
            </div>
          </>
        )}
      </div>

      {/* Main Chart Canvas */}
      <div className="h-80 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              {/* Historical price gradient */}
              <linearGradient id="histGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>

              {/* Forecast uncertainty band gradient */}
              <linearGradient id="forecastBand" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.05} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            
            <XAxis
              dataKey="date"
              stroke="#64748b"
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tick={{ fontSize: 11 }}
              minTickGap={30}
            />

            <YAxis
              domain={yDomain}
              stroke="#64748b"
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `$${v}`}
            />

            <Tooltip content={<CustomTooltip currency={currency} />} />

            {/* Historical Area */}
            <Area
              type="monotone"
              dataKey="close"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#histGradient)"
              isAnimationActive={false}
            />

            {/* Forecast Line */}
            <Line
              type="monotone"
              dataKey="predictedClose"
              stroke="#22d3ee"
              strokeWidth={2.5}
              strokeDasharray="5 5"
              dot={{ r: 3, fill: '#22d3ee', stroke: '#083344', strokeWidth: 1.5 }}
              activeDot={{ r: 5, fill: '#22d3ee', stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Uncertainty Notice */}
      {predictions && predictions.length > 0 && (
        <div className="text-[11px] text-slate-400 bg-slate-950/40 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between">
          <span>Forecast Horizon: {forecastData?.horizon_days} Trading Days</span>
          <span className="text-cyan-400/90 font-medium">Autoregressive Multi-Step Rollout</span>
        </div>
      )}
    </div>
  );
}
