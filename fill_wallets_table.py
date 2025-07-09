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

dotenv.load_dotenv()

def fetch_transactions_summary(adress:str, chain_name:str):
  url = f"https://api.covalenthq.com/v1/{chain_name}/address/{adress}/transactions_summary/"
  
  headers = {"Authorization": f"Bearer {os.getenv('GOLDRUSH_API_KEY')}"}

  response = requests.request("GET", url, headers=headers)
  if response.ok:
    return response.json()
  else:
    raise Exception(response.text)

def add_earliest_tsx_dt_in_db(transaction_summary: dict, adress, db_session: Session) -> bool:
  first_tsx_datetime = transaction_summary["data"]["items"][0]["earliest_transaction"]["block_signed_at"]
  dt = parser.parse(first_tsx_datetime)

  wallet_in_db = db_session.query(models.Wallet).where(models.Wallet.adress == adress).first()
  if wallet_in_db.earliest_tsx is None or dt < wallet_in_db.earliest_tsx.astimezone(timezone.utc):
    wallet_in_db.earliest_tsx = dt

def fetch_all_transactions(adress:str) -> List[Optional[dict]]:

  transactions_to_return = []
  page = 0

  while True:
    url = f"https://api.covalenthq.com/v1/eth-mainnet/address/{adress}/transactions_v3/page/{page}/"

    headers = {"Authorization": f"Bearer {os.getenv('GOLDRUSH_API_KEY')}"}

    response = requests.request("GET", url, headers=headers)
    data = response.json()

    transactions = data["data"]["items"]

    if len(transactions) < 1:
      break
    else:
      transactions_to_return += transactions

    page += 1

  return transactions_to_return

def fetch_used_chains(wallet_address:str) -> List[Optional[dict]]:

  url = f"https://api.covalenthq.com/v1/address/{wallet_address}/activity/"

  headers = {"Authorization": f"Bearer {os.getenv('GOLDRUSH_API_KEY')}"}

  response = requests.request("GET", url, headers=headers)
  data = response.json()

  used_chains = []
  for el in data["data"]["items"]:

    used_chains.append(el["name"])
  
  return used_chains

def fill_data(adress:str, db_session: Session) -> bool:
  # take all used chains for the adress
  used_chains = fetch_used_chains(adress)

  # adding dt of the earliest transaction on the wallet
  for chain_name in used_chains:
    try:
      transactions_summary = fetch_transactions_summary(adress, chain_name)
    except:
      continue
    add_earliest_tsx_dt_in_db(transactions_summary, adress, db_session)


  # all_transactions = fetch_all_transactions(adress)
  # with open("test.json", "w") as fp:
  #   json.dump(all_transactions, fp)
  # transformed_transactions = transform_transactions(adress, all_transactions)
  # print(transform_transactions)

if __name__ == "__main__":
  # db session
  engine = create_engine("sqlite:///mydb.sqlite", echo=True)
  session_ = sessionmaker(bind=engine)
  session = session_()
  models.Base.metadata.create_all(engine)

  wallets = session.query(models.Wallet).all()

  for wallet in wallets:
    fill_data(wallet.adress, session)
     # to remove

  session.commit()



# def transform_transactions(wallet_address: str, all_transactions: list):
#   transformed_transactions = []

#   for transaction in all_transactions:
#     if not transaction["successful"]:
#       continue

#     if not transaction["value_quote"] > 0:
#       continue

#     from_address = transaction["from_address"]
#     to_address = transaction["to_address"]
    
#     order_type = "BUY" if from_address == wallet_address else "SELL"

#   return transform_transactions
  
# def calculate_pnl_and_add_in_db(transformed_transactions: list):
#   pass