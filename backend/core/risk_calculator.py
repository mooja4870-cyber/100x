from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict
from backend.models.schemas import UserConfig, TradeSetupInput, TradeSetupOutput, Side, LeverageMode, FeeType

# 거래소별 수수료 테이블 (왕복 기준)
FEE_TABLE = {
    "BYBIT": {"LIMIT": 0.0002, "MARKET": 0.0012},
    "BINANCE": {"LIMIT": 0.0002, "MARKET": 0.0010},
}

def calculate_risk(config: UserConfig, setup: TradeSetupInput) -> TradeSetupOutput:
    """핵심 리스크 계산 엔진 (Act 지침 반영)"""
    
    exchange_name = config.exchange.value if hasattr(config.exchange, 'value') else config.exchange
    fees = FEE_TABLE.get(exchange_name, FEE_TABLE["BYBIT"])
    
    # ── Step 1: SL/TP 퍼센티지 ──
    sl_pct = abs(setup.entry_price - setup.sl_price) / setup.entry_price
    tp_pct = abs(setup.tp_price - setup.entry_price) / setup.entry_price

    # ── Step 2: 손익비(RR) ──
    rr_ratio = tp_pct / sl_pct if sl_pct > 0 else 0

    # ── Step 3: 레버리지 결정 ──
    if config.leverage_mode == LeverageMode.VARIABLE:
        # 고정 손실 %를 기준으로 레버리지 계산
        leverage = config.fixed_loss_pct / sl_pct
        leverage = max(1, min(int(leverage), 125))
    else:
        leverage = config.fixed_leverage

    # ── Step 4: 수량 계산 ──
    # 1회 매매 리스크 금액 = 잔고 * 리스크 비율
    risk_amount = config.account_balance * config.default_risk_ratio
    # 수량 = 리스크 금액 / (진입가 - 손절가)
    quantity = risk_amount / abs(setup.entry_price - setup.sl_price)

    # ── Step 5: 포지션 사이즈 (USDT) ──
    position_value = quantity * setup.entry_price
    margin_required = position_value / leverage

    # ── Step 6: 예상 청산가 ──
    # 단순화된 공식 (격리 마진 기준)
    if setup.side == Side.LONG:
        liq_price = setup.entry_price * (1 - 0.9 / leverage) # 90% 증거금 소진 시 청산 가정
    else:
        liq_price = setup.entry_price * (1 + 0.9 / leverage)

    # ── Step 7: 수수료 계산 ──
    fee_rate = fees["LIMIT"] if config.fee_type == FeeType.LIMIT else fees["MARKET"]
    fee_amount = position_value * fee_rate
    min_profit_pct = (fee_amount / config.account_balance) * 100

    # Rule 7: Smart SL 적용 (여기서는 이미 sl_price가 입력되었으므로 계산 결과에 반영)
    # 실제 진입 시에는 validator에서 체크함

    import uuid
    from datetime import datetime

    return TradeSetupOutput(
        id=str(uuid.uuid4()),
        symbol=setup.symbol,
        side=setup.side,
        entry_price=setup.entry_price,
        tp_price=setup.tp_price,
        sl_price=setup.sl_price,
        sl_pct=round(sl_pct * 100, 4),
        tp_pct=round(tp_pct * 100, 4),
        risk_reward_ratio=round(rr_ratio, 2),
        leverage=leverage,
        quantity=round(quantity, 6),
        estimated_liq_price=round(liq_price, 2),
        fee_estimate_pct=round(fee_rate * 100, 4),
        min_profit_pct=round(min_profit_pct, 4),
        status="PLANNED",
        created_at=datetime.now()
    )
