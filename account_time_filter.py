from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import models
import requests
import os
import dotenv
from dateutil import parser
from datetime import timezone, timedelta
from typing import List, Optional
import json
from datetime import datetime, timedelta

def filter_wallets_in_db_by_time(db_session: Session, days_lookback:int):
  wallets = db_session.query(models.Wallet).all()
  for wallet in wallets:
    if datetime.now(tz=timezone.utc)  <  wallet.earliest_tsx.astimezone(timezone.utc) + timedelta(days=days_lookback):
      db_session.delete(wallet)
  db_session.commit()