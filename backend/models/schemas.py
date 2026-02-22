from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel
import uuid
from datetime import datetime

class LeverageMode(str, Enum):
    VARIABLE = "VARIABLE"
    FIXED = "FIXED"

class FeeType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class Exchange(str, Enum):
    BYBIT = "BYBIT"
    BINANCE = "BINANCE"

class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class UserConfig(BaseModel):
    account_balance: float
    default_risk_ratio: float = 0.01  # 1%
    fixed_loss_pct: float = 0.10      # 10%
    leverage_mode: LeverageMode = LeverageMode.VARIABLE
    fixed_leverage: int = 10
    fee_type: FeeType = FeeType.MARKET
    exchange: Exchange = Exchange.BYBIT
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

class TradeSetupInput(BaseModel):
    symbol: str = "BTCUSDT"
    side: Side
    entry_price: float
    tp_price: float
    sl_price: float

class TradeSetupOutput(BaseModel):
    id: str
    symbol: str
    side: Side
    entry_price: float
    tp_price: float
    sl_price: float
    
    sl_pct: float
    tp_pct: float
    risk_reward_ratio: float
    leverage: int
    quantity: float
    estimated_liq_price: float
    fee_estimate_pct: float
    min_profit_pct: float
    
    status: str = "PLANNED"
    created_at: datetime
    
