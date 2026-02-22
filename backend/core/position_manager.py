import ccxt
import asyncio
from typing import Dict, Any
from backend.models.schemas import UserConfig, TradeSetupOutput, Side
from backend.core.notifier import Notifier

class PositionManager:
    """거래소 주문 생성·실행·관리 (Act 지침 반영)"""

    def __init__(self, notifier: Notifier = None):
        self.notifier = notifier

    def _get_exchange(self, config: UserConfig):
        exchange_id = config.exchange.value.lower() if hasattr(config.exchange, 'value') else config.exchange.lower()
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': config.api_key,
            'secret': config.api_secret,
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        # Note: Sandbox mode handling might be needed depending on the exchange
        # exchange.set_sandbox_mode(True) 
        return exchange

    async def execute_trade(self, config: UserConfig, setup: TradeSetupOutput) -> Dict[str, Any]:
        """Entry + TP + SL 동시 주문 실행"""
        try:
            exchange = self._get_exchange(config)
            symbol = setup.symbol
            side = setup.side.value if hasattr(setup.side, 'value') else setup.side
            quantity = setup.quantity
            entry = setup.entry_price
            tp = setup.tp_price
            sl = setup.sl_price
            leverage = setup.leverage

            # 1. 레버리지 설정
            try:
                await asyncio.to_thread(exchange.set_leverage, leverage, symbol)
            except Exception as e:
                print(f"Warning setting leverage: {e}")

            orders = {}

            # 2. 진입 주문 (시장가 또는 지정가 - 여기서는 지시대로 지정가 시도)
            entry_side = "buy" if side == "LONG" else "sell"
            # 실시간성을 위해 시장가로 진입하는 경우가 많으나, 요청한 코드대로 지정가 시도
            entry_order = await asyncio.to_thread(
                exchange.create_order,
                symbol=symbol,
                type="limit",
                side=entry_side,
                amount=quantity,
                price=entry
            )
            orders["entry"] = entry_order

            # 3. TP & SL (거래소마다 파라미터가 다르므로 Bybit/Binance 공통 스타일 시도)
            exit_side = "sell" if side == "LONG" else "buy"
            
            # TP
            try:
                tp_order = await asyncio.to_thread(
                    exchange.create_order,
                    symbol=symbol,
                    type="limit",
                    side=exit_side,
                    amount=quantity,
                    price=tp,
                    params={"reduceOnly": True, "triggerPrice": tp}
                )
                orders["take_profit"] = tp_order
            except Exception as e:
                print(f"TP order failed: {e}")

            # SL
            try:
                sl_order = await asyncio.to_thread(
                    exchange.create_order,
                    symbol=symbol,
                    type="stop", # 또는 'stop_market'
                    side=exit_side,
                    amount=quantity,
                    price=sl,
                    params={"reduceOnly": True, "stopPrice": sl}
                )
                orders["stop_loss"] = sl_order
            except Exception as e:
                print(f"SL order failed: {e}")

            if self.notifier:
                await self.notifier.send_discord_message(
                    f"🚀 **포지션 진입 완료**\n심볼: {symbol}\n사이드: {side}\n레버리지: {leverage}x\n수량: {quantity}"
                )

            return {"success": True, "orders": orders}

        except Exception as e:
            if self.notifier:
                await self.notifier.send_discord_message(f"❌ **주문 실행 실패**: {str(e)}")
            raise e

    async def get_open_positions(self, config: UserConfig):
        """현재 열려있는 포지션 조회"""
        try:
            exchange = self._get_exchange(config)
            positions = await asyncio.to_thread(exchange.fetch_positions)
            return [p for p in positions if float(p.get('contracts', 0)) > 0]
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []
