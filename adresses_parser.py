import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from typing import List
import models
from sqlalchemy.orm import Session, sessionmaker

def parse_etherscan_adresses(page:int = 1) -> List[str]:
    url = f"https://etherscan.io/txs?p={page}&ps=25"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        raise ValueError("Transaction table not found.")

    adresses = []

    for tr in table.find_all('tr')[1:]:  # Skip header
        tds = tr.find_all('td')
        if len(tds) < 9:
            continue  # Ensure there's a column 8

        # Column index 8 is usually 'To' address
        to_td = tds[8]

        # Find the inner span with the 'data-highlight-target' attribute
        span = to_td.find('span', attrs={'data-highlight-target': True})
        if span:
            full_address = span['data-highlight-target']
            adresses.append(full_address)
    
    return list(set(adresses))

def update_db(adresses: List[str], db_session: Session):
    wallets = [models.Wallet(adress=adress) for adress in adresses]
    for wallet in wallets:
        if not db_session.query(models.Wallet).where(models.Wallet.adress==wallet.adress).first():
            db_session.add(wallet)
            
    db_session.commit()

def parse_etherscan_adresses_and_update_db(db_session: Session, page:int = 1):
    adresses = parse_etherscan_adresses(page=page)
    update_db(adresses, db_session)

if __name__ == "__main__":
    engine = create_engine("sqlite:///mydb.sqlite", echo=True)
    session_ = sessionmaker(bind=engine)
    session = session_()
    models.Base.metadata.create_all(engine)
    parse_etherscan_adresses_and_update_db(session, page=1)