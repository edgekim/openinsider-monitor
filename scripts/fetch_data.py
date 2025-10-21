#!/usr/bin/env python3
"""
Finnhub Insider Trading Data Fetcher
Fetches insider trading data from Finnhub API and saves to JSON
Finnhub provides free API access with 60 calls/minute
"""

import requests
import json
import os
from datetime import datetime, timedelta
import time

class FinnhubInsiderFetcher:
    def __init__(self, api_key=None):
        self.base_url = "https://finnhub.io/api/v1"
        # Free API key - users should get their own from https://finnhub.io/
        # This is a demo key with limited rate (60 calls/min)
        self.api_key = api_key or "demo"  # Replace with actual key in GitHub Actions
        self.session = requests.Session()

    def fetch_stock_data(self, symbol, months=3):
        """Fetch insider trading data for a specific stock symbol"""
        print(f"Fetching data for {symbol}...")

        try:
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=30 * months)

            # Finnhub insider transactions endpoint
            url = f"{self.base_url}/stock/insider-transactions"
            params = {
                'symbol': symbol,
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d'),
                'token': self.api_key
            }

            response = self.session.get(url, params=params, timeout=10)

            # Handle rate limiting
            if response.status_code == 429:
                print(f"  Rate limited, waiting...")
                time.sleep(5)
                response = self.session.get(url, params=params, timeout=10)

            response.raise_for_status()

            data = response.json()

            # Parse transactions
            buy_count = 0
            sell_count = 0

            if 'data' in data and data['data']:
                for transaction in data['data']:
                    # Finnhub transaction structure:
                    # {
                    #   "name": "Insider name",
                    #   "share": number of shares,
                    #   "change": change in shares,
                    #   "filingDate": "YYYY-MM-DD",
                    #   "transactionDate": "YYYY-MM-DD",
                    #   "transactionCode": "P" or "S" etc,
                    #   "transactionPrice": price
                    # }

                    trans_code = transaction.get('transactionCode', '').upper()

                    if trans_code in ['P', 'P - Purchase']:
                        buy_count += 1
                    elif trans_code in ['S', 'S - Sale']:
                        sell_count += 1

            print(f"  Found: BUY={buy_count}, SELL={sell_count}")

            return {
                'symbol': symbol,
                'buyCount': buy_count,
                'sellCount': sell_count,
                'lastCheck': datetime.now().isoformat()
            }

        except requests.RequestException as e:
            print(f"Error fetching data for {symbol}: {e}")
            return {
                'symbol': symbol,
                'buyCount': 0,
                'sellCount': 0,
                'lastCheck': datetime.now().isoformat()
            }

    def fetch_recommendations(self):
        """Placeholder for recommendations - can be enhanced later"""
        return {'buy': [], 'sell': []}


def main():
    # Get API key from environment variable (set in GitHub Actions secrets)
    api_key = os.environ.get('FINNHUB_API_KEY', 'demo')

    if api_key == 'demo':
        print("WARNING: Using demo API key. Please set FINNHUB_API_KEY environment variable")
        print("Get your free API key from: https://finnhub.io/register")

    # Default stocks to monitor
    default_stocks = ['TSLA', 'PLTR', 'RGTI', 'IONQ', 'MSTR', 'LLY']

    fetcher = FinnhubInsiderFetcher(api_key=api_key)

    # Create data directory
    os.makedirs('data', exist_ok=True)

    # Fetch data for default stocks
    print("=== Fetching Stock Data from Finnhub ===")
    stock_data = {}

    for symbol in default_stocks:
        try:
            data = fetcher.fetch_stock_data(symbol)
            stock_data[symbol] = data
            print(f"{symbol}: BUY={data['buyCount']}, SELL={data['sellCount']}")
            time.sleep(1.1)  # Rate limiting (60 calls/min = ~1 per second)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            stock_data[symbol] = {
                'symbol': symbol,
                'buyCount': 0,
                'sellCount': 0,
                'lastCheck': datetime.now().isoformat()
            }

    # Save stock data
    with open('data/stocks.json', 'w') as f:
        json.dump({
            'lastUpdate': datetime.now().isoformat(),
            'stocks': stock_data
        }, f, indent=2)

    print("\nStock data saved to data/stocks.json")

    # Save recommendations (empty for now)
    print("\n=== Saving Recommendations ===")
    recommendations = fetcher.fetch_recommendations()

    with open('data/recommendations.json', 'w') as f:
        json.dump({
            'lastUpdate': datetime.now().isoformat(),
            'recommendations': recommendations
        }, f, indent=2)

    print("Recommendations saved to data/recommendations.json")
    print("\n=== Data Update Complete ===")


if __name__ == "__main__":
    main()
