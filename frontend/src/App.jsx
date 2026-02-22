import { useState } from 'react';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  // Settings State
  const [settings, setSettings] = useState({
    account_balance: 10000,
    default_risk_ratio: 0.01,
    fixed_loss_pct: 0.10,
    leverage_mode: 'VARIABLE',
    fixed_leverage: 10,
    fee_type: 'MARKET',
    exchange: 'BYBIT',
    api_key: '',
    api_secret: ''
  });

  // Trade Setup State
  const [tradeSetup, setTradeSetup] = useState({
    symbol: 'BTCUSDT',
    side: 'LONG',
    entry_price: 60000,
    tp_price: 65000,
    sl_price: 58000
  });

  // Results State
  const [results, setResults] = useState(null);
  const [signals, setSignals] = useState({});
  const [liqData, setLiqData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scannerActive, setScannerActive] = useState(false);

  // Poll for signals
  useEffect(() => {
    let interval;
    if (activeTab === 'dashboard') {
      const fetchSignals = async () => {
        try {
          const res = await fetch('http://localhost:8000/api/signals');
          if (res.ok) {
            const data = await res.json();
            setSignals(data);
          }
        } catch (e) { console.error(e); }
      };
      fetchSignals();
      interval = setInterval(fetchSignals, 10000);
    }
    return () => clearInterval(interval);
  }, [activeTab]);

  // Fetch Liq Map
  const fetchLiqMap = async (symbol) => {
    try {
      const res = await fetch(`http://localhost:8000/api/liq_map/${symbol}`);
      if (res.ok) {
        const data = await res.json();
        setLiqData(data);
      }
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    if (results?.symbol) {
      fetchLiqMap(results.symbol);
    }
  }, [results]);

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/history');
      if (res.ok) setHistory(await res.json());
      const resStats = await fetch('http://localhost:8000/api/stats');
      if (resStats.ok) setStats(await resStats.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    if (activeTab === 'journal') fetchHistory();
  }, [activeTab]);

  const runBacktest = async (symbol) => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/backtest?symbol=${symbol}`);
      if (res.ok) setBacktestResults(await res.json());
    } catch (e) { setError(`Backtest error: ${e.message}`); }
    setLoading(false);
  };

  const toggleScanner = async () => {
    const endpoint = scannerActive ? 'stop' : 'start';
    try {
      if (!scannerActive) {
        await fetch('http://localhost:8000/api/scanner/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ config: settings })
        });
      } else {
        await fetch('http://localhost:8000/api/scanner/stop', { method: 'POST' });
      }
      setScannerActive(!scannerActive);
    } catch (e) { setError(`Scanner error: ${e.message}`); }
  };

  // Settings Handlers
  const handleSettingChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: ['account_balance', 'default_risk_ratio', 'fixed_loss_pct', 'fixed_leverage'].includes(name)
        ? Number(value)
        : value
    }));
  };

  // Trade Setup Handlers
  const handleSetupChange = (e) => {
    const { name, value } = e.target;
    setTradeSetup(prev => ({
      ...prev,
      [name]: ['entry_price', 'tp_price', 'sl_price'].includes(name)
        ? Number(value)
        : value
    }));
  };

  // API Call
  const calculateRisk = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/calculate_risk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config: settings,
          setup: tradeSetup
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Calculation failed');

      setResults(data.calc);
      setValidation(data.validation);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Execution API Call
  const executeTrade = async () => {
    if (!results) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/execute_trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config: settings,
          setup: results,
          webhook_url: settings.webhook_url
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Execution failed');

      alert('Trade executed successfully!');
      fetchHistory(); // Refresh history
    } catch (err) {
      setError(`Execution Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-6">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <header className="flex items-center justify-between pb-6 border-b border-slate-800">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
              100x Auto-Trader
            </h1>
            <p className="text-slate-400 text-sm mt-1">Advanced Risk Calculator MVP</p>
          </div>

          <nav className="flex space-x-2 bg-slate-800/80 p-1 rounded-xl border border-slate-700 shadow-inner">
            <button onClick={() => setActiveTab('dashboard')} className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-all ${activeTab === 'dashboard' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>Dashboard</button>
            <button onClick={() => setActiveTab('journal')} className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-all ${activeTab === 'journal' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>Journal</button>
            <button onClick={() => setActiveTab('backtest')} className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-all ${activeTab === 'backtest' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>Backtest</button>
            <button onClick={() => setActiveTab('settings')} className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-all ${activeTab === 'settings' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>Settings</button>
          </nav>
        </header>

        {/* Content Tabs */}
        {activeTab === 'journal' && (
          <div className="space-y-8">
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-slate-800/40 p-6 rounded-2xl border border-slate-700 text-center">
                <div className="text-xs text-slate-400 uppercase tracking-widest mb-2">Win Rate</div>
                <div className="text-3xl font-bold text-green-400">{stats?.win_rate?.toFixed(1) || 0}%</div>
              </div>
              <div className="bg-slate-800/40 p-6 rounded-2xl border border-slate-700 text-center">
                <div className="text-xs text-slate-400 uppercase tracking-widest mb-2">Total PnL</div>
                <div className="text-3xl font-bold text-white">${stats?.total_pnl?.toFixed(2) || 0}</div>
              </div>
              <div className="bg-slate-800/40 p-6 rounded-2xl border border-slate-700 text-center">
                <div className="text-xs text-slate-400 uppercase tracking-widest mb-2">Trade Count</div>
                <div className="text-3xl font-bold text-slate-300">{stats?.trade_count || 0}</div>
              </div>
            </div>
            <div className="bg-slate-800/40 border border-slate-700 rounded-2xl shadow-lg overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900/80 text-slate-400">
                  <tr>
                    <th className="p-4">Date</th>
                    <th className="p-4">Symbol</th>
                    <th className="p-4">Side</th>
                    <th className="p-4">Entry</th>
                    <th className="p-4">Exit</th>
                    <th className="p-4">PnL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {history.map(t => (
                    <tr key={t.id} className="hover:bg-slate-700/30 transition-colors">
                      <td className="p-4 text-slate-400 font-mono text-xs">{new Date(t.created_at).toLocaleString()}</td>
                      <td className="p-4 font-bold text-slate-200">{t.symbol}</td>
                      <td className={`p-4 font-bold ${t.side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>{t.side}</td>
                      <td className="p-4">${t.entry_price}</td>
                      <td className="p-4">${t.exit_price || '-'}</td>
                      <td className={`p-4 font-bold ${t.pnl > 0 ? 'text-green-400' : t.pnl < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                        {t.pnl > 0 ? `+$${t.pnl.toFixed(2)}` : t.pnl < 0 ? `-$${Math.abs(t.pnl).toFixed(2)}` : '$0.00'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {history.length === 0 && <div className="p-12 text-center text-slate-500 italic text-sm">No trades found in history.</div>}
            </div>
          </div>
        )}

        {activeTab === 'backtest' && (
          <div className="space-y-8">
            <div className="bg-slate-800/40 border border-slate-700 p-6 rounded-2xl shadow-lg">
              <h2 className="text-lg font-semibold mb-6 text-slate-200 flex items-center">
                <svg className="w-5 h-5 mr-2 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
                Strategy Backtester
              </h2>
              <div className="flex gap-4">
                <div className="flex-grow">
                  <label className="block text-xs font-medium text-slate-400 mb-1">Target Symbol</label>
                  <input type="text" defaultValue="BTCUSDT" id="bt-symbol" className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white focus:outline-none" />
                </div>
                <button onClick={() => runBacktest(document.getElementById('bt-symbol').value)} className="self-end px-8 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition-all">
                  Run Simulation
                </button>
              </div>
            </div>

            {backtestResults && (
              <div className="space-y-6">
                <div className="grid grid-cols-3 gap-6">
                  <div className="bg-slate-900/60 p-5 rounded-xl border border-indigo-500/20 text-center">
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Win Rate</div>
                    <div className="text-2xl font-bold text-indigo-400">{backtestResults.stats.win_rate}%</div>
                  </div>
                  <div className="bg-slate-900/60 p-5 rounded-xl border border-indigo-500/20 text-center">
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Total Return</div>
                    <div className={`text-2xl font-bold ${backtestResults.stats.total_returns_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {backtestResults.stats.total_returns_pct}%
                    </div>
                  </div>
                  <div className="bg-slate-900/60 p-5 rounded-xl border border-indigo-500/20 text-center">
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Total Trades</div>
                    <div className="text-2xl font-bold text-slate-300">{backtestResults.stats.trade_count}</div>
                  </div>
                </div>

                <div className="bg-slate-800/40 border border-slate-700 rounded-2xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/80 text-slate-400 uppercase">
                      <tr>
                        <th className="p-3">Time</th>
                        <th className="p-3">Side</th>
                        <th className="p-3">Entry</th>
                        <th className="p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {backtestResults.trades.slice(0, 10).map((t, i) => (
                        <tr key={i} className="border-t border-slate-700/50">
                          <td className="p-3 text-slate-500">{t.timestamp.split(' ')[0]}</td>
                          <td className={`p-3 font-bold ${t.side === 'LONG' ? 'text-green-500' : 'text-red-500'}`}>{t.side}</td>
                          <td className="p-3">${t.entry_price.toFixed(2)}</td>
                          <td className={`p-3 font-bold ${t.status === 'PROFIT' ? 'text-green-400' : 'text-red-400'}`}>{t.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-2xl max-w-2xl mx-auto">
            <h2 className="text-xl font-semibold mb-6 text-blue-400">Trading Configuration</h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Account Balance ($)</label>
                <input type="number" name="account_balance" value={settings.account_balance} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2 focus:ring-1 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Exchange</label>
                <select name="exchange" value={settings.exchange} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm">
                  <option value="BYBIT">Bybit</option>
                  <option value="BINANCE">Binance</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Leverage Mode</label>
                <select name="leverage_mode" value={settings.leverage_mode} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm">
                  <option value="VARIABLE">Variable (Auto R1)</option>
                  <option value="FIXED">Fixed</option>
                </select>
              </div>

              {settings.leverage_mode === 'FIXED' && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Fixed Leverage (x)</label>
                  <input type="number" name="fixed_leverage" value={settings.fixed_leverage} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2" />
                </div>
              )}

              {settings.leverage_mode === 'VARIABLE' && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Fixed Loss % (Target loss @ SL)</label>
                  <input type="number" step="0.01" name="fixed_loss_pct" value={settings.fixed_loss_pct} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2" />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Risk Ratio (Per Trade, e.g. 0.01 = 1%)</label>
                <input type="number" step="0.01" name="default_risk_ratio" value={settings.default_risk_ratio} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2" />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Fee Type</label>
                <select name="fee_type" value={settings.fee_type} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm">
                  <option value="MARKET">Market (Taker)</option>
                  <option value="LIMIT">Limit (Maker)</option>
                </select>
              </div>

              <div className="col-span-2">
                <label className="block text-xs font-medium text-slate-400 mb-1">Notification Webhook (Discord)</label>
                <input type="password" name="webhook_url" value={settings.webhook_url || ''} onChange={handleSettingChange} placeholder="https://discord.com/api/webhooks/..." className="w-full bg-slate-900 border border-slate-700 rounded p-2 focus:ring-1 focus:ring-blue-500" />
              </div>

              <div className="col-span-2 grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">API Key</label>
                  <input type="password" name="api_key" value={settings.api_key} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">API Secret</label>
                  <input type="password" name="api_secret" value={settings.api_secret} onChange={handleSettingChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2" />
                </div>
              </div>
            </div>
            <div className="mt-8 text-right text-xs text-slate-500">Settings are auto-saved in memory.</div>
          </div>
        )}

        {activeTab === 'dashboard' && (
          <div className="space-y-8">

            {/* Scanner Status & Stats Bar */}
            <div className="bg-slate-800/60 border border-slate-700 p-4 rounded-xl flex items-center justify-between shadow-md">
              <div className="flex items-center space-x-6">
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-2 ${scannerActive ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`}></div>
                  <span className="text-sm font-medium text-slate-300">Signal Scanner: {scannerActive ? 'ACTIVE' : 'OFF'}</span>
                </div>
                <div className="h-4 w-px bg-slate-700"></div>
                <div className="text-sm text-slate-400">
                  Watching: <span className="text-slate-200">{Object.keys(signals).join(', ') || 'None'}</span>
                </div>
              </div>
              <button
                onClick={toggleScanner}
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all ${scannerActive
                  ? 'bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20'
                  : 'bg-green-500/10 text-green-400 border border-green-500/30 hover:bg-green-500/20'
                  }`}
              >
                {scannerActive ? 'Stop Scanner' : 'Start Scanner'}
              </button>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">

              {/* Left Column: Trade Setup & Signals */}
              <div className="space-y-8">
                {/* Trade Setup */}
                <div className="bg-slate-800/40 border border-slate-700 p-6 rounded-2xl flex flex-col shadow-lg relative">
                  <h2 className="text-lg font-semibold mb-6 text-slate-200 border-b border-slate-700/50 pb-2 flex items-center">
                    <svg className="w-5 h-5 mr-2 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                    Trade Setup
                  </h2>
                  <div className="space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Symbol</label>
                        <input type="text" name="symbol" value={tradeSetup.symbol} onChange={handleSetupChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 focus:outline-none" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Side</label>
                        <div className="flex rounded overflow-hidden border border-slate-700 text-sm">
                          <button onClick={() => setTradeSetup({ ...tradeSetup, side: 'LONG' })} className={`flex-1 py-2 ${tradeSetup.side === 'LONG' ? 'bg-green-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:bg-slate-800'}`}>LONG</button>
                          <button onClick={() => setTradeSetup({ ...tradeSetup, side: 'SHORT' })} className={`flex-1 py-2 ${tradeSetup.side === 'SHORT' ? 'bg-red-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:bg-slate-800'}`}>SHORT</button>
                        </div>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-400 mb-1">Entry Price ($)</label>
                      <input type="number" step="any" name="entry_price" value={tradeSetup.entry_price} onChange={handleSetupChange} className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-lg font-mono focus:border-blue-500 focus:outline-none" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Take Profit (TP)</label>
                        <input type="number" step="any" name="tp_price" value={tradeSetup.tp_price} onChange={handleSetupChange} className="w-full bg-slate-900 border border-green-900/50 rounded p-2 text-green-400 font-mono focus:border-green-500 focus:outline-none" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Stop Loss (SL)</label>
                        <input type="number" step="any" name="sl_price" value={tradeSetup.sl_price} onChange={handleSetupChange} className="w-full bg-slate-900 border border-red-900/50 rounded p-2 text-red-400 font-mono focus:border-red-500 focus:outline-none" />
                      </div>
                    </div>
                  </div>
                  <button onClick={calculateRisk} disabled={loading} className="mt-6 w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold rounded-xl shadow-lg transition-all flex justify-center items-center">
                    {loading ? <span className="animate-spin h-5 w-5 border-2 border-white/30 border-t-white rounded-full"></span> : 'Calculate Risk & Size'}
                  </button>
                </div>

                {/* Live Signals */}
                <div className="bg-slate-800/40 border border-slate-700 p-6 rounded-2xl shadow-lg">
                  <h2 className="text-lg font-semibold mb-4 text-slate-200 border-b border-slate-700/50 pb-2 flex items-center">
                    <svg className="w-5 h-5 mr-2 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    Market Signals
                  </h2>
                  <div className="space-y-3">
                    {Object.values(signals).length === 0 ? (
                      <div className="text-center py-8 text-slate-500 text-sm italic">Scanner not started or no signals yet...</div>
                    ) : (
                      Object.values(signals).map((sig) => (
                        <div key={sig.symbol} className="bg-slate-900/60 p-3 rounded-lg border border-slate-700/50 flex items-center justify-between">
                          <div>
                            <span className="font-bold text-slate-200 mr-2">{sig.symbol}</span>
                            <span className={`text-xs px-2 py-0.5 rounded font-bold ${sig.side === 'LONG' ? 'bg-green-500/20 text-green-400' :
                              sig.side === 'SHORT' ? 'bg-red-500/20 text-red-400' : 'bg-slate-700 text-slate-400'
                              }`}>{sig.side}</span>
                          </div>
                          <div className="text-xs text-slate-400 font-mono">
                            {sig.reason}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Results & Liq Map */}
              <div className="space-y-8">
                {/* Analysis Results */}
                <div className="bg-slate-800/40 border border-slate-700 p-6 rounded-2xl shadow-lg relative h-full flex flex-col">
                  <h2 className="text-lg font-semibold mb-6 text-slate-200 border-b border-slate-700/50 pb-2">Analysis Results</h2>
                  {error ? (
                    <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">{error}</div>
                  ) : !results ? (
                    <div className="flex-grow flex flex-col items-center justify-center text-slate-500 h-64">
                      Run calculation to see results
                    </div>
                  ) : (
                    <div className="space-y-4 relative z-10 flex-grow">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700/50 text-center">
                          <div className="text-xs text-slate-400 mb-1 uppercase tracking-wider font-bold">Leverage</div>
                          <div className="text-3xl font-bold text-white font-mono">{results.leverage}x</div>
                        </div>
                        <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700/50 text-center">
                          <div className="text-xs text-slate-400 mb-1 uppercase tracking-wider font-bold">Qty</div>
                          <div className="text-2xl font-bold text-white font-mono">{results.quantity}</div>
                        </div>
                      </div>

                      {/* Liquidation Clusters (M5) */}
                      {liqData && (
                        <div className="bg-slate-900/40 rounded-xl p-4 border border-slate-700/50">
                          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center">
                            <div className="w-1.5 h-1.5 bg-red-500 rounded-full mr-2"></div>
                            Liquidation Clusters
                          </h3>
                          <div className="space-y-2">
                            {/* Simplistic visual representation of clusters */}
                            <div className="relative h-12 bg-slate-950/50 rounded-lg overflow-hidden border border-slate-800">
                              {liqData.long_liq_clusters.map((c, i) => (
                                <div key={i} className="absolute bottom-0 bg-green-500/30 border-t border-green-500/50 w-2" style={{ left: `${40 + i * 15}%`, height: `${c.amount / 2}%` }}></div>
                              ))}
                              {liqData.short_liq_clusters.map((c, i) => (
                                <div key={i} className="absolute top-0 bg-red-500/30 border-b border-red-500/50 w-2" style={{ left: `${60 - i * 15}%`, height: `${c.amount / 2}%` }}></div>
                              ))}
                              <div className="absolute inset-y-0 left-1/2 w-px bg-white/20"></div> {/* Current Price line */}
                            </div>
                            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                              <span>-${(liqData.long_liq_clusters[0].price).toFixed(0)}</span>
                              <span>Current</span>
                              <span>+${(liqData.short_liq_clusters[0].price).toFixed(0)}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 overflow-hidden text-sm">
                        <div className="flex justify-between p-3 border-b border-slate-700/50">
                          <span className="text-slate-400">R/R Ratio</span>
                          <span className={`font-mono ${results.risk_reward_ratio >= 1.5 ? 'text-green-400 font-bold' : 'text-amber-400'}`}>1 : {results.risk_reward_ratio.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between p-3 border-b border-slate-700/50">
                          <span className="text-slate-400">Est. Liquidation</span>
                          <span className="font-mono text-red-400">${results.estimated_liq_price}</span>
                        </div>
                        <div className="flex justify-between p-3">
                          <span className="text-slate-400">Round Trip Fee</span>
                          <span className="font-mono text-slate-300">{results.min_profit_pct.toFixed(2)}%</span>
                        </div>
                      </div>

                      {validation && (
                        <div className={`p-4 rounded-xl border text-sm font-medium ${validation.approved ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                          <div className="flex items-center mb-1">
                            <span className="mr-2">{validation.approved ? '✅' : '❌'}</span>
                            <span>{validation.summary}</span>
                          </div>
                          {!validation.approved && (
                            <ul className="mt-2 space-y-1 text-xs list-disc list-inside opacity-80">
                              {validation.failed_rules.map((rule, idx) => (
                                <li key={idx}>{rule.msg}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}

                      <button
                        onClick={executeTrade}
                        disabled={loading || !results || !validation?.approved}
                        className={`mt-4 w-full py-3 px-4 text-white font-bold rounded-xl shadow-lg transition-all ${!validation?.approved ? 'bg-slate-700 cursor-not-allowed grayscale' : 'bg-blue-600 hover:bg-blue-500'
                          }`}
                      >
                        Auto-Execute Now
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
