import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import DisclaimerModal from './components/DisclaimerModal';
import TickerSearch from './components/TickerSearch';
import TimeRangeSelector from './components/TimeRangeSelector';
import HorizonSelector from './components/HorizonSelector';
import StockChart from './components/StockChart';
import MetricsCard from './components/MetricsCard';
import TrainingProgress from './components/TrainingProgress';
import { fetchStockHistory, requestPrediction, checkJobStatus } from './api/client';
import { AlertCircle, X, ShieldAlert, Sparkles, RefreshCw } from 'lucide-react';

export default function App() {
  const [selectedTicker, setSelectedTicker] = useState('AAPL');
  const [timeRange, setTimeRange] = useState('1y');
  const [horizonDays, setHorizonDays] = useState(7);
  
  const [historyData, setHistoryData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [activeJob, setActiveJob] = useState(null);
  const [error, setError] = useState(null);
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);

  const pollIntervalRef = useRef(null);

  // Load history whenever ticker or timeRange changes
  useEffect(() => {
    let isCurrent = true;
    async function loadHistory() {
      setIsLoadingHistory(true);
      setError(null);
      try {
        const data = await fetchStockHistory(selectedTicker, timeRange);
        if (isCurrent) {
          setHistoryData(data);
        }
      } catch (err) {
        if (isCurrent) {
          setError(err.message || `Failed to fetch data for ${selectedTicker}`);
        }
      } finally {
        if (isCurrent) setIsLoadingHistory(false);
      }
    }

    loadHistory();
    return () => {
      isCurrent = false;
    };
  }, [selectedTicker, timeRange]);

  // Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Handle Predict request
  const handlePredict = async (forceRetrain = false) => {
    setIsPredicting(true);
    setError(null);

    try {
      const res = await requestPrediction(selectedTicker, horizonDays, forceRetrain);

      if (res.status === 'ready') {
        setForecastData(res);
        setIsPredicting(false);
      } else if (res.status === 'training' && res.job_id) {
        // Start polling job
        startJobPolling(res.job_id);
      }
    } catch (err) {
      setError(err.message || 'Forecast generation failed.');
      setIsPredicting(false);
    }
  };

  const startJobPolling = (jobId) => {
    setActiveJob({ job_id: jobId, ticker: selectedTicker, status: 'queued', progress: 5, stage: 'Queued...' });

    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(async () => {
      try {
        const jobStatus = await checkJobStatus(jobId);
        setActiveJob(jobStatus);

        if (jobStatus.status === 'done') {
          clearInterval(pollIntervalRef.current);
          setIsPredicting(false);
          if (jobStatus.prediction_result) {
            setForecastData(jobStatus.prediction_result);
          }
        } else if (jobStatus.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          setIsPredicting(false);
          setError(jobStatus.error || 'Model training failed.');
        }
      } catch (err) {
        console.error('Job polling error:', err);
      }
    }, 1500);
  };

  // Reset forecast when changing ticker
  const handleSelectTicker = (newTicker) => {
    if (newTicker !== selectedTicker) {
      setSelectedTicker(newTicker);
      setForecastData(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navbar Header */}
      <Header onOpenDisclaimer={() => setDisclaimerOpen(true)} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Banner Notice */}
        <div className="bg-gradient-to-r from-cyan-950/40 via-slate-900 to-indigo-950/40 border border-cyan-500/20 rounded-2xl p-4 flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-400 border border-cyan-500/20 shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold text-white">Interactive Deep Learning Forecasts: </span>
              <span className="text-slate-300">
                Trained with TensorFlow/Keras LSTM neural networks & evaluated against naive random-walk baselines.
              </span>
            </div>
          </div>
          <button
            onClick={() => setDisclaimerOpen(true)}
            className="hidden sm:inline-flex text-cyan-400 hover:text-cyan-300 font-semibold underline underline-offset-2 shrink-0 cursor-pointer"
          >
            Read Caveat
          </button>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 flex items-start justify-between gap-3 text-rose-300 text-sm animate-shake">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="font-bold text-rose-200">Error: </strong>
                <span>{error}</span>
              </div>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-rose-400 hover:text-rose-200 p-1 rounded-lg hover:bg-rose-500/20 transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Search & Top Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
          <div className="lg:col-span-2">
            <TickerSearch
              selectedTicker={selectedTicker}
              onSelectTicker={handleSelectTicker}
              isLoading={isLoadingHistory || isPredicting}
            />
          </div>
          <div className="flex justify-start lg:justify-end">
            <TimeRangeSelector
              selectedRange={timeRange}
              onSelectRange={setTimeRange}
              isLoading={isLoadingHistory}
            />
          </div>
        </div>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Interactive Stock Chart */}
          <div className="lg:col-span-2 space-y-6">
            <StockChart
              historyData={historyData}
              forecastData={forecastData}
              ticker={selectedTicker}
              currency={historyData?.currency || 'USD'}
            />

            {/* Validation Metrics Comparison Card */}
            {forecastData?.metrics && (
              <MetricsCard
                metrics={forecastData.metrics}
                ticker={selectedTicker}
              />
            )}
          </div>

          {/* Right Column: Prediction Controls & Meta */}
          <div className="space-y-6">
            <HorizonSelector
              selectedHorizon={horizonDays}
              onSelectHorizon={setHorizonDays}
              onPredict={() => handlePredict(false)}
              onRetrain={() => handlePredict(true)}
              isLoading={isLoadingHistory}
              isPredicting={isPredicting}
            />

            {/* Educational Info Card */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-3 text-xs text-slate-400">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                Forecasting Architecture
              </h4>
              <p className="leading-relaxed">
                The model uses a <strong className="text-slate-300">sliding 60-day sequence window</strong> of normalized closing prices. Multi-step forecasts are computed autoregressively by rolling the output forward step-by-step.
              </p>
              <div className="pt-2 border-t border-slate-800 space-y-1.5 font-mono text-[11px] text-slate-500">
                <div>Framework: FastAPI + TensorFlow / Keras 3</div>
                <div>Model: Stacked LSTM + Dropout (0.2) + Dense</div>
                <div>Optimizer: Adam (lr=0.001, loss=MSE)</div>
              </div>
            </div>
          </div>

        </div>

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500 bg-slate-950">
        <p>Stock Price Prediction LSTM Web Application • Built with FastAPI, TensorFlow, & React</p>
        <p className="mt-1 text-[11px] text-slate-600">Educational demonstration only. Not investment or financial advice.</p>
      </footer>

      {/* Background Training Progress Modal */}
      {activeJob && (
        <TrainingProgress
          job={activeJob}
          onDismiss={() => setActiveJob(null)}
        />
      )}

      {/* Financial Disclaimer Modal */}
      <DisclaimerModal
        isOpen={disclaimerOpen}
        onClose={() => setDisclaimerOpen(false)}
      />
    </div>
  );
}
