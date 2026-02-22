from sqlalchemy.orm import Session
from backend.db.database import Trade
import datetime

class JournalManager:
    @staticmethod
    def save_trade(db: Session, trade_data: dict):
        db_trade = Trade(**trade_data)
        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)
        return db_trade

    @staticmethod
    def get_trades(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Trade).order_by(Trade.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_stats(db: Session):
        trades = db.query(Trade).filter(Trade.status == "CLOSED").all()
        if not trades:
            return {"win_rate": 0, "total_pnl": 0, "trade_count": 0}
        
        wins = [t for t in trades if t.pnl > 0]
        total_pnl = sum(t.pnl for t in trades)
        
        return {
            "win_rate": len(wins) / len(trades) * 100,
            "total_pnl": total_pnl,
            "trade_count": len(trades)
        }
