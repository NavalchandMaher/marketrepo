import ccxt
import os

def get_binance_testnet():
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_TESTNET_API_KEY"),
        "secret": os.getenv("BINANCE_TESTNET_SECRET"),
        "options": {
            "defaultType": "spot"
        },
        "urls": {
            "api": {
                "public": "https://testnet.binance.vision/api",
                "private": "https://testnet.binance.vision/api",
            }
        }
    })

    exchange.load_markets()
    return exchange
