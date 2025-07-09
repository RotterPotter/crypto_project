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


if __name__ == "__main__":
  # db session
  engine = create_engine("sqlite:///mydb.sqlite", echo=True)
  session_ = sessionmaker(bind=engine)
  session = session_()
  models.Base.metadata.create_all(engine)

  wallets = session.query(models.Wallet).all()

  for wallet in wallets:
    if datetime.now(tz=timezone.utc)  <  wallet.earliest_tsx.astimezone(timezone.utc) + timedelta(days=90):
      session.delete(wallet)

  session.commit()