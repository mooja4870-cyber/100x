import pandas as pd
import numpy as np
import asyncio
from typing import List, Dict

class SignalDetector:
    """기술적 지표 기반 진입 시그널 탐지 (CCI Reversal)"""

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_cci(self, df, period=20):
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad_tp = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        return (tp - sma_tp) / (0.015 * mad_tp)

    def analyze_signals(self, df: pd.DataFrame) -> Dict:
        """CCI 반전 전략 반영"""
        if df is None or len(df) < 5:
            return {"side": "NEUTRAL", "reason": "No data"}

        df = df.copy()
        df['rsi'] = self.calculate_rsi(df['close'])
        df['cci'] = self.calculate_cci(df)
        
        if len(df) < 20: 
            return {"side": "NEUTRAL", "reason": "Insufficient data"}
            
        # CCI Reversal Logic
        # 롱 시그널: 전전봉 CCI < -100, 전봉 CCI > -100
        # 숏 시그널: 전전봉 CCI > +100, 전봉 CCI < +100
        last_cci = df['cci'].iloc[-1]
        prev_cci = df['cci'].iloc[-2]
        prev_prev_cci = df['cci'].iloc[-3]
        
        side = "NEUTRAL"
        reason = f"CCI: {last_cci:.2f}"

        if prev_prev_cci < -100 and prev_cci > -100:
            side = "LONG"
            reason = "CCI Reversal Bull (-100 breakout)"
        elif prev_prev_cci > 100 and prev_cci < 100:
            side = "SHORT"
            reason = "CCI Reversal Bear (100 breakdown)"

        # 추가 컨플루언스 (RSI)
        last_rsi = df['rsi'].iloc[-1]
        if side == "LONG" and last_rsi > 60: # 과매수 구간이면 패스 고려 가능하나 여기서는 기록만
             reason += " (High RSI)"
        
        return {
            "symbol": "BTCUSDT", # Example, should be passed or detected
            "side": side,
            "entry_price": df['close'].iloc[-1],
            "rsi": last_rsi if not np.isnan(last_rsi) else 0,
            "cci": last_cci if not np.isnan(last_cci) else 0,
            "reason": reason,
            "timestamp": str(df['timestamp'].iloc[-1])
        }

    def suggest_sl_tp(self, df: pd.DataFrame, side: str) -> Dict:
        """ATR 기반 SL/TP 제안 (단순화된 버전)"""
        # ATR 계산 (단순하게 High-Low 평균)
        atr = (df['high'] - df['low']).rolling(window=14).mean().iloc[-1]
        entry_price = df['close'].iloc[-1]
        
        if side == "LONG":
            sl = entry_price - (atr * 1.5)
            tp = entry_price + (atr * 3.0)
        else:
            sl = entry_price + (atr * 1.5)
            tp = entry_price - (atr * 3.0)
            
        return {
            "entry": round(entry_price, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "sl_pct": round(abs(entry_price - sl) / entry_price * 100, 4)
        }
