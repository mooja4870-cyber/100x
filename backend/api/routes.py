from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import ccxt

from backend.core.notifier import Notifier
from backend.core.position_manager import PositionManager
from backend.core.scanner import Scanner
from backend.core.liq_map import LiqMapProvider
from backend.core.journal_manager import JournalManager
from backend.core.backtest_engine import BacktestEngine
from backend.db.database import SessionLocal
from backend.models.schemas import UserConfig, TradeSetupInput, TradeSetupOutput
from backend.core.exchange_sync import fetch_balance, BalanceResponse

from backend.core.risk_calculator import calculate_risk
from backend.core.risk_validator import RiskValidator
from typing import Dict

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Global instances
notifier = Notifier()
notifier.webhook_url = "https://discord.com/api/webhooks/1475123788826804320/o7CnJ-Cnnhh0nUdUt-_CICDPmlKqjfvegZOeGJH1NlLRJcMy_F9FhTP9WvnZQeg30q0O"

pos_manager = PositionManager(notifier=notifier)
validator = RiskValidator()
scanner = Scanner(notifier=notifier)
liq_provider = LiqMapProvider()
journal = JournalManager()

class RiskCalculationRequest(BaseModel):
    config: UserConfig
    setup: TradeSetupInput

class BalanceRequest(BaseModel):
    exchange: str
    api_key: str
    api_secret: str
    testnet: bool = False

class ExecutionRequest(BaseModel):
    config: UserConfig
    setup: TradeSetupOutput
    webhook_url: Optional[str] = None

class ScannerControlRequest(BaseModel):
    config: UserConfig
    interval: int = 60
    symbols: List[str] = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

@router.post("/calculate_risk", response_model=Dict)
def api_calculate_risk(req: RiskCalculationRequest):
    try:
        result = calculate_risk(req.config, req.setup)
        validation = validator.validate(result, req.config, [])
        return {
            "calc": result.dict(),
            "validation": validation
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/signals")
def api_get_signals():
    return scanner.latest_signals

@router.get("/liq_map/{symbol}")
async def api_get_liq_map(symbol: str):
    return await liq_provider.get_liq_data(symbol)

@router.post("/scanner/start")
async def api_start_scanner(req: ScannerControlRequest):
    if scanner.is_running:
        return {"status": "already running"}
    scanner.scan_interval = req.interval
    scanner.symbols = req.symbols
    # Start in background
    asyncio.create_task(scanner.run(req.config))
    return {"status": "started"}

@router.post("/scanner/stop")
def api_stop_scanner():
    scanner.stop()
    return {"status": "stopped"}

@router.get("/history")
def api_get_history(db: SessionLocal = Depends(get_db)):
    return journal.get_trades(db)

@router.get("/stats")
def api_get_stats(db: SessionLocal = Depends(get_db)):
    return journal.get_stats(db)

@router.post("/backtest")
async def api_run_backtest(symbol: str, timeframe: str = '1h', limit: int = 500):
    exchange = ccxt.bybit() # Default for backtest
    engine = BacktestEngine(exchange)
    return await engine.run(symbol, timeframe, limit)

@router.post("/execute_trade")
async def api_execute_trade(req: ExecutionRequest, db: SessionLocal = Depends(get_db)):
    try:
        if req.webhook_url:
            notifier.webhook_url = req.webhook_url
            
        # 1. Validation check again
        validation = validator.validate(req.setup, req.config, [])
        if not validation["approved"]:
            raise HTTPException(status_code=400, detail=f"Validation failed: {validation['summary']}")

        # 2. Execute on exchange
        result = await pos_manager.execute_trade(req.config, req.setup)
        
        # 3. Save to journal
        journal.save_trade(db, {
            "symbol": req.setup.symbol,
            "side": req.setup.side.value if hasattr(req.setup.side, 'value') else req.setup.side,
            "entry_price": req.setup.entry_price,
            "tp_price": req.setup.tp_price,
            "sl_price": req.setup.sl_price,
            "quantity": req.setup.quantity,
            "leverage": req.setup.leverage,
            "status": "OPEN",
            "details": {"exec_result": result}
        })
        
        return {"status": "success", "result": result, "validation": validation}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch_balance", response_model=BalanceResponse)
def api_fetch_balance(req: BalanceRequest):
    return fetch_balance(req.exchange, req.api_key, req.api_secret, req.testnet)

@router.get("/health")
def health_check():
    return {"status": "ok", "message": "100x Backend is running"}
