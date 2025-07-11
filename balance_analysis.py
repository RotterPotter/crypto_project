from datetime import datetime, timedelta, timezone
from typing import List, Dict, Union
import os
import dotenv
import requests
from dateutil import parser
import pandas as vbt
import vectorbt as vbt
import numpy as np
import time
import pprint
from sqlalchemy.orm import Session
import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

dotenv.load_dotenv()

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

def get_a_block(chain_name:str, block_height: Union[str, int] = "latest"):
  while True:
    url = f"https://api.covalenthq.com/v1/{chain_name}/block_v2/{block_height}/"

    headers = {"Authorization": f"Bearer {os.getenv('GOLDRUSH_API_KEY')}"}

    response = requests.request("GET", url, headers=headers)

    if not response.ok:
      print(response.text)
      print("sleeping for 30 sec")
      time.sleep(30)
      continue

    return response.json()["data"]["items"][0]

def take_starting_block_height(chain_name, days_lookback:int):
  from_datetime = datetime.now(tz=timezone.utc) - timedelta(days=days_lookback)
  threshold_window = timedelta(minutes=15)

  latest_block_h = get_a_block(chain_name, "latest")["height"]
  low = 0
  high = latest_block_h

  while low <= high:
    mid = (low + high) // 2
    block = get_a_block(chain_name, mid)
    block_dt = parser.parse(block["signed_at"])

    if from_datetime - threshold_window <= block_dt <= from_datetime + threshold_window:
      return mid

    if block_dt < from_datetime:
      low = mid + 1
    else:
      high = mid - 1

  raise ValueError("Could not find block close enough to target date.")

def take_all_erc_token_transfers(wallet_address:str, chain_name:str, token_address:str, starting_block:int):
  url = f"https://api.covalenthq.com/v1/{chain_name}/address/{wallet_address}/transfers_v2/"

  
  headers = {"Authorization": f"Bearer {os.getenv('GOLDRUSH_API_KEY')}"}

  all_transfers = []

  p = 0
  while True:
    query_params = {"starting-block": starting_block, "page-number": p, "quote-currency": "EUR", "contract-address": token_address}
    response = requests.request("GET", url, headers=headers, params=query_params)
    response_data = response.json()["data"]
    
    if not response.ok:
      print(response.text)
      print("slepping for 30 sec")
      time.sleep(30)
      continue

    for item in response_data["items"]:
      all_transfers += item["transfers"]
    
    if response_data["pagination"]["has_more"]:
      p += 1
    else:
      break

  return all_transfers

def backtest_token_portfolio(token_address: str, wallet_address: str, token_transfers: list):
    prices = {}
    position_deltas = {}

    for transfer in token_transfers:
        dt = parser.parse(transfer["block_signed_at"])
        quote_rate = transfer.get("quote_rate", 0.0)

        if quote_rate is None or quote_rate <= 0:
            continue

        token_decimals = transfer.get("contract_decimals", 0.0)
        amount = float(transfer["delta"]) / (10 ** token_decimals)

        # Determine if wallet gained or lost tokens
        delta = -amount if transfer["from_address"] == wallet_address else amount

        prices[dt] = quote_rate
        position_deltas[dt] = delta  # now raw (not cumulative)

    if not prices:
        return None

    price_series = pd.Series(prices).sort_index()
    delta_series = pd.Series(position_deltas).sort_index()

    # Generate entry signals based on positive/negative delta
    long_entries = delta_series > 0
    short_entries = delta_series < 0

    # Use absolute delta as position size
    size_series = delta_series.abs()

    return backtest_with_vectorbt(price_series, long_entries, short_entries, size_series)

def backtest_with_vectorbt(price_series: pd.Series, long_entries: pd.Series, short_entries: pd.Series, size_series: pd.Series) -> vbt.Portfolio:
    # Ensure indices match
    index = price_series.index.union(long_entries.index).union(short_entries.index).union(size_series.index).sort_values()

    close = price_series.reindex(index).ffill()
    long_entries = long_entries.reindex(index, fill_value=False)
    short_entries = short_entries.reindex(index, fill_value=False)
    size = size_series.reindex(index).fillna(0)

    return vbt.Portfolio.from_signals(
        close=close,
        entries=long_entries,
        exits=short_entries,
        size=size,
        init_cash=0.0,
        direction="both",  # allow both long and short
        freq="1h"
    )

def save_backtesting_results(token_address:str, backtesting_results:vbt.Portfolio, db_session:Session):
  pass

def analyze_wallet_balance(wallet_address:str, chain_name:str, days_lookback:int):
  daily_tokens_movement = take_daily_tokens_movement(wallet_address, chain_name, days_lookback)

  used_tokens = set(token for tokens in daily_tokens_movement.values() for token in tokens)

  starting_block = take_starting_block_height(chain_name, days_lookback)

  portfolios = {}
  for token_address in used_tokens:
    token_transfers = take_all_erc_token_transfers(wallet_address, chain_name, token_address, starting_block)
    backtesting_results = backtest_token_portfolio(token_address, wallet_address, token_transfers)
    portfolios[token_address] = backtesting_results

  for token_address, backtesting_results in portfolios.items():
    if backtesting_results is not None:
      win_rate = backtesting_results.stats()["Win Rate [%]"]
      if not win_rate is None:
        if win_rate > 0:
          save_backtesting_results(token_address, backtesting_results, db_session)

  return portfolios

def main():
  engine = create_engine("sqlite:///mydb.sqlite", echo=True)
  session_ = sessionmaker(bind=engine)
  session = session_()
  models.Base.metadata.create_all(engine)

  wallets = session.query(models.Wallet).all()

  for wallet in wallets:
    portfolios = analyze_wallet_balance(wallet.adress, "eth-mainnet", 300)
    print(portfolios)

  

if __name__ == "__main__":
  main()