import pandas as pd
import ccxt
import asyncio
from typing import List, Dict
from backend.core.signal_detector import SignalDetector
import datetime

class BacktestEngine:
    def __init__(self, exchange: ccxt.Exchange):
        self.exchange = exchange
        self.detector = SignalDetector(exchange)

    async def run(self, symbol: str, timeframe: str = '1h', limit: int = 500):
        # Fetch historical data
        ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Add indicators
        df['rsi'] = self.detector.calculate_rsi(df['close'])
        df['cci'] = self.detector.calculate_cci(df)

        trades = []
        active_trade = None

        for i in range(25, len(df)): # Need enough data for indicators
            row = df.iloc[i]
            
            if active_trade:
                # Check for exit (TP or SL)
                if active_trade['side'] == 'LONG':
                    if row['high'] >= active_trade['tp']:
                        active_trade['status'] = 'PROFIT'
                        active_trade['exit_price'] = active_trade['tp']
                        active_trade['closed_at'] = row['timestamp']
                        trades.append(active_trade)
                        active_trade = None
                    elif row['low'] <= active_trade['sl']:
                        active_trade['status'] = 'LOSS'
                        active_trade['exit_price'] = active_trade['sl']
                        active_trade['closed_at'] = row['timestamp']
                        trades.append(active_trade)
                        active_trade = None
                else: # SHORT
                    if row['low'] <= active_trade['tp']:
                        active_trade['status'] = 'PROFIT'
                        active_trade['exit_price'] = active_trade['tp']
                        active_trade['closed_at'] = row['timestamp']
                        trades.append(active_trade)
                        active_trade = None
                    elif row['high'] >= active_trade['sl']:
                        active_trade['status'] = 'LOSS'
                        active_trade['exit_price'] = active_trade['sl']
                        active_trade['closed_at'] = row['timestamp']
                        trades.append(active_trade)
                        active_trade = None
            else:
                # Check for entry signal
                prev_rows = df.iloc[:i+1]
                signal = self.detector.analyze_signals(prev_rows)
                
                if signal['side'] != 'NEUTRAL':
                    # Simplified TP/SL (e.g. 1% SL, 2% TP)
                    entry_price = row['close']
                    side = signal['side']
                    sl_pct = 0.01
                    tp_pct = 0.02
                    
                    sl = entry_price * (1 - sl_pct) if side == 'LONG' else entry_price * (1 + sl_pct)
                    tp = entry_price * (1 + tp_pct) if side == 'LONG' else entry_price * (1 - tp_pct)
                    
                    active_trade = {
                        "symbol": symbol,
                        "side": side,
                        "entry_price": entry_price,
                        "sl": sl,
                        "tp": tp,
                        "timestamp": row['timestamp'],
                        "status": "OPEN"
                    }

        # Calculate statistics
        if not trades:
            return {"trades": [], "stats": {"win_rate": 0, "total_returns": 0}}

        wins = [t for t in trades if t['status'] == 'PROFIT']
        win_rate = len(wins) / len(trades) * 100
        
        # Simple returns calculation (ignoring leverage for now)
        total_returns = 0
        for t in trades:
            ret = (t['exit_price'] - t['entry_price']) / t['entry_price']
            if t['side'] == 'SHORT': ret *= -1
            total_returns += ret

        return {
            "trades": [ {**t, "timestamp": str(t['timestamp']), "closed_at": str(t['closed_at'])} for t in trades ],
            "stats": {
                "win_rate": round(win_rate, 2),
                "total_returns_pct": round(total_returns * 100, 2),
                "trade_count": len(trades)
            }
        }
