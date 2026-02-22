import asyncio
import ccxt
import pandas as pd
from backend.core.signal_detector import SignalDetector
from backend.core.notifier import Notifier
from backend.models.schemas import UserConfig, Side
from backend.core.risk_calculator import calculate_risk
from backend.core.risk_validator import RiskValidator
from backend.core.position_manager import PositionManager

class Scanner:
    """전체 자동매매 오케스트레이션 (Act 지침 반영)"""

    def __init__(self, notifier: Notifier = None):
        self.notifier = notifier
        self.is_running = False
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.scan_interval = 60 # Default 60 seconds
        self.latest_signals = {}
        self.validator = RiskValidator()
        self.pos_manager = PositionManager(notifier=notifier)
        self.active_trades = []

    async def fetch_ohlcv(self, exchange, symbol, timeframe='1h', limit=100):
        try:
            ohlcv = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol}: {e}")
            return None

    async def run(self, config: UserConfig):
        self.is_running = True
        exchange_id = config.exchange.value.lower() if hasattr(config.exchange, 'value') else config.exchange.lower()
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': config.api_key,
            'secret': config.api_secret,
            'options': {'defaultType': 'future'}
        })
        detector = SignalDetector()

        print(f"🚀 Scanner started for {self.symbols}")

        while self.is_running:
            try:
                for symbol in self.symbols:
                    df = await self.fetch_ohlcv(exchange, symbol, timeframe='1h', limit=50)
                    if df is None: continue

                    signal = detector.analyze_signals(df)
                    signal['symbol'] = symbol
                    self.latest_signals[symbol] = signal
                    
                    if signal['side'] != "NEUTRAL":
                        # 1. 시그널 발생 시 알림
                        if self.notifier:
                             await self.notifier.send_discord_message(
                                 f"📡 **시그널 감지**: {symbol}\n사이드: {signal['side']}\n근거: {signal['reason']}"
                             )

                        # 2. 자동 진입 로직 (선택 사항 - 여기선 매뉴얼 진입 위주이나 오케스트레이터엔 포함)
                        # if config.auto_trade_enabled: ...
                
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                print(f"Scanner error: {e}")
                await asyncio.sleep(10)
        
        await asyncio.to_thread(exchange.close)

    def stop(self):
        self.is_running = False
