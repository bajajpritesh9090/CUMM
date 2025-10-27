import time
import os
import requests
from binance.client import Client
from datetime import datetime, timezone
from prettytable import PrettyTable
import pandas as pd
import re

# ==================== CONFIG ====================

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

PERCENT_THRESHOLD = 4.5
INTERVAL = Client.KLINE_INTERVAL_3MINUTE

# =================================================

def send_telegram_alert(message: str):
    """Send message via Telegram bot"""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"Telegram exception: {e}")

def main():
    client = Client(API_KEY, API_SECRET)

    # Fetch all USDT perpetual contracts
    info = client.futures_exchange_info()
    all_perps = [
        s['symbol'] for s in info['symbols']
        if s['contractType'] == 'PERPETUAL'
        and s['status'] == 'TRADING'
        and s['quoteAsset'] == 'USDT'
    ]
    print(f"Monitoring {len(all_perps)} perpetual pairs...\n")

    while True:
        print(f"\n=== Checking at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC ===")
        results = []

        for symbol in all_perps:
            try:
                klines = client.futures_klines(symbol=symbol, interval=INTERVAL, limit=2)
                o1, c1 = float(klines[-1][1]), float(klines[-1][4])
                percent_change = ((c1 - o1) / o1) * 100

                if abs(percent_change) >= PERCENT_THRESHOLD:
                    result = f"{symbol} [{percent_change:+.2f}%]"
                    print(result)
                    results.append(result)

            except Exception as e:
                print(f"Error fetching {symbol}: {e}")

        if results:
            # Sort results by % change (descending)
            results_sorted = sorted(
                results,
                key=lambda x: float(re.search(r"([+-]?\d+\.\d+)%", x).group(1)),
                reverse=True
            )

            alert_text = "⚠️ *Detected!*\n\n" + "\n".join(results_sorted)
            send_telegram_alert(alert_text)

        # Align with next 3-min candle
        now = datetime.now()
        minute = now.minute
        second = now.second
        wait_min = (3 - (minute % 3)) % 3
        if wait_min == 0 and second < 3:
            wait_min = 0
        elif wait_min == 0:
            wait_min = 3

        sleep_secs = wait_min * 60 + (60 - second) + 3 - 60
        print(f"Sleeping for {sleep_secs:.1f} seconds...\n")
        time.sleep(max(sleep_secs, 60))  # at least 1 minute sleep

if __name__ == "__main__":
    main()