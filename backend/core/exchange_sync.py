import ccxt
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional

class BalanceResponse(BaseModel):
    exchange: str
    total_balance: float
    free_balance: float
    used_balance: float

def fetch_balance(exchange_id: str, api_key: str, api_secret: str, testnet: bool = False) -> BalanceResponse:
    try:
        exchange_class = getattr(ccxt, exchange_id.lower())
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        if testnet:
            if 'test' in exchange.urls:
                exchange.set_sandbox_mode(True)

        balance = exchange.fetch_balance()
        
        # Typically USDT is used for futures
        coin = "USDT" 
        
        if coin not in balance:
            raise HTTPException(status_code=400, detail=f"{coin} balance not found on {exchange_id}")

        total = balance[coin]['total']
        free = balance[coin]['free']
        used = balance[coin]['used']

        return BalanceResponse(
            exchange=exchange_id,
            total_balance=total,
            free_balance=free,
            used_balance=used
        )
    except ccxt.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API Key or Secret")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
