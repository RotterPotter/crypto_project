from datetime import datetime, timedelta, timezone
from typing import List, Dict
import os
import dotenv
import requests
from dateutil import parser


dotenv.load_dotenv()

def analyze_transactions(wallet_address:str, token_name:str, dt:datetime):
  pass

def take_daily_tokens_movement(
  wallet_address:str,
  chain_name:str,
  days_lookback:int
) -> Dict[str, List[str]]: # {date: [coin's contract adress 1, coin's contract adress 2]}

  url = f"https://api.covalenthq.com/v1/{chain_name}/address/{wallet_address}/portfolio_v2/"

  query_params = {"days": days_lookback}

  headers = {"Authorization": f"Bearer {os.getenv('GOLDRUSH_API_KEY')}"}

  response = requests.request("GET", url, headers=headers, params=query_params)

  tokens_movement = {}

  for coin_data in response.json()["data"]["items"]:
    prev_item = None

    for item in coin_data["holdings"]:
      if prev_item is None:
        prev_item = item
        continue
      
      prev_day_close = float(prev_item["close"]["balance"]) 

      cur_day_high = float(item["high"]["balance"]) 
      cur_day_low = float(item["low"]["balance"]) 
      cur_day_close = float(item["close"]["balance"]) 

      if (
        cur_day_close != prev_day_close or
        cur_day_low != prev_day_close or
        cur_day_high != prev_day_close
      ):
        if tokens_movement.get(item["timestamp"], None) is None:
          tokens_movement[item["timestamp"]] = []
        
        tokens_movement[item["timestamp"]].append(coin_data["contract_address"])
      
      prev_item = item
    
  return tokens_movement

def take_all_wallets_transactions(wallet_address:str, chain_name:str, days_lookback:int):

  stop_looking_date = datetime.now(tz=timezone.utc) - timedelta(days_lookback)
  all_transactions = []
  page = 1
  run = True

  while run:
    url = f"https://api.covalenthq.com/v1/{chain_name}/address/{wallet_address}/transactions_v3/page/{page}/"
    headers = {"Authorization": f"Bearer {os.getenv("GOLDRUSH_API_KEY")}"}
    response = requests.request("GET", url, headers=headers)
    transactions = response.json()["data"]["items"]

    if len(transactions) < 1 or parser.parse(transactions[0]["block_signed_at"]) < stop_looking_date:
      run = False

    for transaction in transactions:
      # TODO add re-orged block checker. "Get block heights" endpoint + custom mapping block height:hash
      # check sender/receiver hashes.
      # time, sender/receiver, value
      if transaction.get("log_events", None) is None:
        continue

      block_signed_at = parser.parse(transaction["block_signed_at"])
      if block_signed_at < stop_looking_date:
        run = False
        break
      
      for log_event in transaction["log_events"]:
        from_address = log_event
        to_address = log_event
        value = log_event

        all_transactions.append({
          "block_signed_at": block_signed_at,
          "from_address": from_address,
          "to_address": to_address,
          "value": value

        })


    page += 1

  return all_transactions
  

def analyze_wallet_ballance(wallet_address:str, chain_name:str, days_lookback:int):
  # 1. Take daily change of the wallet's token-balance.
  # 2. If there is a portfolio change (compare prev and cur days), start transaction analysis.
  daily_tokens_movement = take_daily_tokens_movement(wallet_address, chain_name, days_lookback)
  all_transactions = take_all_wallets_transactions(wallet_address, chain_name, days_lookback)
  
  for date, contract_names in daily_tokens_movement.items():
    for 

if __name__ == "__main__":
  result = analyze_wallet_ballance("0x8badd8b59DdAf9A12c4910Ca1B2E8ea750A71594", "eth-mainnet", 30)