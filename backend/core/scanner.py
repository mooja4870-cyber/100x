import asyncio
import ccxt
from backend.core.signal_detector import SignalDetector
from backend.core.notifier import Notifier
from backend.models.schemas import UserConfig, TradeSetupInput
from backend.core.risk_calculator import calculate_risk

class Scanner:
    def __init__(self, notifier: Notifier = None):
        self.notifier = notifier
        self.is_running = False
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.scan_interval = 60 # Default 60 seconds
        self.auto_trade = False
        self.latest_signals = {}

    async def run(self, config: UserConfig):
        self.is_running = True
        exchange_class = getattr(ccxt, config.exchange.lower())
        exchange = exchange_class()
        detector = SignalDetector(exchange)

        while self.is_running:
            for symbol in self.symbols:
                df = await detector.fetch_ohlcv(symbol, timeframe='5m', limit=50) # Use 5m for faster signals
                signal = detector.analyze_signals(df)
                signal['symbol'] = symbol
                self.latest_signals[symbol] = signal
                
                if signal['side'] != "NEUTRAL":
                    # Potentially auto-trade or just notify
                    if self.notifier:
                        await self.notifier.send_discord(f"🎯 **{symbol} {signal['side']} Signal Detected!**\n{signal['reason']}")
            
            await asyncio.sleep(self.scan_interval)
        
        await asyncio.to_thread(exchange.close)

    def stop(self):
        self.is_running = False
