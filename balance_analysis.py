from datetime import datetime, timedelta, timezone
from typing import List, Dict, Union
import os
import dotenv
import requests
from dateutil import parser
import pandas as pd
import vectorbt as vbt

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

def get_a_block(chain_name:str, block_height: Union[str | int] = "latest"):

  url = f"https://api.covalenthq.com/v1/{chain_name}/block_v2/{block_height}/"

  headers = {"Authorization": f"Bearer {os.getenv('GOLDRUSH_API_KEY')}"}

  response = requests.request("GET", url, headers=headers)

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
    query_params = {"starting_block": starting_block, "page_number": p, "quote_currency": "EUR"}
    response = requests.request("GET", url, headers=headers, params=query_params)
    response_data = response.json()["data"]

    if response.ok:
      all_transfers += response_data["items"]
    
    if response_data["pagination"]["has_more"]:
      p += 1
    else:
      break

  return all_transfers

def backtest_token_portfolio(token_address: str, wallet_address: str, token_transfers: list):
  """
  Backtest a token portfolio using vectorbt:
  - token_prices_over_time: Series of token prices over time (EUR)
  - position_sizes: Series of position sizes (raw token amounts held)
  """

  prices = {}
  position_deltas = {}

  for transfer in token_transfers:
    if not transfer.get("successful", True):
      continue

    dt = parser.parse(transfer["block_signed_at"])
    price = transfer["value_quote"]
    amount = transfer["value"]

    # Determine if wallet gained or lost tokens
    delta = -amount if transfer["from_sender"] == wallet_address else amount

    prices[dt] = price  # Overwrites are fine, Covalent reports 1 tx/block usually
    position_deltas[dt] = position_deltas.get(dt, 0) + delta

  if not prices:
    return None  # Or raise Exception

  # Create sorted Series
  price_series = pd.Series(prices).sort_index()
  position_deltas_series = pd.Series(position_deltas).sort_index()

  # Build cumulative token holdings (wallet position over time)
  position_series = position_deltas_series.cumsum()

  # Align position series with price timestamps (forward-fill holdings)
  position_series = position_series.reindex(price_series.index, method='ffill').fillna(0)

  # Backtest with vectorbt
  portfolio = backtest_with_vectorbt(price_series, position_series)

  return portfolio


def backtest_with_vectorbt(price_series: pd.Series, position_series: pd.Series) -> vbt.Portfolio:
  """
  Create a vectorbt Portfolio using known price and position series.
  Assumes you already calculated holdings over time.
  """
  return vbt.Portfolio.from_holding(
    close=price_series,
    size=position_series,
    init_cash=0.0,
    freq='1h'
  )

def save_backtesting_results(token_address:str, results):
  pass


def analyze_wallet_ballance(wallet_address:str, chain_name:str, days_lookback:int):

  daily_tokens_movement = take_daily_tokens_movement(wallet_address, chain_name, days_lookback)
  starting_block = take_starting_block_height(chain_name, days_lookback)

  for token_address in daily_tokens_movement:
    token_transfers = take_all_erc_token_transfers(wallet_address, chain_name, token_address, starting_block)
    backtesting_results = backtest_token_portfolio(token_address, wallet_address, token_transfers)
    save_backtesting_results(backtesting_results)
  

if __name__ == "__main__":
  result = analyze_wallet_ballance("0x8badd8b59DdAf9A12c4910Ca1B2E8ea750A71594", "eth-mainnet", 30)




# def take_all_wallets_transactions(wallet_address:str, chain_name:str, days_lookback:int):

#   stop_looking_date = datetime.now(tz=timezone.utc) - timedelta(days_lookback)
#   all_transactions = []
#   page = 1
#   run = True

#   while run:
#     url = f"https://api.covalenthq.com/v1/{chain_name}/address/{wallet_address}/transactions_v3/page/{page}/"
#     headers = {"Authorization": f"Bearer {os.getenv("GOLDRUSH_API_KEY")}"}
#     response = requests.request("GET", url, headers=headers)
#     transactions = response.json()["data"]["items"]

#     if len(transactions) < 1 or parser.parse(transactions[0]["block_signed_at"]) < stop_looking_date:
#       run = False

#     for transaction in transactions:
#       # TODO add re-orged block checker. "Get block heights" endpoint + custom mapping block height:hash
#       # check sender/receiver hashes.
#       # time, sender/receiver, value
#       if transaction.get("log_events", None) is None:
#         continue

#       block_signed_at = parser.parse(transaction["block_signed_at"])
#       if block_signed_at < stop_looking_date:
#         run = False
#         break
      
#       for log_event in transaction["log_events"]:
#         from_address = log_event
#         to_address = log_event
#         value = log_event

#         all_transactions.append({
#           "block_signed_at": block_signed_at,
#           "from_address": from_address,
#           "to_address": to_address,
#           "value": value

#         })


#     page += 1

#   return all_transactions