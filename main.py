from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import models
import requests
import os
import dotenv
from dateutil import parser
from datetime import timezone, timedelta

  
def check_wallet(adress:str) -> bool:
  # 0. Wallet data fetching
  # 1. activity time checker
  # 2. pnl checker
  
  # data extraction
  # check1 - x month activity checker
  # check2 - verify total pnl between all opened-closed trades (bought x amount of ETH, sold x amount of ETH) 0 durinlast x amount of month
  # ...
  return True

if __name__ == "__main__":
  # db session
  engine = create_engine("sqlite:///mydb.sqlite", echo=True)
  session_ = sessionmaker(bind=engine)
  session = session_()
  models.Base.metadata.create_all(engine)

  wallets = session.query(models.Wallet).all()

  for wallet in wallets:
    result = check_wallet(wallet.adress)
    wallet.good = result

  session.commit()
