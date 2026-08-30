import React, { useState, useEffect, useRef } from 'react';
import { Search, X, TrendingUp, Building2, ChevronRight, Sparkles } from 'lucide-react';
import { searchTickers } from '../api/client';

const POPULAR_QUICK_PICKS = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN', 'SPY'];

export default function TickerSearch({ selectedTicker, onSelectTicker, isLoading }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const containerRef = useRef(null);
  const debounceTimer = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    setIsSearching(true);
    debounceTimer.current = setTimeout(async () => {
      try {
        const data = await searchTickers(query);
        setResults(data);
        setIsOpen(true);
      } catch (err) {
        console.error('Ticker search error:', err);
      } finally {
        setIsSearching(false);
      }
    }, 280);

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [query]);

  const handleSelect = (ticker) => {
    onSelectTicker(ticker.symbol);
    setQuery('');
    setIsOpen(false);
    setSelectedIndex(-1);
  };

  const handleKeyDown = (e) => {
    if (!isOpen || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(results[selectedIndex]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className="w-full space-y-3" ref={containerRef}>
      {/* Search Input Container */}
      <div className="relative">
        <div className="relative flex items-center">
          <Search className="absolute left-3.5 w-5 h-5 text-slate-400 pointer-events-none" />
          
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => {
              if (query.trim() || results.length > 0) setIsOpen(true);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search stock ticker or company name (e.g. AAPL, NVDA, Microsoft)..."
            className="w-full pl-11 pr-10 py-3 bg-slate-900/90 hover:bg-slate-900 focus:bg-slate-900 border border-slate-700/80 focus:border-cyan-500 rounded-xl text-white placeholder-slate-500 text-sm shadow-inner focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition"
          />

          {query && (
            <button
              onClick={() => {
                setQuery('');
                setResults([]);
                setIsOpen(false);
              }}
              className="absolute right-3.5 text-slate-400 hover:text-white p-0.5 rounded transition"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Autocomplete Dropdown */}
        {isOpen && results.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-1 duration-150 max-h-80 overflow-y-auto">
            <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase border-b border-slate-800 flex items-center justify-between">
              <span>Matching Symbols</span>
              {isSearching && <span className="text-cyan-400 text-[10px] animate-pulse">Searching...</span>}
            </div>

            <ul className="py-1">
              {results.map((item, idx) => {
                const isSelected = idx === selectedIndex;
                const isCurrent = item.symbol === selectedTicker;

                return (
                  <li key={`${item.symbol}-${idx}`}>
                    <button
                      type="button"
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`w-full px-4 py-2.5 flex items-center justify-between text-left transition cursor-pointer ${
                        isSelected ? 'bg-slate-800/80 text-white' : 'text-slate-300 hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-cyan-400">
                          {item.symbol.slice(0, 3)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white text-sm">{item.symbol}</span>
                            {isCurrent && (
                              <span className="text-[10px] bg-cyan-500/20 text-cyan-300 px-1.5 py-0.2 rounded font-medium">
                                Active
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-400 line-clamp-1">{item.name}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-right">
                        <span className="text-[11px] text-slate-500 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700/50">
                          {item.exchange}
                        </span>
                        <ChevronRight className="w-4 h-4 text-slate-500" />
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>

      {/* Quick Pick Popular Tickers */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-amber-400" /> Popular:
        </span>
        {POPULAR_QUICK_PICKS.map((sym) => {
          const isActive = sym === selectedTicker;
          return (
            <button
              key={sym}
              onClick={() => onSelectTicker(sym)}
              disabled={isLoading}
              className={`px-3 py-1 text-xs font-semibold rounded-lg border transition cursor-pointer ${
                isActive
                  ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-300 shadow-sm shadow-cyan-500/20'
                  : 'bg-slate-900/80 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 hover:bg-slate-800/50'
              }`}
            >
              {sym}
            </button>
          );
        })}
      </div>
    </div>
  );
}
