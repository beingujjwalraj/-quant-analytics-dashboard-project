import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'quant-dev-secret-key-2024'
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'tick_data.db')
    MAX_BUFFER_SIZE = 5000
    DEFAULT_SYMBOLS = ['btcusdt', 'ethusdt', 'adausdt', 'solusdt']
    RESAMPLE_INTERVALS = ['1s', '5s', '15s', '1m', '5m', '15m']
    ROLLING_WINDOWS = [10, 20, 50, 100]
    BINANCE_WS_URL = "wss://fstream.binance.com/ws/{}@trade"