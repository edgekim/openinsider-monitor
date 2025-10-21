#!/usr/bin/env python3
"""
SEC EDGAR Insider Trading Data Fetcher
Fetches real insider trading data from SEC EDGAR API and saves to JSON
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import time
import re
from urllib.parse import urlencode

class SECInsiderFetcher:
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.session = requests.Session()
        # SEC requires a User-Agent with contact info - using proper format
        # Format: "Company Name Contact@email.com"
        self.session.headers.update({
            'User-Agent': 'OpenInsiderMonitor contact@edgekim.com',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'application/json'
        })
        self.ticker_to_cik = {}
        self._load_ticker_mappings()

    def _load_ticker_mappings(self):
        """Load ticker to CIK mappings - using hardcoded values for reliability"""
        # Hardcoded CIK mappings for monitored stocks
        # CIK can be found at: https://www.sec.gov/cgi-bin/browse-edgar?company=[ticker]&action=getcompany
        self.ticker_to_cik = {
            'TSLA': '0001318605',  # Tesla Inc
            'PLTR': '0001321655',  # Palantir Technologies Inc
            'RGTI': '0001810383',  # Rigetti Computing Inc
            'IONQ': '0001733755',  # IonQ Inc
            'MSTR': '0001050446',  # MicroStrategy Inc
            'LLY': '0000059478',   # Eli Lilly and Company
            'AAPL': '0000320193',  # Apple Inc
            'MSFT': '0000789019',  # Microsoft Corp
            'NVDA': '0001045810',  # NVIDIA Corp
            'GOOGL': '0001652044', # Alphabet Inc
            'AMZN': '0001018724',  # Amazon.com Inc
            'META': '0001326801',  # Meta Platforms Inc
        }

        print(f"Loaded {len(self.ticker_to_cik)} ticker mappings (hardcoded)")

        # Optionally try to load more from SEC API
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.values():
                    ticker = item['ticker'].upper()
                    cik = str(item['cik_str']).zfill(10)
                    if ticker not in self.ticker_to_cik:
                        self.ticker_to_cik[ticker] = cik
                print(f"Enhanced with {len(self.ticker_to_cik)} total mappings")
        except Exception as e:
            print(f"Note: Using hardcoded CIKs only (SEC API unavailable)")

    def _get_cik(self, symbol):
        """Get CIK for a stock symbol"""
        return self.ticker_to_cik.get(symbol.upper())

    def fetch_stock_data(self, symbol, months=3):
        """Fetch insider trading data for a specific stock symbol from SEC EDGAR Data API"""
        print(f"Fetching data for {symbol}...")

        cik = self._get_cik(symbol)
        if not cik:
            print(f"CIK not found for {symbol}")
            return {'symbol': symbol, 'buyCount': 0, 'sellCount': 0, 'lastCheck': datetime.now().isoformat()}

        try:
            # Use SEC EDGAR Data API - official JSON endpoint
            url = f"{self.base_url}/submissions/CIK{cik}.json"

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            data = response.json()

            # Get recent filings
            filings = data.get('filings', {}).get('recent', {})
            if not filings:
                print(f"No filings found for {symbol}")
                return {'symbol': symbol, 'buyCount': 0, 'sellCount': 0, 'lastCheck': datetime.now().isoformat()}

            # Extract Form 4 filings
            forms = filings.get('form', [])
            dates = filings.get('filingDate', [])
            accession_numbers = filings.get('accessionNumber', [])

            buy_count = 0
            sell_count = 0
            cutoff_date = datetime.now() - timedelta(days=30 * months)

            for i, (form, date_str, accession) in enumerate(zip(forms, dates, accession_numbers)):
                if form != '4':  # Only Form 4 (insider trading)
                    continue

                try:
                    filing_date = datetime.strptime(date_str, '%Y-%m-%d')
                    if filing_date < cutoff_date:
                        continue

                    # Construct URL to Form 4 XML document
                    # Format: https://www.sec.gov/cgi-bin/viewer?action=view&cik=CIK&accession_number=ACCESSION&xbrl_type=v
                    # Or simpler: https://www.sec.gov/Archives/edgar/data/CIK/ACCESSION-NO-DASHES/primary_doc.xml
                    accession_no_dashes = accession.replace('-', '')
                    cik_no_leading_zeros = str(int(cik))

                    # Form 4 primary document is usually form4.xml or wf-form4.xml
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_no_dashes}/primary_doc.xml"

                    # Fetch the Form 4 XML with proper headers
                    time.sleep(0.15)  # Rate limiting for SEC
                    doc_headers = self.session.headers.copy()
                    doc_headers['Host'] = 'www.sec.gov'

                    try:
                        form_response = requests.get(doc_url, headers=doc_headers, timeout=10)

                        if form_response.status_code == 200:
                            form_text = form_response.text.upper()

                            # Parse transaction codes from XML
                            # Transaction codes in Form 4:
                            # P = Purchase
                            # S = Sale
                            if '<TRANSACTIONCODE>P<' in form_text or '>P<' in form_text:
                                buy_count += 1
                            elif '<TRANSACTIONCODE>S<' in form_text or '>S<' in form_text:
                                sell_count += 1

                    except Exception as e:
                        # Try alternate document name
                        continue

                except (IndexError, ValueError) as e:
                    continue

            print(f"  Found: BUY={buy_count}, SELL={sell_count}")

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

        # For now, return empty recommendations
        # This can be enhanced later with SEC EDGAR's latest filings
        print("Note: Recommendations feature will be enhanced in future update")
        return {'buy': [], 'sell': []}

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

    fetcher = SECInsiderFetcher()

    # Create data directory
    os.makedirs('data', exist_ok=True)

    # Fetch data for default stocks
    print("=== Fetching Stock Data ===")
    stock_data = {}

    for symbol in default_stocks:
        try:
            data = fetcher.fetch_stock_data(symbol)
            stock_data[symbol] = data
            print(f"{symbol}: BUY={data['buyCount']}, SELL={data['sellCount']}")
            time.sleep(1)  # Be respectful to SEC servers
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

    # Fetch recommendations - simplified for now
    print("\n=== Fetching Recommendations ===")
    try:
        recommendations = fetcher.fetch_sp500_recommendations()

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