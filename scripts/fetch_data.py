#!/usr/bin/env python3
"""
OpenInsider Data Fetcher
Fetches real insider trading data from OpenInsider.com and saves to JSON
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import time
import re

class OpenInsiderScraper:
    def __init__(self):
        self.base_url = "http://openinsider.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_stock_data(self, symbol, months=3):
        """Fetch insider trading data for a specific stock symbol"""
        print(f"Fetching data for {symbol}...")

        # OpenInsider search URL
        search_url = f"{self.base_url}/search"
        params = {
            'q': symbol,
            'o': 'yes',  # Include options
            'tc': '',    # Transaction code
            's': '',     # Size
            'o1': '',    # Options 1
            'o2': '',    # Options 2
            'oc': '',    # Options code
            'x': '1'     # Execute search
        }

        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the main data table
            table = soup.find('table', {'class': 'tinytable'})
            if not table:
                print(f"No data table found for {symbol}")
                return {'symbol': symbol, 'buyCount': 0, 'sellCount': 0, 'lastCheck': datetime.now().isoformat()}

            # Parse table rows
            rows = table.find_all('tr')[1:]  # Skip header
            buy_count = 0
            sell_count = 0
            cutoff_date = datetime.now() - timedelta(days=30 * months)

            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue

                try:
                    # Extract date (usually in first few columns)
                    date_text = cells[1].get_text(strip=True) if cells[1] else ""
                    if date_text:
                        # Parse date - OpenInsider uses format like "2024-01-15"
                        try:
                            trade_date = datetime.strptime(date_text, '%Y-%m-%d')
                        except ValueError:
                            continue

                        if trade_date < cutoff_date:
                            continue

                    # Extract transaction type (Buy/Sell) - usually in transaction column
                    transaction_cell = cells[4] if len(cells) > 4 else None
                    if transaction_cell:
                        transaction_text = transaction_cell.get_text(strip=True).upper()
                        if 'P' in transaction_text or 'BUY' in transaction_text:
                            buy_count += 1
                        elif 'S' in transaction_text or 'SELL' in transaction_text:
                            sell_count += 1

                except (IndexError, ValueError) as e:
                    continue

            return {
                'symbol': symbol,
                'buyCount': buy_count,
                'sellCount': sell_count,
                'lastCheck': datetime.now().isoformat()
            }

        except requests.RequestException as e:
            print(f"Error fetching data for {symbol}: {e}")
            return {'symbol': symbol, 'buyCount': 0, 'sellCount': 0, 'lastCheck': datetime.now().isoformat()}

    def fetch_sp500_recommendations(self, limit=100):
        """Fetch insider trading data for S&P 500 stocks"""
        print("Fetching S&P 500 insider trading data...")

        # Use OpenInsider's latest insider trading page
        latest_url = f"{self.base_url}/latest-insider-trading"

        try:
            response = self.session.get(latest_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'tinytable'})

            if not table:
                print("No data table found for latest trades")
                return []

            recommendations = []
            rows = table.find_all('tr')[1:limit+1]  # Skip header, limit results

            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue

                try:
                    # Extract data from cells
                    symbol = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                    company_name = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                    # Extract transaction value
                    value_text = cells[7].get_text(strip=True) if len(cells) > 7 else "0"
                    value = self.parse_value(value_text)

                    # Extract shares
                    shares_text = cells[6].get_text(strip=True) if len(cells) > 6 else "0"
                    shares = self.parse_shares(shares_text)

                    # Extract insider type
                    insider_text = cells[5].get_text(strip=True) if len(cells) > 5 else "Other"

                    # Transaction type
                    transaction_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                    is_buy = 'P' in transaction_text.upper() or 'BUY' in transaction_text.upper()

                    if symbol and company_name:
                        recommendations.append({
                            'symbol': symbol,
                            'name': company_name,
                            'transactionValue': value,
                            'sharesTraded': shares,
                            'sharesRatio': min(shares / 1000000000 * 100, 2.0),  # Estimate ratio
                            'executiveType': self.normalize_executive_type(insider_text),
                            'insiderCount': 1,  # Will be aggregated later
                            'isBuy': is_buy,
                            'isCeoOrCfo': 'CEO' in insider_text.upper() or 'CFO' in insider_text.upper()
                        })

                except (IndexError, ValueError) as e:
                    continue

            # Aggregate by symbol and calculate scores
            aggregated = self.aggregate_recommendations(recommendations)
            return aggregated

        except requests.RequestException as e:
            print(f"Error fetching S&P 500 data: {e}")
            return []

    def parse_value(self, value_text):
        """Parse transaction value from text like '$1.2M' or '$500K'"""
        if not value_text or value_text == '-':
            return 0

        # Remove currency symbols and spaces
        value_text = re.sub(r'[^\d.,KMB]', '', value_text.upper())

        try:
            if 'M' in value_text:
                return float(value_text.replace('M', '')) * 1000000
            elif 'K' in value_text:
                return float(value_text.replace('K', '')) * 1000
            elif 'B' in value_text:
                return float(value_text.replace('B', '')) * 1000000000
            else:
                return float(value_text.replace(',', ''))
        except:
            return 0

    def parse_shares(self, shares_text):
        """Parse shares count from text"""
        if not shares_text or shares_text == '-':
            return 0

        # Remove commas and extract number
        shares_text = re.sub(r'[^\d.]', '', shares_text)
        try:
            return float(shares_text)
        except:
            return 0

    def normalize_executive_type(self, insider_text):
        """Normalize insider type to standard categories"""
        insider_upper = insider_text.upper()

        if 'CEO' in insider_upper:
            return 'CEO'
        elif 'CFO' in insider_upper:
            return 'CFO'
        elif 'DIRECTOR' in insider_upper:
            return 'Director'
        elif '10%' in insider_upper or 'OWNER' in insider_upper:
            return '10% Owner'
        elif 'OFFICER' in insider_upper:
            return 'Officer'
        else:
            return 'Other'

    def aggregate_recommendations(self, recommendations):
        """Aggregate recommendations by symbol and calculate scores"""
        symbol_data = {}

        for rec in recommendations:
            symbol = rec['symbol']
            if symbol not in symbol_data:
                symbol_data[symbol] = {
                    'symbol': symbol,
                    'name': rec['name'],
                    'buyTransactions': [],
                    'sellTransactions': [],
                    'insiderCount': set()
                }

            symbol_data[symbol]['insiderCount'].add(rec['executiveType'])

            if rec['isBuy']:
                symbol_data[symbol]['buyTransactions'].append(rec)
            else:
                symbol_data[symbol]['sellTransactions'].append(rec)

        # Calculate scores for buy and sell recommendations
        buy_recommendations = []
        sell_recommendations = []

        for symbol, data in symbol_data.items():
            if data['buyTransactions']:
                score = self.calculate_score(data['buyTransactions'], len(data['insiderCount']))
                buy_recommendations.append({
                    'symbol': symbol,
                    'name': data['name'],
                    'score': score,
                    'transactionValue': sum(t['transactionValue'] for t in data['buyTransactions']),
                    'sharesRatio': sum(t['sharesRatio'] for t in data['buyTransactions']) / len(data['buyTransactions']),
                    'executiveType': data['buyTransactions'][0]['executiveType'],
                    'insiderCount': len(data['insiderCount']),
                    'isCeoOrCfo': any(t['isCeoOrCfo'] for t in data['buyTransactions'])
                })

            if data['sellTransactions']:
                score = self.calculate_score(data['sellTransactions'], len(data['insiderCount']))
                sell_recommendations.append({
                    'symbol': symbol,
                    'name': data['name'],
                    'score': score,
                    'transactionValue': sum(t['transactionValue'] for t in data['sellTransactions']),
                    'sharesRatio': sum(t['sharesRatio'] for t in data['sellTransactions']) / len(data['sellTransactions']),
                    'executiveType': data['sellTransactions'][0]['executiveType'],
                    'insiderCount': len(data['insiderCount']),
                    'isCeoOrCfo': any(t['isCeoOrCfo'] for t in data['sellTransactions'])
                })

        # Sort by score and return top 10 each
        buy_recommendations.sort(key=lambda x: x['score'], reverse=True)
        sell_recommendations.sort(key=lambda x: x['score'], reverse=True)

        return {
            'buy': buy_recommendations[:10],
            'sell': sell_recommendations[:10]
        }

    def calculate_score(self, transactions, insider_count):
        """Calculate recommendation score based on transaction data"""
        total_value = sum(t['transactionValue'] for t in transactions)
        avg_ratio = sum(t['sharesRatio'] for t in transactions) / len(transactions)

        # Calculate scores
        value_score = self.calculate_value_score(total_value)
        ratio_score = self.calculate_ratio_score(avg_ratio)
        executive_score = self.calculate_executive_score(transactions[0]['executiveType'])
        concentration_score = self.calculate_concentration_score(insider_count)

        # Weighted final score
        final_score = (
            value_score * 0.4 +
            ratio_score * 0.3 +
            executive_score * 0.2 +
            concentration_score * 0.1
        )

        return round(final_score)

    def calculate_value_score(self, value):
        """Calculate score based on transaction value"""
        if value >= 10000000: return 100
        if value >= 5000000: return 80
        if value >= 1000000: return 60
        if value >= 100000: return 40
        return 20

    def calculate_ratio_score(self, ratio):
        """Calculate score based on shares ratio"""
        if ratio >= 1.0: return 100
        if ratio >= 0.5: return 80
        if ratio >= 0.1: return 60
        if ratio >= 0.05: return 40
        return 20

    def calculate_executive_score(self, exec_type):
        """Calculate score based on executive type"""
        scores = {
            'CEO': 100,
            'CFO': 90,
            '10% Owner': 85,
            'Director': 70,
            'Officer': 50,
            'Other': 30
        }
        return scores.get(exec_type, 30)

    def calculate_concentration_score(self, count):
        """Calculate score based on insider count"""
        if count >= 5: return 100
        if count >= 3: return 70
        if count >= 2: return 50
        return 30

def main():
    # Default stocks to monitor
    default_stocks = ['TSLA', 'PLTR', 'RGTI', 'IONQ', 'MSTR', 'LLY']

    scraper = OpenInsiderScraper()

    # Create data directory
    os.makedirs('data', exist_ok=True)

    # Fetch data for default stocks
    print("=== Fetching Stock Data ===")
    stock_data = {}

    for symbol in default_stocks:
        try:
            data = scraper.fetch_stock_data(symbol)
            stock_data[symbol] = data
            time.sleep(2)  # Be respectful to the server
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

    print("Stock data saved to data/stocks.json")

    # Fetch recommendations
    print("\n=== Fetching Recommendations ===")
    try:
        recommendations = scraper.fetch_sp500_recommendations()

        with open('data/recommendations.json', 'w') as f:
            json.dump({
                'lastUpdate': datetime.now().isoformat(),
                'recommendations': recommendations
            }, f, indent=2)

        print("Recommendations saved to data/recommendations.json")
        print(f"Found {len(recommendations.get('buy', []))} buy recommendations")
        print(f"Found {len(recommendations.get('sell', []))} sell recommendations")

    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        # Create empty recommendations file
        with open('data/recommendations.json', 'w') as f:
            json.dump({
                'lastUpdate': datetime.now().isoformat(),
                'recommendations': {'buy': [], 'sell': []}
            }, f, indent=2)

    print("\n=== Data Update Complete ===")

if __name__ == "__main__":
    main()