from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

DB_PATH = "sqlite:///./100x_trading.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    side = Column(String) # LONG, SHORT
    entry_price = Column(Float)
    tp_price = Column(Float)
    sl_price = Column(Float)
    quantity = Column(Float)
    leverage = Column(Integer)
    status = Column(String) # OPEN, CLOSED, CANCELLED
    pnl = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    details = Column(JSON, nullable=True)

Base.metadata.create_all(bind=engine)
